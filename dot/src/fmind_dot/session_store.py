"""Immutable, versioned storage for normalized agent transcripts."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import secrets
import stat
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

SESSION_SCHEMA_VERSION = 1
SESSION_PARSER_VERSION = "1"
SESSION_STORE_VERSION = "v1"
_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]+$")

Completeness = Literal["complete", "partial"]
IngestionStatus = Literal["ingested", "duplicate", "skipped"]


def _is_safe_component(value: str) -> bool:
    return bool(_SESSION_ID.fullmatch(value))


@dataclass
class SessionLog:
    """One source-neutral conversation record."""

    ts: str
    agent: str
    sid: str
    role: str
    content: str
    cwd: str = ""
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "ts": self.ts,
            "agent": self.agent,
            "sid": self.sid,
            "role": self.role,
            "content": self.content,
        }
        if self.cwd:
            value["cwd"] = self.cwd
        if self.model:
            value["model"] = self.model
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SessionLog:
        required = ("ts", "agent", "sid", "role", "content")
        if any(not isinstance(value.get(key), str) for key in required):
            raise ValueError("invalid normalized transcript record")
        cwd = value.get("cwd", "")
        model = value.get("model", "")
        if not isinstance(cwd, str) or not isinstance(model, str):
            raise ValueError("invalid normalized transcript record")
        return cls(*(value[key] for key in required), cwd=cwd, model=model)


@dataclass
class SessionSource:
    """Evidence retained about the raw source used for one generation."""

    type: str = ""
    fingerprint: str = ""
    high_water: str = ""
    completeness: Completeness | Literal[""] = ""
    malformed: int = 0
    skipped: int = 0


@dataclass
class SessionManifest:
    """Integrity and provenance metadata for an immutable generation."""

    parser_version: str
    agent: str
    session_id: str
    lineage_id: str
    source_type: str
    source_fingerprint: str
    high_water_mark: str
    ingested_at: str
    completeness: Completeness
    transcript_sha256: str
    schema_version: int
    record_count: int
    malformed_records: int
    skipped_records: int

    def to_dict(self) -> dict[str, Any]:
        # Preserve the v1 Go manifest field order for byte-stable output.
        result: dict[str, Any] = {
            "parser_version": self.parser_version,
            "agent": self.agent,
            "session_id": self.session_id,
            "lineage_id": self.lineage_id,
            "source_type": self.source_type,
            "source_fingerprint": self.source_fingerprint,
        }
        if self.high_water_mark:
            result["high_water_mark"] = self.high_water_mark
        result.update(
            {
                "ingested_at": self.ingested_at,
                "completeness": self.completeness,
                "transcript_sha256": self.transcript_sha256,
                "schema_version": self.schema_version,
                "record_count": self.record_count,
                "malformed_records": self.malformed_records,
                "skipped_records": self.skipped_records,
            }
        )
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SessionManifest:
        try:
            completeness = value["completeness"]
            if completeness not in {"complete", "partial"}:
                raise ValueError("invalid completeness")
            return cls(
                parser_version=_string(value, "parser_version"),
                agent=_string(value, "agent"),
                session_id=_string(value, "session_id"),
                lineage_id=_string(value, "lineage_id"),
                source_type=_string(value, "source_type"),
                source_fingerprint=_string(value, "source_fingerprint"),
                high_water_mark=_string(value, "high_water_mark", required=False),
                ingested_at=_string(value, "ingested_at"),
                completeness=completeness,
                transcript_sha256=_string(value, "transcript_sha256"),
                schema_version=_integer(value, "schema_version"),
                record_count=_integer(value, "record_count"),
                malformed_records=_integer(value, "malformed_records"),
                skipped_records=_integer(value, "skipped_records"),
            )
        except (KeyError, TypeError) as error:
            raise ValueError("invalid session manifest") from error


@dataclass
class SessionIngestionResult:
    status: IngestionStatus
    lineage_id: str
    generation_id: str = ""
    manifest: SessionManifest | None = None


def _string(value: dict[str, Any], key: str, *, required: bool = True) -> str:
    item = value.get(key, "")
    if not isinstance(item, str) or (required and not item):
        raise ValueError(f"invalid manifest field {key}")
    return item


def _integer(value: dict[str, Any], key: str) -> int:
    item = value[key]
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        raise ValueError(f"invalid manifest field {key}")
    return item


def session_digest(*values: str) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode())
        digest.update(b"\0")
    return digest.hexdigest()


def session_lineage_id(agent: str, session_id: str) -> str:
    return session_digest(agent, session_id)


def session_generation_id(source_fingerprint: str) -> str:
    return session_digest(SESSION_PARSER_VERSION, source_fingerprint)


def fingerprint_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fingerprint_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _go_json_bytes(value: object, *, escape_html: bool) -> bytes:
    content = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if escape_html:
        for character, escaped in (("&", r"\u0026"), ("<", r"\u003c"), (">", r"\u003e")):
            content = content.replace(character, escaped)
    # encoding/json escapes these separators even when HTML escaping is disabled.
    for character, escaped in ((chr(0x2028), r"\u2028"), (chr(0x2029), r"\u2029")):
        content = content.replace(character, escaped)
    return content.encode("utf-8")


def fingerprint_json(value: object) -> str:
    # Preserve encoding/json's default escaping because this digest is part of
    # the existing immutable v1 identity for SQLite-backed sources.
    return fingerprint_bytes(_go_json_bytes(value, escape_html=True))


def marshal_session_logs(logs: list[SessionLog]) -> bytes:
    return b"".join(_go_json_bytes(log.to_dict(), escape_html=False) + b"\n" for log in logs)


def fingerprint_logs(logs: list[SessionLog]) -> str:
    return fingerprint_bytes(marshal_session_logs(logs))


def session_high_water(logs: list[SessionLog]) -> str:
    return max((log.ts for log in logs), default="")


def session_store_root() -> Path:
    return Path.home() / ".agents" / "sessions" / SESSION_STORE_VERSION


def _open_directory_at(parent: int, name: str, path: Path, *, secure: bool) -> int:
    created = False
    try:
        os.mkdir(name, 0o700, dir_fd=parent)
        created = True
    except FileExistsError:
        pass
    if created:
        # Persist each new path component before a later raw-source prune can
        # treat a descendant generation as durable successor evidence.
        os.fsync(parent)
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise ValueError(f"refusing symbolic link or non-directory in session store: {path}") from error
        raise
    try:
        if secure:
            os.fchmod(descriptor, 0o700)  # nosemgrep: insecure-file-permissions
        if created:
            os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _secure_directories(agent: str, lineage: str) -> int:
    """Open the lineage directory without trusting mutable path components."""
    home = Path.home()
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    current = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    path = home
    try:
        for name, secure in (
            (".agents", False),
            ("sessions", False),
            (SESSION_STORE_VERSION, True),
            (agent, True),
            (lineage, True),
        ):
            path /= name
            child = _open_directory_at(current, name, path, secure=secure)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _require_current_lineage(agent: str, lineage: str, expected: int) -> None:
    try:
        current = _secure_directories(agent, lineage)
    except (OSError, ValueError) as error:
        raise ValueError("session store lineage changed during ingestion") from error
    try:
        expected_metadata = os.fstat(expected)
        current_metadata = os.fstat(current)
        if (expected_metadata.st_dev, expected_metadata.st_ino) != (current_metadata.st_dev, current_metadata.st_ino):
            raise ValueError("session store lineage changed during ingestion")
    finally:
        os.close(current)


def _write_owner_only_at(directory: int, name: str, content: bytes) -> None:
    descriptor = os.open(name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)


def _require_private_metadata(metadata: os.stat_result, path: Path, *, directory: bool) -> None:
    expected_type = stat.S_ISDIR if directory else stat.S_ISREG
    kind = "directory" if directory else "file"
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError(f"session generation {kind} is a symbolic link: {path}")
    if not expected_type(metadata.st_mode):
        raise ValueError(f"session generation path is not a {kind}: {path}")
    expected_mode = 0o700 if directory else 0o600
    if stat.S_IMODE(metadata.st_mode) != expected_mode:
        raise ValueError(f"session generation {kind} is not owner-only: {path}")
    if not directory and metadata.st_nlink != 1:
        raise ValueError(f"session generation file has multiple hard links: {path}")


def _require_private_path(path: Path, *, directory: bool) -> None:
    _require_private_metadata(path.lstat(), path, directory=directory)


def _open_private_directory_at(parent: int, name: str, path: Path) -> int:
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise ValueError(f"session generation directory is a symbolic link or non-directory: {path}") from error
        raise
    try:
        _require_private_metadata(os.fstat(descriptor), path, directory=True)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _open_existing_lineage(agent: str, lineage: str) -> int | None:
    """Open an existing lineage through stable descriptors without creating it."""
    home = Path.home()
    try:
        current = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    path = home
    try:
        for name, private in (
            (".agents", False),
            ("sessions", False),
            (SESSION_STORE_VERSION, True),
            (agent, True),
            (lineage, True),
        ):
            path /= name
            try:
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            except FileNotFoundError:
                return None
            except OSError as error:
                if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                    raise ValueError(f"refusing symbolic link or non-directory in session store: {path}") from error
                raise
            try:
                if private:
                    _require_private_metadata(os.fstat(child), path, directory=True)
            except BaseException:
                os.close(child)
                raise
            os.close(current)
            current = child
        result = current
        current = -1
        return result
    finally:
        if current >= 0:
            os.close(current)


def _create_private_directory_at(parent: int, name: str, path: Path) -> int:
    os.mkdir(name, 0o700, dir_fd=parent)
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    except BaseException:
        with suppress(FileNotFoundError):
            os.rmdir(name, dir_fd=parent)
        raise
    try:
        os.fchmod(descriptor, 0o700)  # nosemgrep: insecure-file-permissions
        _require_private_metadata(os.fstat(descriptor), path, directory=True)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _read_owner_only_at(directory: int, name: str, path: Path) -> bytes:
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise ValueError(f"session generation file is a symbolic link: {path}") from error
        raise
    try:
        _require_private_metadata(os.fstat(descriptor), path, directory=False)
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(descriptor)


def _open_absolute_directory(path: Path) -> int:
    """Open an absolute directory one component at a time without following links."""
    if not path.is_absolute():
        raise ValueError(f"publication parent must be absolute: {path}")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path.anchor, flags)
    try:
        for component in path.parts[1:]:
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        result = descriptor
        descriptor = -1
        return result
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _require_current_directory(path: Path, expected: int, operation: str) -> None:
    try:
        current = _open_absolute_directory(path)
    except OSError as error:
        raise ValueError(f"{operation} parent changed during publication: {path}") from error
    try:
        expected_info = os.fstat(expected)
        current_info = os.fstat(current)
        if (expected_info.st_dev, expected_info.st_ino) != (current_info.st_dev, current_info.st_ino):
            raise ValueError(f"{operation} parent changed during publication: {path}")
    finally:
        os.close(current)


def publish_owner_only(path: Path, content: bytes) -> None:
    """Atomically replace a private file, safe for concurrent hook writers."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = _open_absolute_directory(path.parent.absolute())
    descriptor = -1
    temp_name = f".{path.name}.{secrets.token_hex(16)}"
    try:
        descriptor = os.open(
            temp_name,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.close(descriptor)
        descriptor = -1
        os.replace(temp_name, path.name, src_dir_fd=directory, dst_dir_fd=directory)
        temp_name = ""
        os.fsync(directory)
        _require_current_directory(path.parent.absolute(), directory, "target")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temp_name:
            with suppress(FileNotFoundError):
                os.unlink(temp_name, dir_fd=directory)
        os.close(directory)


def _parse_session_manifest(content: str | bytes) -> SessionManifest:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid session manifest: {error}") from error
    if not isinstance(value, dict):
        raise ValueError("invalid session manifest")
    return SessionManifest.from_dict(value)


def read_session_manifest(path: Path) -> SessionManifest:
    manifest_path = path / "manifest.json"
    _require_private_path(path, directory=True)
    _require_private_path(manifest_path, directory=False)
    return _parse_session_manifest(manifest_path.read_text(encoding="utf-8"))


def _validate_transcript(transcript: bytes, manifest: SessionManifest) -> list[SessionLog]:
    if fingerprint_bytes(transcript) != manifest.transcript_sha256:
        raise ValueError("session transcript fingerprint mismatch")
    logs: list[SessionLog] = []
    try:
        text = transcript.decode()
    except UnicodeDecodeError as error:
        raise ValueError("invalid normalized transcript record") from error
    decoder = json.JSONDecoder()
    position = 0
    record_number = 0
    while position < len(text):
        while position < len(text) and text[position].isspace():
            position += 1
        if position >= len(text):
            break
        record_number += 1
        try:
            value, position = decoder.raw_decode(text, position)
            if not isinstance(value, dict):
                raise ValueError
            log = SessionLog.from_dict(value)
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"invalid normalized transcript record {record_number}") from error
        if log.agent != manifest.agent or log.sid != manifest.session_id:
            raise ValueError("normalized transcript record has mismatched lineage")
        logs.append(log)
    if len(logs) != manifest.record_count:
        raise ValueError(f"normalized transcript contains {len(logs)} records, expected {manifest.record_count}")
    high_water = session_high_water(logs)
    if high_water != manifest.high_water_mark:
        raise ValueError(
            f"normalized transcript high-water mark {high_water!r} does not match manifest {manifest.high_water_mark!r}"
        )
    return logs


