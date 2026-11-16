"""Google Drive and Google Slides upload/verification helpers for Typst slide decks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pptx_builder import inspect_pptx_metadata
from typst_check import collect_source_files

DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,128}$")
PDF_MIME = "application/pdf"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
GOOGLE_SLIDES_MIME = "application/vnd.google-apps.presentation"
FOLDER_MIME = "application/vnd.google-apps.folder"


def validate_drive_id(value: str, label: str) -> str:
    cleaned = value.strip()
    if not DRIVE_ID_RE.fullmatch(cleaned):
        raise ValueError(f"Invalid Google Drive {label}: {value!r}")
    return cleaned


def validate_upload_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned or cleaned in {".", ".."} or cleaned.startswith("-") or "/" in cleaned or "\\" in cleaned:
        raise ValueError(f"Remote filename must be a plain filename without path separators or leading '-': {value!r}")
    return cleaned


def validate_presentation_title(value: str) -> str:
    cleaned = value.strip()
    if not cleaned or any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        raise ValueError(f"Google Slides presentation title must be a single non-empty line: {value!r}")
    return cleaned


def _escape_drive_q(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def run_gws(args: list[str], *, cwd: Path) -> dict[str, Any]:
    gws_bin = shutil.which("gws")
    if not gws_bin:
        raise RuntimeError("gws CLI not found on PATH; install and authenticate `gws` before uploading.")
    proc = subprocess.run(  # noqa: S603 - fixed gws CLI binary and structured arguments
        [gws_bin, *args, "--format", "json"],
        cwd=str(cwd),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if proc.returncode != 0:
        detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
        raise RuntimeError(f"gws {' '.join(args[:3])} failed (exit {proc.returncode}): {detail}")
    out = proc.stdout.strip()
    if not out:
        raise RuntimeError(f"gws {' '.join(args[:3])}: expected JSON object on stdout.")
    decoder = json.JSONDecoder()
    data: Any = None
    found = False
    for pos, ch in enumerate(out):
        if (pos == 0 or out[pos - 1] == "\n") and ch == "{":
            try:
                data, end = decoder.raw_decode(out, pos)
            except json.JSONDecodeError:
                break
            if end == len(out) and isinstance(data, dict):
                found = True
            break
    if not found:
        raise RuntimeError(f"gws {' '.join(args[:3])}: expected valid JSON output, got: {out[:200]}")
    if "error" in data:
        detail = json.dumps(data["error"], ensure_ascii=False)[:300]
        raise RuntimeError(f"Google API error: {detail}")
    return data


def _require_drive_id(response: dict[str, Any], op: str) -> str:
    file_id = response.get("id")
    if not isinstance(file_id, str) or not file_id:
        raise RuntimeError(f"Drive {op} response missing file id")
    return file_id


def _find_existing_file_in_folder(
    parent_id: str,
    name: str,
    *,
    mime_type: str | None = None,
    cwd: Path,
    run_gws_fn: Callable[..., dict[str, Any]] = run_gws,
) -> str | None:
    valid_parent = validate_drive_id(parent_id, "folder ID")
    mime_clause = f"mimeType = '{_escape_drive_q(mime_type)}'" if mime_type else f"mimeType != '{FOLDER_MIME}'"
    query = f"trashed = false and {mime_clause} and '{valid_parent}' in parents and name = '{_escape_drive_q(name)}'"
    params: dict[str, Any] = {
        "pageSize": 100,
        "q": query,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
        "fields": "nextPageToken,files(id,name)",
    }
    matches: list[str] = []
    while True:
        resp = run_gws_fn(["drive", "files", "list", "--params", json.dumps(params)], cwd=cwd)
        files = resp.get("files") or []
        matches.extend(str(item["id"]) for item in files)
        token = resp.get("nextPageToken")
        if not token:
            break
        params["pageToken"] = token
    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple non-trashed Drive files named {name!r} in folder {valid_parent}: {matches}; pass --file-id explicitly."
        )
    return matches[0] if matches else None


def _ensure_drive_folder(
    parent_id: str,
    name: str,
    *,
    cwd: Path,
    run_gws_fn: Callable[..., dict[str, Any]] = run_gws,
) -> str:
    existing = _find_existing_file_in_folder(parent_id, name, mime_type=FOLDER_MIME, cwd=cwd, run_gws_fn=run_gws_fn)
    if existing:
        return existing
    created = run_gws_fn(
        [
            "drive",
            "files",
            "create",
            "--params",
            json.dumps({"supportsAllDrives": True, "fields": "id,name"}),
            "--json",
            json.dumps({"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}),
        ],
        cwd=cwd,
    )
    return _require_drive_id(created, "folder create")


def _upload_binary_file(
    local_path: Path,
    *,
    upload_name: str,
    staged_name: str | None = None,
    upload_mime: str,
    target_mime: str,
    parent_folder: str | None,
    target_file_id: str | None,
    protect_copy: bool,
    rename: bool,
    cwd: Path,
    fields: str,
    run_gws_fn: Callable[..., dict[str, Any]] = run_gws,
) -> tuple[str, str]:
    staged = cwd / (staged_name or upload_name)
    shutil.copyfile(local_path, staged)
    resolved_id = target_file_id
    if not resolved_id and parent_folder:
        resolved_id = _find_existing_file_in_folder(
            parent_folder, upload_name, mime_type=target_mime, cwd=cwd, run_gws_fn=run_gws_fn
        )

    if resolved_id:
        meta_body: dict[str, Any] = {}
        if rename:
            meta_body["name"] = upload_name
        if protect_copy:
            meta_body["copyRequiresWriterPermission"] = True
        cmd = [
            "drive",
            "files",
            "update",
            "--params",
            json.dumps({"fileId": resolved_id, "supportsAllDrives": True, "fields": fields}),
        ]
        if meta_body:
            cmd.extend(["--json", json.dumps(meta_body)])
        cmd.extend(["--upload", staged.name, "--upload-content-type", upload_mime])
        res = run_gws_fn(cmd, cwd=cwd)
        return _require_drive_id(res, "file update"), "updated"

    if not parent_folder:
        raise ValueError("Cannot create a new Drive file without --drive-folder.")
    create_body: dict[str, Any] = {
        "name": upload_name,
        "mimeType": target_mime,
        "parents": [parent_folder],
    }
    if protect_copy:
        create_body["copyRequiresWriterPermission"] = True
    res = run_gws_fn(
        [
            "drive",
            "files",
            "create",
            "--params",
            json.dumps({"supportsAllDrives": True, "fields": fields}),
            "--json",
            json.dumps(create_body),
            "--upload",
            staged.name,
            "--upload-content-type",
            upload_mime,
        ],
        cwd=cwd,
    )
    return _require_drive_id(res, "file create"), "created"


def file_md5_and_size(path: Path) -> tuple[str, int]:
    digest = hashlib.md5(usedforsecurity=False)
    total = 0
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def upload_deck_artifact(
    args: argparse.Namespace,
    *,
    run_gws_fn: Callable[..., dict[str, Any]] = run_gws,
) -> dict[str, Any]:
    """Validate .pdf or .pptx bytes, stage in a private tempdir, upload via gws, and verify read-back."""
    artifact_arg: Path = args.artifact
    artifact_path = artifact_arg.resolve()
    suffix = artifact_path.suffix.lower()
    if not artifact_path.is_file() or suffix not in {".pdf", ".pptx"}:
        raise ValueError(f"Input must be an existing .pdf or .pptx file: {artifact_arg}")
    if args.google_slides and suffix != ".pptx":
        raise ValueError("--google-slides requires a .pptx file (compile one with 'check --pptx' or python-pptx).")
    if not args.drive_folder and not args.file_id:
        raise ValueError("Specify --file-id <FILE_ID> or --drive-folder <FOLDER_ID>.")

    expected_slides: int | None = None
    if suffix == ".pdf":
        with artifact_path.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise ValueError(f"File does not start with valid %PDF- header: {artifact_path}")
        upload_mime, target_mime, default_name = PDF_MIME, PDF_MIME, artifact_path.name
    else:
        expected_slides, pptx_title = inspect_pptx_metadata(artifact_path)
        upload_mime = PPTX_MIME
        target_mime = GOOGLE_SLIDES_MIME if args.google_slides else PPTX_MIME
        if args.google_slides:
            default_name = (
                pptx_title if (pptx_title and pptx_title not in {"Deck", artifact_path.stem}) else artifact_path.stem
            )
        else:
            default_name = artifact_path.name

    local_md5, local_size = file_md5_and_size(artifact_path)
    if local_size == 0:
        raise ValueError(f"Artifact file is empty: {artifact_path}")

    source_files: list[Path] = []
    if args.source_dir is not None:
        source_root = args.source_dir.resolve()
        if not source_root.is_dir():
            raise ValueError(f"--source-dir does not exist or is not a directory: {args.source_dir}")
        source_files = collect_source_files(source_root)
        if not source_files:
            raise ValueError(f"No .typ or .py source files found under --source-dir: {args.source_dir}")

    valid_folder = validate_drive_id(args.drive_folder, "folder ID") if args.drive_folder else None
    valid_file_id = validate_drive_id(args.file_id, "file ID") if args.file_id else None
    if args.google_slides:
        upload_name = validate_presentation_title(args.name or default_name)
        staged_name: str | None = "deck.pptx"
    else:
        upload_name = validate_upload_name(args.name or default_name)
        staged_name = None

    if args.dry_run:
        payload: dict[str, Any] = {
            "dry_run": True,
            "artifact": str(artifact_path),
            "name": upload_name,
            "target_mime": target_mime,
            "google_slides": args.google_slides,
            "target_file_id": valid_file_id,
            "drive_folder": valid_folder,
            "local_md5": local_md5,
            "local_size": local_size,
            "protect_copy": args.protect_copy,
        }
        if expected_slides is not None:
            payload["expected_slides"] = expected_slides
        if source_files and args.source_dir is not None:
            payload["source_files"] = [str(p.relative_to(args.source_dir.resolve())) for p in source_files]
        return payload

    fields = "id,name,mimeType,version,modifiedTime,webViewLink,md5Checksum,size,copyRequiresWriterPermission,trashed,parents"
    with tempfile.TemporaryDirectory(prefix="typst-deck-upload-") as tmp_dir_str:
        gws_dir = Path(tmp_dir_str)
        uploaded_id, operation = _upload_binary_file(
            artifact_path,
            upload_name=upload_name,
            staged_name=staged_name,
            upload_mime=upload_mime,
            target_mime=target_mime,
            parent_folder=valid_folder,
            target_file_id=valid_file_id,
            protect_copy=args.protect_copy,
            rename=bool(args.name),
            cwd=gws_dir,
            fields=fields,
            run_gws_fn=run_gws_fn,
        )
        verified = run_gws_fn(
            [
                "drive",
                "files",
                "get",
                "--params",
                json.dumps({"fileId": uploaded_id, "supportsAllDrives": True, "fields": fields}),
            ],
            cwd=gws_dir,
        )
        if verified.get("trashed") is True:
            raise RuntimeError(f"Uploaded file is marked trashed in Drive: {uploaded_id}")

        slides_count: int | None = None
        if args.google_slides:
            remote_mime = str(verified.get("mimeType") or "")
            if remote_mime != GOOGLE_SLIDES_MIME:
                raise RuntimeError(f"Expected Google Slides mimeType {GOOGLE_SLIDES_MIME}, got {remote_mime!r}")
            slides_doc = run_gws_fn(
                [
                    "slides",
                    "presentations",
                    "get",
                    "--params",
                    json.dumps({"presentationId": uploaded_id, "fields": "presentationId,title,slides(objectId)"}),
                ],
                cwd=gws_dir,
            )
            slides_count = len(slides_doc.get("slides") or [])
            if slides_count != expected_slides:
                raise RuntimeError(
                    f"Google Slides slide-count mismatch: expected {expected_slides}, got {slides_count}"
                )
        else:
            remote_md5 = str(verified.get("md5Checksum") or "")
            remote_size = int(verified.get("size") or 0)
            if remote_md5 != local_md5 or remote_size != local_size:
                raise RuntimeError(
                    f"Integrity mismatch after upload: local ({local_md5}, {local_size} B) != remote ({remote_md5}, {remote_size} B)."
                )

        synced_sources = _sync_source_files(
            source_files,
            args.source_dir.resolve() if args.source_dir else artifact_path.parent,
            artifact_path.stem,
            valid_folder or next(iter(verified.get("parents") or []), None),
            cwd=gws_dir,
            run_gws_fn=run_gws_fn,
        )

    result: dict[str, Any] = {
        "ok": True,
        "operation": operation,
        "file_id": uploaded_id,
        "name": verified.get("name"),
        "mimeType": verified.get("mimeType"),
        "web_view_link": verified.get("webViewLink"),
        "copyRequiresWriterPermission": verified.get("copyRequiresWriterPermission"),
        "reminder": "Verify ACLs via `gws drive permissions list` before widening access.",
    }
    if args.google_slides:
        result["slide_count"] = slides_count
    else:
        result["md5Checksum"] = str(verified.get("md5Checksum") or "")
        result["size"] = int(verified.get("size") or 0)
    if synced_sources:
        result["synced_sources"] = synced_sources
    return result


def _sync_source_files(
    source_files: list[Path],
    source_root: Path,
    slug: str,
    parent_folder: str | None,
    *,
    cwd: Path,
    run_gws_fn: Callable[..., dict[str, Any]],
) -> list[dict[str, str]]:
    if not source_files:
        return []
    if not parent_folder:
        raise RuntimeError("Cannot sync --source-dir without a resolved parent Drive folder ID.")
    assets_id = _ensure_drive_folder(str(parent_folder), "assets", cwd=cwd, run_gws_fn=run_gws_fn)
    slug_folder_id = _ensure_drive_folder(assets_id, slug, cwd=cwd, run_gws_fn=run_gws_fn)
    synced: list[dict[str, str]] = []
    for src in source_files:
        rel_name = validate_upload_name(src.relative_to(source_root).as_posix().replace("/", "__"))
        src_md5, src_size = file_md5_and_size(src)
        src_id, src_op = _upload_binary_file(
            src,
            upload_name=rel_name,
            upload_mime="text/plain",
            target_mime="text/plain",
            parent_folder=slug_folder_id,
            target_file_id=None,
            protect_copy=False,
            rename=False,
            cwd=cwd,
            fields="id,md5Checksum,size",
            run_gws_fn=run_gws_fn,
        )
        src_get = run_gws_fn(
            [
                "drive",
                "files",
                "get",
                "--params",
                json.dumps({"fileId": src_id, "supportsAllDrives": True, "fields": "id,md5Checksum,size"}),
            ],
            cwd=cwd,
        )
        if str(src_get.get("md5Checksum") or "") != src_md5 or int(src_get.get("size") or 0) != src_size:
            raise RuntimeError(f"Source integrity mismatch for {rel_name}")
        synced.append({"name": rel_name, "file_id": src_id, "operation": src_op})
    return synced
