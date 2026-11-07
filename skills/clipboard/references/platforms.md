# Clipboard platform behavior

Read when [copy.py](../scripts/copy.py) fails or reports an unexpected backend; the helper prints the native tool's diagnostic.

- **macOS**: built-in `pbcopy` and `pbpaste`, with `LC_CTYPE=UTF-8` so non-ASCII text survives the read-back.
- **ChromeOS/Linux**: on Crostini (`SOMMELIER_VERSION` set), `xclip -selection clipboard` with `DISPLAY`, because Sommelier syncs the X11 clipboard with ChromeOS; elsewhere `wl-copy` and `wl-paste` with `WAYLAND_DISPLAY` first, then `xclip` (on Android AVF `ttyd` VMs where `/etc/profile.d/activate_display.sh` sets `DISPLAY=:0` without `SOMMELIER_VERSION`, `ttyd-clipboard.service` forwards `xclip` selections as OSC 52 to active `ttyd` PTYs, while Neovim uses `osc52-write` directly). On Crostini and AVF, verification proves the container clipboard; the sync to the host is not observable from inside.
- **Failures are bounded and explicit**: each native command has a five-second timeout. Failures leave the clipboard state uncertain; a backend error does not trigger another write. Headless/remote shells without a local clipboard fail explicitly.
