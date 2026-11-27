#!/usr/bin/env python3
"""Upload or upsert a local file to Google Drive via gws in an isolated temp dir with read-back verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"

_DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_MIME_TYPE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")


def validate_drive_id(value: str, label: str = "Drive ID") -> str:
    """Validate a Drive folder or file ID before interpolation into Drive queries."""
    cleaned = value.strip()
    if not cleaned or not _DRIVE_ID_RE.fullmatch(cleaned):
        raise ValueError(f"Invalid {label}: expected 8-128 characters from [A-Za-z0-9_-].")
    return cleaned


def validate_mime_type(value: str, label: str = "MIME type") -> str:
    """Validate an RFC 6838 type/subtype string before sending to Drive."""
    cleaned = value.strip()
    if not cleaned or not _MIME_TYPE_RE.fullmatch(cleaned):
        raise ValueError(f"Invalid {label}: expected a valid RFC 6838 type/subtype.")
    return cleaned


def validate_name(value: str, label: str = "name") -> str:
    """Reject empty, path-like, or control-character Drive filenames."""
    cleaned = value.strip()
    if not cleaned or cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned or _CONTROL_CHAR_RE.search(cleaned):
        raise ValueError(f"Invalid {label}: must be a single filename without slashes or control characters.")
    return cleaned


def _escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _parse_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        raise RuntimeError("gws returned empty output.")
    decoder = json.JSONDecoder()
    parsed: Any = None
    found = False
    for pos, ch in enumerate(text):
        if (pos == 0 or text[pos - 1] == "\n") and ch == "{":
            try:
                parsed, end = decoder.raw_decode(text, pos)
            except json.JSONDecodeError:
                break
            if end == len(text) and isinstance(parsed, dict):
                found = True
            break
    if not found:
        raise RuntimeError("gws did not return a JSON object.")
    if "error" in parsed:
        detail = json.dumps(parsed["error"], ensure_ascii=False)[:300]
        raise RuntimeError(f"Google API error: {detail}")
    return parsed


def run_gws(args: list[str], *, cwd: Path) -> dict[str, Any]:
    """Execute gws inside an isolated directory so ancestor .env files are never loaded."""
    gws_bin = shutil.which("gws")
    if not gws_bin:
        raise RuntimeError("gws binary not found on PATH; install and run `dot login workspace`.")
    proc = subprocess.run(  # noqa: S603
        [gws_bin, *args, "--format", "json"],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if proc.returncode != 0:
        detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
        raise RuntimeError(f"gws {' '.join(args[:3])} failed (exit {proc.returncode}): {detail}")
    return _parse_json(proc.stdout)


def find_existing(folder_id: str, name: str, *, target_mime: str | None, cwd: Path) -> dict[str, Any] | None:
    """Find a unique non-trashed file matching name (and optional target_mime) inside folder_id."""
    clauses = [f"'{folder_id}' in parents", f"name = '{_escape_drive_query(name)}'", "trashed = false"]
    if target_mime:
        clauses.append(f"mimeType = '{_escape_drive_query(target_mime)}'")
    query = " and ".join(clauses)
    matches: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {
            "q": query,
            "fields": "nextPageToken,incompleteSearch,files(id,name,mimeType,webViewLink)",
            "pageSize": 20,
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }
        if page_token:
            params["pageToken"] = page_token
        data = run_gws(["drive", "files", "list", "--params", json.dumps(params)], cwd=cwd)
        if data.get("incompleteSearch") is True:
            raise RuntimeError(
                f"Drive search for {name!r} in folder {folder_id} was incomplete; retry or specify --file-id."
            )
        files = data.get("files") or []
        matches.extend(item for item in files if isinstance(item, dict))
        if len(matches) > 1:
            raise RuntimeError(
                f"Multiple Drive files ({len(matches)}+) match {name!r} in folder {folder_id}; specify --file-id."
            )
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return matches[0] if matches else None


def _upload_content_type(path: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    suffix = path.suffix.lower()
    overrides = {
        ".md": "text/markdown",
        ".html": "text/html",
        ".htm": "text/html",
        ".pdf": "application/pdf",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv",
    }
    if suffix in overrides:
        return overrides[suffix]
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _file_md5_and_size(path: Path) -> tuple[str, int]:
    digest = hashlib.md5(usedforsecurity=False)
    total = 0
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def upload_file(
    source: Path,
    *,
    drive_folder: str | None = None,
    file_id: str | None = None,
    name: str | None = None,
    content_type: str | None = None,
    target_mime: str | None = None,
    protect_copy: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Stage source in a private temp dir, upsert to Drive via gws, and verify read-back."""
    src = source.resolve()
    if not src.is_file() or src.stat().st_size == 0:
        raise ValueError(f"Source file must exist and be non-empty: {source}")
    if bool(drive_folder) == bool(file_id):
        raise ValueError("Provide exactly one of --drive-folder or --file-id.")

    folder_id = validate_drive_id(drive_folder, "--drive-folder") if drive_folder else None
    existing_id = validate_drive_id(file_id, "--file-id") if file_id else None
    validated_content_type = validate_mime_type(content_type, "--content-type") if content_type else None
    validated_target_mime = validate_mime_type(target_mime, "--target-mime") if target_mime else None
    upload_mime = _upload_content_type(src, validated_content_type)
    final_mime = validated_target_mime or upload_mime
    is_google_native = final_mime.startswith("application/vnd.google-apps.")
    explicit_name = validate_name(name, "--name") if name is not None else None
    derived_name = explicit_name or validate_name(src.stem if is_google_native else src.name, "--name")

    if existing_id and final_mime == GOOGLE_DOC_MIME:
        raise ValueError(
            "Refusing drive.files.update on an existing Google Doc (drops comments/suggestions); "
            "patch via documents.batchUpdate or create a new sibling file."
        )

    plan: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "source": str(src),
        "remote_name": explicit_name if existing_id else derived_name,
        "upload_content_type": upload_mime,
        "target_mime": final_mime,
        "drive_folder": folder_id,
        "file_id": existing_id,
        "size": src.stat().st_size,
        "protect_copy": protect_copy,
    }
    if dry_run:
        return plan

    with tempfile.TemporaryDirectory(prefix="gws-upload-") as tmp:
        tmp_dir = Path(tmp)
        # Sentinel stops gws from walking upward into /tmp/.env or $TMPDIR/.env.
        os.close(os.open(tmp_dir / ".env", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        staged_suffix = src.suffix if re.fullmatch(r"\.[A-Za-z0-9]{1,10}", src.suffix) else ""
        staged = tmp_dir / f"upload{staged_suffix}"
        shutil.copy2(src, staged)
        local_md5, local_size = _file_md5_and_size(staged)

        target_id = existing_id
        if target_id is not None:
            current = run_gws(
                [
                    "drive",
                    "files",
                    "get",
                    "--params",
                    json.dumps({"fileId": target_id, "supportsAllDrives": True, "fields": "id,mimeType,trashed"}),
                ],
                cwd=tmp_dir,
            )
            if current.get("trashed") is True:
                raise ValueError(f"Refusing drive.files.update on trashed file {target_id}.")
            current_mime = current.get("mimeType")
            if not isinstance(current_mime, str) or not current_mime:
                raise RuntimeError(f"Existing file {target_id} metadata missing mimeType; refusing update.")
            if current_mime == GOOGLE_DOC_MIME:
                raise ValueError(
                    f"Refusing drive.files.update on existing Google Doc {target_id} (drops comments/suggestions); "
                    "patch via documents.batchUpdate or create a new sibling file."
                )
            if validated_target_mime and current_mime != validated_target_mime:
                raise ValueError(
                    f"Existing file {target_id} has mimeType {current_mime!r}, expected {validated_target_mime!r}; "
                    "create a new sibling file to change MIME types."
                )
            if not validated_target_mime and current_mime.startswith("application/vnd.google-apps."):
                raise ValueError(
                    f"Existing file {target_id} is Google-native ({current_mime!r}); "
                    "pass matching --target-mime or create a new sibling file."
                )
        elif folder_id is not None:
            found = find_existing(folder_id, derived_name, target_mime=final_mime, cwd=tmp_dir)
            if found and isinstance(found.get("id"), str):
                if final_mime == GOOGLE_DOC_MIME:
                    raise ValueError(
                        f"Google Doc {derived_name!r} already exists in folder {folder_id} (id={found['id']}); "
                        "refusing drive.files.update (drops comments/suggestions). "
                        "Patch via documents.batchUpdate or choose a distinct --name."
                    )
                target_id = found["id"]

        metadata: dict[str, Any] = {}
        if target_id is None:
            metadata["name"] = derived_name
            metadata["parents"] = [folder_id]
            if validated_target_mime:
                metadata["mimeType"] = validated_target_mime
        elif explicit_name is not None:
            metadata["name"] = explicit_name
        if protect_copy:
            metadata["copyRequiresWriterPermission"] = True

        fields = "id,name,mimeType,webViewLink,trashed,md5Checksum,size"
        if protect_copy:
            fields += ",copyRequiresWriterPermission"
        if target_id:
            params: dict[str, Any] = {"fileId": target_id, "supportsAllDrives": True, "fields": fields}
            cmd = ["drive", "files", "update", "--params", json.dumps(params)]
            if metadata:
                cmd.extend(["--json", json.dumps(metadata)])
            cmd.extend(["--upload", staged.name, "--upload-content-type", upload_mime])
            result = run_gws(cmd, cwd=tmp_dir)
            action = "updated"
        else:
            params = {"supportsAllDrives": True, "fields": fields}
            result = run_gws(
                [
                    "drive",
                    "files",
                    "create",
                    "--params",
                    json.dumps(params),
                    "--json",
                    json.dumps(metadata),
                    "--upload",
                    staged.name,
                    "--upload-content-type",
                    upload_mime,
                ],
                cwd=tmp_dir,
            )
            action = "created"

        uploaded_id = result.get("id")
        if not isinstance(uploaded_id, str) or not uploaded_id:
            raise RuntimeError("Drive upload response missing file id.")

        verified = run_gws(
            [
                "drive",
                "files",
                "get",
                "--params",
                json.dumps({"fileId": uploaded_id, "supportsAllDrives": True, "fields": fields}),
            ],
            cwd=tmp_dir,
        )
        if verified.get("trashed") is True:
            raise RuntimeError(f"Read-back failed: file {uploaded_id} is trashed.")
        if validated_target_mime and verified.get("mimeType") != validated_target_mime:
            raise RuntimeError(
                f"Read-back mimeType mismatch: expected {validated_target_mime}, got {verified.get('mimeType')}."
            )
        if protect_copy and verified.get("copyRequiresWriterPermission") is not True:
            raise RuntimeError(f"Read-back failed: copyRequiresWriterPermission not enabled for {uploaded_id}.")
        if not is_google_native:
            remote_md5 = verified.get("md5Checksum")
            remote_size = verified.get("size")
            if not isinstance(remote_md5, str) or remote_md5 != local_md5:
                raise RuntimeError(f"Read-back MD5 missing or mismatch for {uploaded_id}.")
            if isinstance(remote_size, bool) or not isinstance(remote_size, (int, str)):
                raise RuntimeError(f"Read-back size missing or invalid for {uploaded_id}.")
            try:
                parsed_remote_size = int(remote_size)
            except ValueError as err:
                raise RuntimeError(f"Read-back size invalid for {uploaded_id}.") from err
            if parsed_remote_size != local_size:
                raise RuntimeError(f"Read-back size mismatch for {uploaded_id}.")

        return {
            "ok": True,
            "action": action,
            "id": uploaded_id,
            "name": verified.get("name"),
            "mimeType": verified.get("mimeType"),
            "webViewLink": verified.get("webViewLink"),
        }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    if hasattr(parser, "suggest_on_error"):
        parser.suggest_on_error = True
    parser.add_argument("source", type=Path, help="Local file to upload.")
    parser.add_argument("--drive-folder", default=None, help="Target Drive folder ID (upserts matching name + MIME).")
    parser.add_argument("--file-id", default=None, help="Existing Drive file ID to update in place.")
    parser.add_argument("--name", default=None, help="Remote Drive filename.")
    parser.add_argument("--content-type", default=None, help="Source MIME type override (inferred from extension).")
    parser.add_argument("--target-mime", default=None, help="Target Drive MIME type (e.g. Google Doc/Slides/Sheets).")
    parser.add_argument("--protect-copy", action="store_true", help="Set copyRequiresWriterPermission=true.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print upload plan without writing.")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Emit JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        payload = upload_file(
            args.source,
            drive_folder=args.drive_folder,
            file_id=args.file_id,
            name=args.name,
            content_type=args.content_type,
            target_mime=args.target_mime,
            protect_copy=args.protect_copy,
            dry_run=args.dry_run,
        )
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        if args.json_output:
            sys.stderr.write(json.dumps({"error": str(exc)}) + "\n")
        else:
            sys.stderr.write(f"Error: {exc}\n")
        return 1
    if args.json_output:
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        for key, value in payload.items():
            sys.stdout.write(f"{key}: {value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
