# Clipboard platform behavior

Read when [copy.py](../scripts/copy.py) fails or reports an unexpected backend; the helper prints the native tool's diagnostic.

- **macOS**: built-in `pbcopy` and `pbpaste`, with `LC_CTYPE=UTF-8` so non-ASCII text survives the read-back.
- **ChromeOS/Linux**: on Crostini (`SOMMELIER_VERSION` set), `xclip -selection clipboard` with `DISPLAY`, because Sommelier syncs the X11 clipboard with ChromeOS; elsewhere `wl-copy` and `wl-paste` with `WAYLAND_DISPLAY` first, then `xclip`. On Crostini, verification proves the container clipboard; the sync to ChromeOS is not observable from inside.
- **Failures**: each native command has a five-second timeout. Failures leave the clipboard state uncertain; a backend error does not trigger another write. Headless/remote shells without a local clipboard fail explicitly.
- **Input contract**: plain UTF-8 text up to 1 MiB; inner newlines are preserved, empty input is rejected, and clipboard contents are never printed or retained.
