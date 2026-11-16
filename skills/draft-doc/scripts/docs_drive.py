"""Validate Google Drive identifiers and upload compiled Docs Markdown and asset bundles via gws."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Protocol

DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,128}$")
DOC_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ASSET_MIME_TYPES = {
    ".md": "text/markdown",
    ".mmd": "text/plain",
    ".svg": "image/svg+xml",
    ".typ": "text/plain",
    ".png": "image/png",
}


class GwsRunner(Protocol):
    """Callable matching `run_gws` for executing gws commands in a working directory."""

    def __call__(self, args: list[str], *, cwd: Path | None = None) -> dict[str, Any]: ...


def _validate_drive_id(value: str, label: str = "Drive ID") -> str:
    """Validate a Google Drive file or folder ID before embedding in API queries."""
    cleaned = value.strip()
    if not DRIVE_ID_RE.fullmatch(cleaned):
        msg = f"Invalid {label}: {value!r}"
        raise ValueError(msg)
    return cleaned


def _escape_drive_q(value: str) -> str:
    """Escape backslashes and single quotes for Google Drive q filter strings."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _validate_doc_slug(value: str) -> str:
    """Validate a Drive assets/<doc-slug> directory name against path traversal and empty slugs."""
    cleaned = value.strip()
    if not DOC_SLUG_RE.fullmatch(cleaned):
        msg = f"Invalid doc slug {value!r}: expected [A-Za-z0-9][A-Za-z0-9._-]{{0,127}}"
        raise ValueError(msg)
    return cleaned


def _validate_doc_name(value: str) -> str:
    """Validate a remote Drive document filename against empty names, leading hyphens, and path separators."""
    cleaned = value.strip()
    if not cleaned or cleaned in {".", ".."} or cleaned.startswith("-") or "/" in cleaned or "\\" in cleaned:
        msg = f"Invalid doc name {value!r}: expected a plain filename without path separators or leading '-'."
        raise ValueError(msg)
    return cleaned


def _slugify_doc(name: str) -> str:
    """Derive a clean Drive assets/<doc-slug> directory name from a document filename."""
    stem = name.removesuffix(".src.md").removesuffix(".gdoc.md").removesuffix(".md")
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", stem).strip(".-_") or "document"