def validate_session_generation(path: Path, expected: SessionManifest) -> list[SessionLog]:
    manifest = read_session_manifest(path)
    if manifest != expected:
        raise ValueError("session manifest did not round-trip")
    transcript_path = path / "transcript.jsonl"
    _require_private_path(transcript_path, directory=False)
    return _validate_transcript(transcript_path.read_bytes(), manifest)


def _validate_session_generation_at(
    generation: int, path: Path, expected: SessionManifest | None = None
) -> tuple[SessionManifest, list[SessionLog]]:
    manifest = _parse_session_manifest(_read_owner_only_at(generation, "manifest.json", path / "manifest.json"))
    if expected is not None and manifest != expected:
        raise ValueError("session manifest did not round-trip")
    transcript = _read_owner_only_at(generation, "transcript.jsonl", path / "transcript.jsonl")
    return manifest, _validate_transcript(transcript, manifest)


def _same_immutable_identity(existing: SessionManifest, expected: SessionManifest) -> bool:
    return (
        existing.schema_version,
        existing.parser_version,
        existing.agent,
        existing.session_id,
        existing.lineage_id,
        existing.source_fingerprint,
    ) == (
        expected.schema_version,
        expected.parser_version,
        expected.agent,
        expected.session_id,
        expected.lineage_id,
        expected.source_fingerprint,
    )


