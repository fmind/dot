---
name: language
description: "Apply Python 3.14+ idioms, strict ty typing, exception chaining, subprocess bounds, and atomic file I/O."
---

# Python Language, Typing, & Boundaries

High-leverage Python `3.14+` invariants and safety boundaries; [foundation](foundation/GUIDE.md) owns packaging and tooling, and [async](async.md) owns concurrency.

## Strict Typing (`ty`)

- **Narrow parameter contracts**: accept read-only `Sequence[T]`, `Mapping[K, V]`, `Iterable[T]`, or small `Protocol` interfaces instead of concrete `list`/`dict` when callers do not need mutation.
- **Value objects & exhaustiveness**: prefer `@dataclass(slots=True, frozen=True)` for immutable domain values, discriminated unions + `typing.assert_never(...)` on `match` branches, and `typing.TypeIs[T]` over `TypeGuard` when narrowing both branches.
- **Zero unexamined escapes**: avoid `Any`, `cast()`, and blanket ignores; mark typed libraries with `py.typed` and validate untrusted data at boundaries with [Pydantic](pydantic.md).

## Python 3.14 / 3.15 Deltas

- **Deferred annotations (PEP 649, `3.14+`)**: annotations evaluate lazily via `__annotate__` / `annotationlib`; keep `from __future__ import annotations` only when supporting `<3.14` or libraries that expect stringized annotations.
- **Stdlib replacements (`3.14+`)**: use `compression.zstd` instead of third-party `zstandard`, `concurrent.interpreters` / `InterpreterPoolExecutor` for pure-Python CPU isolation, and PEP 750 template strings (`t"..."`, `string.templatelib.Template`) when building structured SQL/HTML/shell formatters safely.
- **Lazy CLI imports (`3.15+`)**: use `__lazy_modules__ = [...]` (or handler-local imports on `3.14`) to keep CLI startup sub-50ms ([argparse](argparse/GUIDE.md)).

## Exceptions, Subprocesses, & Filesystem I/O

- **Chain and preserve cancellation**: catch narrow exception types, never swallow `asyncio.CancelledError` or `KeyboardInterrupt`, always chain `raise DomainError(...) from err` (or explicit `from None` when hiding internals), attach structured attributes to domain errors, and never use `assert` for runtime validation (`python -O` strips it).
- **Bound subprocesses**: invoke `subprocess.run([cmd, ...], check=True, timeout=..., stdin=subprocess.DEVNULL)` with explicit list argv (never `shell=True` on untrusted inputs) and validate exit codes when `check=False`.
- **Encoding, timezones, & iteration**: pass `encoding="utf-8"` on every `open()` / `Path.read_text()` / `Path.write_text()`, `strict=True` on parallel `zip(...)`, and `datetime.now(UTC)` (never naive `datetime.now()` / `utcnow()`).
- **Atomic writes & path containment**: write durable files to a same-directory temp file (`tempfile.NamedTemporaryFile(dir=target.parent, delete=False)`), fsync when durability matters, and swap via `os.replace(...)`; verify derived write/delete paths with `resolved.is_relative_to(allowed_root)` and `resolved != allowed_root`.

## Documentation

- [Python 3.14 What's New](https://docs.python.org/3/whatsnew/3.14.html) · [PEP 649](https://peps.python.org/pep-0649/) · [PEP 750](https://peps.python.org/pep-0750/) · [typing](https://docs.python.org/3/library/typing.html) · [subprocess](https://docs.python.org/3/library/subprocess.html)
- Companions: [foundation](foundation/GUIDE.md), [async](async.md), [pydantic](pydantic.md), [testing](testing/GUIDE.md).