def run_gws(args: list[str], *, cwd: Path | None = None) -> dict[str, Any]:
    """Execute a gws CLI command with --format json and return the parsed JSON object."""
    gws_bin = shutil.which("gws")
    if not gws_bin:
        msg = "`gws` not found in PATH; install @googleworkspace/cli (e.g. `mise install`)."
        raise RuntimeError(msg)
    proc = subprocess.run(  # noqa: S603 - fixed gws binary and validated arguments
        [gws_bin, *args, "--format", "json"],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        detail = " ".join((proc.stderr or proc.stdout).split())[-300:]
        msg = f"gws {' '.join(args[:3])} failed (exit {proc.returncode}): {detail}"
        raise RuntimeError(msg)
    out = proc.stdout.strip()
    if not out:
        msg = f"gws {' '.join(args[:3])}: expected JSON object on stdout"
        raise RuntimeError(msg)
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
        msg = f"gws {' '.join(args[:3])}: expected valid JSON object on stdout, got: {out[:200]}"
        raise RuntimeError(msg)
    if "error" in data:
        msg = f"Google API error: {data['error']}"
        raise RuntimeError(msg)
    return data


def _require_drive_id(response: dict[str, Any], op: str) -> str:
    file_id = response.get("id")
    if not isinstance(file_id, str) or not file_id:
        msg = f"Drive {op} response missing file id"
        raise RuntimeError(msg)
    return file_id


def _ensure_drive_folder(
    parent_id: str,
    folder_name: str,
    gws_dir: Path,
    *,
    run_gws_fn: GwsRunner | None = None,
) -> str:
    """Find or create a child folder named folder_name inside parent_id."""
    call_gws = run_gws_fn or run_gws
    valid_parent = _validate_drive_id(parent_id, "parent folder ID")
    q = (
        "trashed = false and mimeType = 'application/vnd.google-apps.folder' "
        f"and '{valid_parent}' in parents and name = '{_escape_drive_q(folder_name)}'"
    )
    params: dict[str, Any] = {
        "pageSize": 100,
        "q": q,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
        "fields": "nextPageToken,files(id,name)",
    }
    matches: list[str] = []
    while True:
        resp = call_gws(["drive", "files", "list", "--params", json.dumps(params)], cwd=gws_dir)
        matches.extend(str(item["id"]) for item in resp.get("files") or [] if isinstance(item, dict) and "id" in item)
        token = resp.get("nextPageToken")
        if not token:
            break
        params["pageToken"] = token
    if len(matches) > 1:
        msg = (
            f"Multiple non-trashed Drive folders named {folder_name!r} in folder {valid_parent}: "
            f"{matches}; deduplicate them in Drive first."
        )
        raise RuntimeError(msg)
    if matches:
        return matches[0]
    created = call_gws(
        [
            "drive",
            "files",
            "create",
            "--params",
            json.dumps({"supportsAllDrives": True, "fields": "id,name"}),
            "--json",
            json.dumps(
                {
                    "name": folder_name,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [valid_parent],
                }
            ),
        ],
        cwd=gws_dir,
    )
    return _require_drive_id(created, "folder create")


def _list_folder_files(
    parent_id: str,
    gws_dir: Path,
    *,
    run_gws_fn: GwsRunner | None = None,
) -> dict[str, list[str]]:
    """Return {name: [file_id, ...]} for non-trashed non-folder files inside parent_id, across all pages."""
    call_gws = run_gws_fn or run_gws
    valid_parent = _validate_drive_id(parent_id, "folder ID")
    q = f"trashed = false and mimeType != 'application/vnd.google-apps.folder' and '{valid_parent}' in parents"
    params: dict[str, Any] = {
        "pageSize": 100,
        "q": q,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
        "fields": "nextPageToken,files(id,name)",
    }
    found: dict[str, list[str]] = {}
    while True:
        resp = call_gws(["drive", "files", "list", "--params", json.dumps(params)], cwd=gws_dir)
        for item in resp.get("files") or []:
            if "id" in item and "name" in item:
                found.setdefault(str(item["name"]), []).append(str(item["id"]))
        if not resp.get("nextPageToken"):
            return found
        params["pageToken"] = resp["nextPageToken"]


def _get_drive_file(
    file_id: str,
    gws_dir: Path,
    *,
    run_gws_fn: GwsRunner | None = None,
) -> dict[str, Any]:
    """Return the id, name, and parents of an existing Drive file."""
    call_gws = run_gws_fn or run_gws
    params = {"fileId": _validate_drive_id(file_id, "file ID"), "supportsAllDrives": True, "fields": "id,name,parents"}
    return call_gws(["drive", "files", "get", "--params", json.dumps(params)], cwd=gws_dir)


def _upsert_drive_file(
    local_path: Path,
    *,
    name: str,
    content_type: str,
    gws_dir: Path,
    parent_id: str | None = None,
    file_id: str | None = None,
    existing_by_name: dict[str, list[str]] | None = None,
    rename: bool = False,
    run_gws_fn: GwsRunner | None = None,
) -> dict[str, Any]:
    """Create or update a file in Google Drive; updates keep the File ID and rename only when asked."""
    call_gws = run_gws_fn or run_gws
    if file_id:
        target_id: str | None = file_id
    else:
        matches = (existing_by_name or {}).get(name, [])
        if len(matches) > 1:
            msg = (
                f"Multiple non-trashed Drive files named {name!r} in folder {parent_id}: "
                f"{matches}; pass --file-id explicitly."
            )
            raise RuntimeError(msg)
        target_id = matches[0] if matches else None
    fields = "id,name,mimeType,version,modifiedTime,webViewLink"
    # gws rejects --upload paths outside its working directory, so stage the file in the run's gws
    # directory and upload it by bare name from there, like every other gws call of the run.
    staged_name = (
        f"upload-{local_path.name.lstrip('-') or 'file'}" if local_path.name.startswith("-") else local_path.name
    )
    staged = gws_dir / staged_name
    if staged.resolve() != local_path.resolve():
        shutil.copyfile(local_path, staged)
    upload = ["--upload", staged_name, "--upload-content-type", content_type]
    if target_id:
        valid_id = _validate_drive_id(target_id, "file ID")
        params = json.dumps({"fileId": valid_id, "supportsAllDrives": True, "fields": fields})
        body = ["--json", json.dumps({"name": name})] if rename else []
        return call_gws(
            ["drive", "files", "update", "--params", params, *body, *upload],
            cwd=gws_dir,
        )
    if not parent_id:
        msg = f"Cannot create {name!r} without a target Drive folder ID."
        raise ValueError(msg)
    valid_parent = _validate_drive_id(parent_id, "folder ID")
    return call_gws(
        [
            "drive",
            "files",
            "create",
            "--params",
            json.dumps({"supportsAllDrives": True, "fields": fields}),
            "--json",
            json.dumps({"name": name, "mimeType": content_type, "parents": [valid_parent]}),
            *upload,
        ],
        cwd=gws_dir,
    )


def prepare_drive_context(
    out_name: str,
    gws_dir: Path,
    drive_folder: str | None = None,
    file_id: str | None = None,
    doc_name: str | None = None,
    doc_slug: str | None = None,
    *,
    run_gws_fn: GwsRunner | None = None,
) -> tuple[str | None, str, dict[str, Any] | None]:
    """Validate Drive flags, fetch existing file metadata if needed, and resolve doc_name and doc_slug."""
    if drive_folder is not None:
        _validate_drive_id(drive_folder, "folder ID")
    if file_id is not None:
        _validate_drive_id(file_id, "file ID")
    validated_name = _validate_doc_name(doc_name) if doc_name is not None else None
    if doc_slug is not None:
        _validate_doc_slug(doc_slug)
    existing_file = _get_drive_file(file_id, gws_dir, run_gws_fn=run_gws_fn) if file_id and not validated_name else None
    drive_name = validated_name or (existing_file or {}).get("name") or out_name
    resolved_slug = _validate_doc_slug(doc_slug) if doc_slug is not None else _slugify_doc(str(drive_name))
    return validated_name, resolved_slug, existing_file


def upload_to_drive(
    compiled_md: Path,
    asset_paths: list[Path],
    *,
    gws_dir: Path,
    drive_folder: str | None = None,
    file_id: str | None = None,
    doc_name: str | None = None,
    doc_slug: str | None = None,
    existing_file: dict[str, Any] | None = None,
    run_gws_fn: GwsRunner | None = None,
) -> dict[str, Any]:
    """Upload the compiled .md file and its assets/<doc-slug>/ bundle to Google Drive.

    gws loads a `.env` from its working directory upward, so every gws call runs from gws_dir, a private
    directory: metadata reads, uploads, and read-backs then resolve the same account.
    """
    call_gws = run_gws_fn or run_gws
    if not drive_folder and not file_id:
        msg = "Provide --drive-folder <FOLDER_ID> and/or --file-id <FILE_ID> to upload to Google Drive."
        raise ValueError(msg)

    parent_folder_id = _validate_drive_id(drive_folder, "folder ID") if drive_folder else None
    validated_doc_name = _validate_doc_name(doc_name) if doc_name is not None else None
    resolved_name = validated_doc_name or compiled_md.name
    if file_id:
        # Keep the live document's name and location unless --doc-name asks for a rename.
        existing = existing_file or _get_drive_file(file_id, gws_dir, run_gws_fn=call_gws)
        if not parent_folder_id and existing.get("parents"):
            parent_folder_id = _validate_drive_id(str(existing["parents"][0]), "folder ID")
        if not validated_doc_name and existing.get("name"):
            resolved_name = str(existing["name"])
    if not resolved_name.endswith(".md"):
        resolved_name = f"{resolved_name}.md"

    resolved_slug = _validate_doc_slug(doc_slug) if doc_slug is not None else _slugify_doc(resolved_name)
    existing_in_parent = (
        _list_folder_files(parent_folder_id, gws_dir, run_gws_fn=call_gws) if (parent_folder_id and not file_id) else {}
    )
    doc_result = _upsert_drive_file(
        compiled_md,
        name=resolved_name,
        content_type="text/markdown",
        gws_dir=gws_dir,
        parent_id=parent_folder_id,
        file_id=file_id,
        existing_by_name=existing_in_parent,
        rename=bool(file_id and validated_doc_name),
        run_gws_fn=call_gws,
    )
    uploaded_file_id = _require_drive_id(doc_result, "file upload")

    assets_folder_id: str | None = None
    uploaded_assets: list[dict[str, Any]] = []
    warning: str | None = None
    if asset_paths and not parent_folder_id:
        # Only reachable with --file-id alone, when Drive lists no `parents` for the file.
        names = ", ".join(path.name for path in asset_paths)
        warning = (
            f"Skipped {len(asset_paths)} asset upload(s) ({names}): Drive returned no parent folder for file "
            f"{uploaded_file_id}, so assets/{resolved_slug}/ has no location; rerun with --drive-folder <FOLDER_ID> "
            "to upload them."
        )
    if parent_folder_id and asset_paths:
        assets_root_id = _ensure_drive_folder(parent_folder_id, "assets", gws_dir, run_gws_fn=call_gws)
        assets_folder_id = _ensure_drive_folder(assets_root_id, resolved_slug, gws_dir, run_gws_fn=call_gws)
        existing_assets = _list_folder_files(assets_folder_id, gws_dir, run_gws_fn=call_gws)
        for asset_path in asset_paths:
            if not asset_path.is_file():
                continue
            mime = ASSET_MIME_TYPES.get(asset_path.suffix.lower(), "application/octet-stream")
            res = _upsert_drive_file(
                asset_path,
                name=asset_path.name,
                content_type=mime,
                gws_dir=gws_dir,
                parent_id=assets_folder_id,
                existing_by_name=existing_assets,
                run_gws_fn=call_gws,
            )
            uploaded_assets.append(
                {
                    "id": res.get("id"),
                    "name": res.get("name", asset_path.name),
                    "mimeType": res.get("mimeType", mime),
                }
            )

    return {
        "file_id": uploaded_file_id,
        "name": doc_result.get("name", resolved_name),
        "docs_url": f"https://docs.google.com/document/d/{uploaded_file_id}/edit",
        "web_view_link": doc_result.get("webViewLink"),
        "assets_folder_id": assets_folder_id,
        "assets_folder_path": f"assets/{resolved_slug}" if assets_folder_id else None,
        "assets_folder_url": f"https://drive.google.com/drive/folders/{assets_folder_id}" if assets_folder_id else None,
        "uploaded_assets": uploaded_assets,
        "warning": warning,
    }