def _normalize_logs(agent: str, session_id: str, logs: list[SessionLog]) -> None:
    if not _is_safe_component(session_id):
        raise ValueError(f"invalid session_id format: {session_id!r}")
    for number, log in enumerate(logs, start=1):
        if log.agent != agent or log.sid != session_id:
            raise ValueError(f"session record {number} does not match its lineage")
    active = ""
    for log in logs:
        if log.model:
            active = log.model
        elif active:
            log.model = active
    active = ""
    for log in reversed(logs):
        if log.model:
            active = log.model
        elif active:
            log.model = active


def stored_generation(agent: str, session_id: str, source_fingerprint: str) -> SessionManifest | None:
    if not source_fingerprint or not _is_safe_component(agent) or not _is_safe_component(session_id):
        return None
    lineage = session_lineage_id(agent, session_id)
    path = session_store_root() / agent / lineage / session_generation_id(source_fingerprint)
    lineage_descriptor = _open_existing_lineage(agent, lineage)
    if lineage_descriptor is None:
        return None
    try:
        try:
            generation_descriptor = _open_private_directory_at(lineage_descriptor, path.name, path)
        except FileNotFoundError:
            return None
        try:
            try:
                manifest = _parse_session_manifest(
                    _read_owner_only_at(generation_descriptor, "manifest.json", path / "manifest.json")
                )
            except OSError as error:
                raise ValueError(f"stored session generation could not be read: {path}") from error
            immutable = (
                manifest.schema_version == SESSION_SCHEMA_VERSION
                and manifest.parser_version == SESSION_PARSER_VERSION
                and manifest.agent == agent
                and manifest.session_id == session_id
                and manifest.lineage_id == lineage
                and manifest.source_fingerprint == source_fingerprint
            )
            if not immutable:
                raise ValueError("stored session generation does not match its immutable identity")
            try:
                _validate_session_generation_at(generation_descriptor, path, manifest)
            except OSError as error:
                raise ValueError(f"stored session generation could not be read: {path}") from error

            current_lineage = _open_existing_lineage(agent, lineage)
            if current_lineage is None:
                raise ValueError("session store lineage changed during validation")
            try:
                expected_metadata = os.fstat(lineage_descriptor)
                current_metadata = os.fstat(current_lineage)
                if (expected_metadata.st_dev, expected_metadata.st_ino) != (
                    current_metadata.st_dev,
                    current_metadata.st_ino,
                ):
                    raise ValueError("session store lineage changed during validation")
            finally:
                os.close(current_lineage)
            return manifest
        finally:
            os.close(generation_descriptor)
    finally:
        os.close(lineage_descriptor)


