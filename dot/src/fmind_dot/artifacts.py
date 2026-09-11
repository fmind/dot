"""Preview-first cleanup of generated project artifacts."""

import os
import stat
from contextlib import suppress
from pathlib import Path

from fmind_dot.errors import DotError
from fmind_dot.private_files import (
    _open_directory_at,
    _open_verified_directory,
    _safe_agent_fs_available,
    _same_file_identity,
)
from fmind_dot.state import State


def prune_agent_artifacts(state: State, *, dry_run: bool) -> None:
    expanded = {"prompts", "proposals", "reports"}
    if not _safe_agent_fs_available():
        raise DotError("safe agent cleanup is unavailable on this platform")
    result = state.runner.run(["git", "rev-parse", "--show-toplevel"], check=False)
    project = Path(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else Path.cwd()
    try:
        project_descriptor = _open_verified_directory(project)
    except OSError as error:
        raise DotError(f"failed to open cleanup root: {error}") from error
    try:
        try:
            agents_mode = os.stat(".agents", dir_fd=project_descriptor, follow_symlinks=False).st_mode
        except FileNotFoundError:
            agents_descriptor = None
        else:
            if stat.S_ISLNK(agents_mode):
                raise DotError("refusing symlinked cleanup directory .agents")
            if not stat.S_ISDIR(agents_mode):
                raise DotError("cleanup target .agents is not a directory")
            try:
                agents_descriptor = _open_directory_at(project_descriptor, ".agents")
            except OSError as error:
                raise DotError(f"failed to open cleanup directory .agents: {error}") from error

        try:
            for target in sorted(expanded):
                entries: list[str] = []
                target_descriptor: int | None = None
                if agents_descriptor is not None:
                    try:
                        mode = os.stat(target, dir_fd=agents_descriptor, follow_symlinks=False).st_mode
                    except FileNotFoundError:
                        pass
                    else:
                        if stat.S_ISLNK(mode):
                            raise DotError(f"refusing symlinked cleanup directory .agents/{target}")
                        if not stat.S_ISDIR(mode):
                            raise DotError(f"cleanup target .agents/{target} is not a directory")
                        try:
                            target_descriptor = _open_directory_at(agents_descriptor, target)
                        except OSError as error:
                            raise DotError(f"failed to open cleanup directory .agents/{target}: {error}") from error
                        try:
                            # Pathlib would reopen the raced pathname; list the held directory instead.
                            entries = sorted(os.listdir(target_descriptor))  # noqa: PTH208
                        except BaseException:
                            os.close(target_descriptor)
                            target_descriptor = None
                            raise
                try:
                    if dry_run:
                        for entry in entries:
                            state.stdout.write(f"  ○ .agents/{target}/{entry}\n")
                    elif target_descriptor is not None:
                        _clear_directory(target_descriptor, target)
                finally:
                    if target_descriptor is not None:
                        os.close(target_descriptor)
                state.stdout.write(
                    f"✓ {'Would clean' if dry_run else 'Cleaned'} {len(entries)} file(s) in .agents/{target}\n"
                )
        finally:
            if agents_descriptor is not None:
                os.close(agents_descriptor)
    finally:
        os.close(project_descriptor)


def _clear_directory(directory: int, target: str) -> None:
    def fail(error: OSError) -> None:
        raise error

    try:
        walk = os.fwalk(".", topdown=False, onerror=fail, follow_symlinks=False, dir_fd=directory)
        for _root, directory_names, file_names, current in walk:
            for name in sorted(file_names):
                mode = os.stat(name, dir_fd=current, follow_symlinks=False).st_mode
                if stat.S_ISDIR(mode):
                    raise DotError(f"cleanup entry .agents/{target}/{name} changed during removal")
                with suppress(FileNotFoundError):
                    os.unlink(name, dir_fd=current)
            for name in sorted(directory_names):
                try:
                    mode = os.stat(name, dir_fd=current, follow_symlinks=False).st_mode
                except FileNotFoundError:
                    continue
                if not stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
                    os.unlink(name, dir_fd=current)
                    continue
                child = _open_directory_at(current, name)
                try:
                    if os.listdir(child):  # noqa: PTH208 - keep the emptiness check on the verified descriptor.
                        raise DotError(f"cleanup directory .agents/{target}/{name} changed during removal")
                    opened = os.fstat(child)
                    current_entry = os.stat(name, dir_fd=current, follow_symlinks=False)
                    if not _same_file_identity(opened, current_entry):
                        raise DotError(f"cleanup directory .agents/{target}/{name} changed during removal")
                    os.rmdir(name, dir_fd=current)
                finally:
                    os.close(child)
    except (DotError, OSError) as error:
        if isinstance(error, DotError):
            raise
        raise DotError(f"failed to clean .agents/{target}: {error}") from error
