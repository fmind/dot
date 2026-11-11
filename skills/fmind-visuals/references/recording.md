# Reproducible Terminal Recordings

Record executable terminal demos with VHS ([fmind-visuals](../SKILL.md) owns branding; the target project owns output paths and delivery).

## Workflow

1. **Pretest on synthetic fixtures**: run the demonstrated command in a disposable directory and verify its exit code—VHS typing a command does not check success.
1. **Preflight dependencies and fonts**: verify `vhs --version`, `ttyd --version`, `ffmpeg -version` (only `ffmpeg` is global), the target binary, and font (`vhs validate` checks syntax only). Pin `mise use --pin vhs` plus `ttyd = { version = "<exact>", os = ["linux"] }`; on macOS, qualify a local `ttyd` build or reviewed container first since upstream publishes no macOS release asset.
1. **Adapt [demo.tape](../templates/demo.tape)**: set dimensions, font, typing speed, and bounded waits (`Wait` on observable output under an outer process timeout).
1. **Copy `theme.tape`**: `cp ~/.agents/themes/vhs/fmind.tape theme.tape` ([fmind/theme](https://github.com/fmind/theme)), or write a single `Set Theme {...}` line with customer ANSI colors ([renderers.md](renderers.md) covers diagrams).
1. **Supervise in a clean HOME**: locate the reviewed font (`fc-match -f '%{file}' 'GoogleSansCode Nerd Font Mono'` on Linux; verify family before accepting fallbacks), save `record.py`, and run `mise exec -- python3 record.py <font-file>` so resolved tool paths run without personal shell config or credentials:
   ```python
   import os
   import shutil
   import signal
   import subprocess
   import sys
   from pathlib import Path
   from tempfile import TemporaryDirectory

   def run(arguments, environment, timeout):
       with subprocess.Popen(arguments, env=environment, start_new_session=True) as process:
           try:
               result = process.wait(timeout=timeout)
           finally:
               try:
                   os.killpg(process.pid, signal.SIGKILL)
               except ProcessLookupError:
                   pass
           if result:
               raise subprocess.CalledProcessError(result, arguments)

   with TemporaryDirectory(prefix="vhs-home-") as home:
       fonts = Path(home) / ("Library/Fonts" if sys.platform == "darwin" else ".local/share/fonts")
       fonts.mkdir(parents=True)
       shutil.copy2(sys.argv[1], fonts)
       environment = {
           "HOME": home, "XDG_CONFIG_HOME": f"{home}/.config", "XDG_CACHE_HOME": f"{home}/.cache",
           "PATH": os.environ["PATH"], "TERM": "xterm-256color", "LANG": "C.UTF-8",
           "TZ": "UTC", "PS1": "$ ", "HISTFILE": os.devnull,
       }
       run(["vhs", "validate", "demo.tape"], environment, 15)
       run(["vhs", "demo.tape"], environment, 120)
   ```
1. **Inspect and retain**: check opening, output, and final frames for legibility, clipping, font fallback, leaks, and pacing. Keep a short `Sleep` after `Screenshot` (captured on the next frame) and confirm the PNG exists. Commit `.tape`, `theme.tape`, synthetic fixtures, and static/text fallbacks alongside exports, recording tool and theme versions.

## Gotchas

- **Tapes execute code**: audit `Type`, `Source`, `Env`, and `Output` in external tapes (`Hide` suppresses frames, not side effects).
- **Scrub inherited env**: pass an explicit `env` dict so `BASH_ENV`, prompt hooks, and secrets stay out, adding only variables the demo requires.
- **First-run browser provisioning**: diagnose missing browsers or fonts explicitly; never treat a partial render as success.
- **Never publish implicitly**: `vhs publish`, `--publish`, and `vhs serve` expose assets/ports and require separate authorization.

## Documentation

- [VHS commands and prerequisites](https://github.com/charmbracelet/vhs) · [ttyd](https://github.com/tsl0922/ttyd) · [FFmpeg](https://ffmpeg.org/documentation.html)
- Releases: [VHS](https://github.com/charmbracelet/vhs/releases) · [ttyd](https://github.com/tsl0922/ttyd/releases)