def ingest_session(
    agent: str, session_id: str, logs: list[SessionLog], source: SessionSource | None = None
) -> SessionIngestionResult:
    """Validate and atomically publish one immutable transcript generation."""
    if not _is_safe_component(agent):
        raise ValueError(f"invalid agent format: {agent!r}")
    source = source or SessionSource()
    lineage = session_lineage_id(agent, session_id)
    completeness: Completeness = "partial" if source.malformed else (source.completeness or "complete")
    if not logs:
        manifest = SessionManifest(
            parser_version="",
            agent=agent,
            session_id=session_id,
            lineage_id=lineage,
            source_type=source.type,
            source_fingerprint="",
            high_water_mark="",
            ingested_at="",
            completeness=completeness,
            transcript_sha256="",
            schema_version=0,
            record_count=0,
            malformed_records=source.malformed,
            skipped_records=source.skipped or 1,
        )
        return SessionIngestionResult("skipped", lineage, manifest=manifest)

    _normalize_logs(agent, session_id, logs)
    fingerprint = source.fingerprint or fingerprint_logs(logs)
    if len(fingerprint) != 64:
        raise ValueError("session source fingerprint must be a full SHA-256 digest")
    try:
        bytes.fromhex(fingerprint)
    except ValueError as error:
        raise ValueError("session source fingerprint must be a full SHA-256 digest") from error

    transcript = marshal_session_logs(logs)
    generation = session_generation_id(fingerprint)
    manifest = SessionManifest(
        parser_version=SESSION_PARSER_VERSION,
        agent=agent,
        session_id=session_id,
        lineage_id=lineage,
        source_type=source.type or "normalized",
        source_fingerprint=fingerprint,
        high_water_mark=source.high_water or session_high_water(logs),
        ingested_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        completeness=completeness,
        transcript_sha256=fingerprint_bytes(transcript),
        schema_version=SESSION_SCHEMA_VERSION,
        record_count=len(logs),
        malformed_records=source.malformed,
        skipped_records=source.skipped,
    )

    root = session_store_root()
    lineage_dir = root / agent / lineage
    final = lineage_dir / generation
    lineage_descriptor = _secure_directories(agent, lineage)
    temp_name = f".ingest-{secrets.token_hex(16)}"
    temp_descriptor = -1
    try:
        try:
            final_descriptor = _open_private_directory_at(lineage_descriptor, generation, final)
        except FileNotFoundError:
            final_descriptor = -1
        if final_descriptor >= 0:
            try:
                existing = _parse_session_manifest(
                    _read_owner_only_at(final_descriptor, "manifest.json", final / "manifest.json")
                )
                if not _same_immutable_identity(existing, manifest):
                    raise ValueError("existing session generation does not match its immutable identity")
                _validate_session_generation_at(final_descriptor, final, existing)
                os.fsync(final_descriptor)
                os.fsync(lineage_descriptor)
                _require_current_lineage(agent, lineage, lineage_descriptor)
                return SessionIngestionResult("duplicate", lineage, generation, existing)
            finally:
                os.close(final_descriptor)

        temp = lineage_dir / temp_name
        temp_descriptor = _create_private_directory_at(lineage_descriptor, temp_name, temp)
        _write_owner_only_at(temp_descriptor, "transcript.jsonl", transcript)
        manifest_content = (json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n").encode()
        _write_owner_only_at(temp_descriptor, "manifest.json", manifest_content)
        _validate_session_generation_at(temp_descriptor, temp, manifest)
        os.fsync(temp_descriptor)
        try:
            os.rename(temp_name, generation, src_dir_fd=lineage_descriptor, dst_dir_fd=lineage_descriptor)
        except OSError as rename_error:
            try:
                final_descriptor = _open_private_directory_at(lineage_descriptor, generation, final)
            except FileNotFoundError:
                raise rename_error from None
            try:
                existing, _ = _validate_session_generation_at(final_descriptor, final)
                if not _same_immutable_identity(existing, manifest):
                    raise ValueError("concurrent session generation has mismatched identity") from None
                os.fsync(final_descriptor)
                os.fsync(lineage_descriptor)
                _require_current_lineage(agent, lineage, lineage_descriptor)
                return SessionIngestionResult("duplicate", lineage, generation, existing)
            finally:
                os.close(final_descriptor)
        temp_name = ""
        os.fsync(lineage_descriptor)
        try:
            _require_current_lineage(agent, lineage, lineage_descriptor)
        except OSError, ValueError:
            for name in ("transcript.jsonl", "manifest.json"):
                with suppress(FileNotFoundError):
                    os.unlink(name, dir_fd=temp_descriptor)
            os.rmdir(generation, dir_fd=lineage_descriptor)
            raise
        return SessionIngestionResult("ingested", lineage, generation, manifest)
    finally:
        if temp_descriptor >= 0:
            if temp_name:
                for name in ("transcript.jsonl", "manifest.json"):
                    with suppress(FileNotFoundError):
                        os.unlink(name, dir_fd=temp_descriptor)
            os.close(temp_descriptor)
        if temp_name:
            with suppress(FileNotFoundError):
                os.rmdir(temp_name, dir_fd=lineage_descriptor)
        os.close(lineage_descriptor)


def report_ingestion(result: SessionIngestionResult) -> str:
    manifest = result.manifest
    if manifest is None:
        raise ValueError("ingestion result is missing its manifest")
    return (
        f"agent-session: {result.status} lineage={result.lineage_id[:12]} "
        f"records={manifest.record_count} malformed={manifest.malformed_records} "
        f"skipped={manifest.skipped_records} completeness={manifest.completeness}"
    )


def is_valid_session_id(session_id: str) -> bool:
    return _is_safe_component(session_id)


__all__ = [
    "SESSION_PARSER_VERSION",
    "SESSION_SCHEMA_VERSION",
    "SESSION_STORE_VERSION",
    "SessionIngestionResult",
    "SessionLog",
    "SessionManifest",
    "SessionSource",
    "fingerprint_bytes",
    "fingerprint_file",
    "fingerprint_json",
    "fingerprint_logs",
    "ingest_session",
    "is_valid_session_id",
    "marshal_session_logs",
    "publish_owner_only",
    "read_session_manifest",
    "report_ingestion",
    "session_digest",
    "session_generation_id",
    "session_high_water",
    "session_lineage_id",
    "session_store_root",
    "stored_generation",
    "validate_session_generation",
]
