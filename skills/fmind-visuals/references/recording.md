# Reproducible Terminal Recordings

Use VHS for executable terminal demonstrations; [fmind-visuals](../SKILL.md) owns presentation choices. The course or publishing project owns the explanation, output location, and publication decision.

## Workflow

1. Define one capability the viewer should learn, the command, its expected output, and the final frame. Use synthetic inputs and a disposable working directory. Test the command and its exit status before recording; VHS typing a command does not assert that it succeeded.
1. Preflight `vhs --version`, `ttyd --version`, `ffmpeg -version`, the demonstrated executable, and the selected font. Install missing user-space tools through mise where supported. The dot toolchain supplies `ttyd` on Linux; upstream has no macOS release asset, so qualify a supported local build or a reviewed container before recording there. A successful `vhs validate` does not prove these runtime dependencies or the browser are available.
1. Copy [demo.tape](../templates/demo.tape) into the disposable directory. Set dimensions, font, typing speed, and short holds deliberately. Keep waits bounded; use `Wait` for observable output when timing varies, with a process deadline as the outer bound.
1. Prepare `theme.tape` as described below. Fmind terminal recordings use the selected [fmind/theme](https://github.com/fmind/theme) palette; published article/deck colors remain a separate identity in [fmind-theme.md](fmind-theme.md). The template sources generated theme data rather than maintaining another palette here.
1. Render with a clean environment and a deadline. Save the Python supervisor below as `record.py` and run `mise exec -- python record.py <font-file>` so PATH contains resolved tool directories rather than home-dependent shims. On Linux, `fc-match -f '%{file}' 'GoogleSansCode Nerd Font Mono'` locates the font; inspect the returned family before accepting a fallback. Copy that reviewed font into the temporary home. The supervisor discards inherited credentials and shell setup, and terminates its process group on timeout or interruption:
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
           "HOME": home,
           "XDG_CONFIG_HOME": str(Path(home) / ".config"),
           "XDG_CACHE_HOME": str(Path(home) / ".cache"),
           "PATH": os.environ["PATH"],
           "TERM": "xterm-256color",
           "LANG": "C.UTF-8",
           "TZ": "UTC",
           "PS1": "$ ",
           "HISTFILE": os.devnull,
       }
       run(["vhs", "validate", "demo.tape"], environment, 15)
       run(["vhs", "demo.tape"], environment, 120)
   ```
1. Inspect the beginning, command output, and final frame for legibility, clipping, font fallback, private data, and sufficient reading time. Retain `.tape`, `theme.tape`, synthetic fixture inputs, and the export together; record tool versions and the theme source revision. Provide a static frame and text equivalent for readers who cannot use animation.

## Generate the terminal theme

Read the selected Ghostty theme from a reviewed fmind/theme release or its managed local file. Save this standard-library recipe as `theme.py` in the disposable directory and run `uv run python theme.py <ghostty-theme-path> > theme.tape`. It maps all sixteen slots without reinterpreting named ANSI colors, so the semantic bright half is retained.

```python
import json
import re
import sys
from pathlib import Path

source = Path(sys.argv[1])
fields = {}
slots = {}
for line in source.read_text().splitlines():
    key, separator, value = line.partition("=")
    if not separator or key.lstrip().startswith("#"):
        continue
    key, value = key.strip(), value.strip()
    if key == "palette":
        index, color = value.split("=", 1)
        index = int(index.strip())
        if not 0 <= index <= 255:
            raise ValueError("palette index must be between 0 and 255")
        if index > 15:
            continue
        if index in slots:
            raise ValueError("duplicate palette slot")
        slots[index] = color.strip()
    else:
        fields[key] = value
if set(slots) != set(range(16)):
    raise ValueError("theme must provide all sixteen ANSI slots")
names = "black red green yellow blue magenta cyan white".split()
names += ["bright" + name.title() for name in names]
theme = dict(zip(names, (slots[i] for i in range(16)), strict=True))
theme.update(background=fields["background"], foreground=fields["foreground"])
if any(re.fullmatch(r"#[0-9a-fA-F]{6}", color) is None for color in theme.values()):
    raise ValueError("theme colors must be six-digit hex values")
theme["name"] = source.stem
print("Set Theme " + json.dumps(theme))
```

## Gotchas

- A tape is executable input. Review every `Type`, `Source`, `Env`, and output path before running an external tape. `Hide` hides frames, not side effects or logs.
- A temporary HOME removes personal shell files; also remove inherited `BASH_ENV`, prompt commands, and credentials by constructing the environment explicitly. Add only the variables the demonstrated command needs.
- VHS may need to provision a browser on first use. Diagnose missing dependencies or fonts explicitly; do not mistake a partial export for success.
- `vhs publish`, `--publish`, and `vhs serve` expose artifacts or services. Local recording does not include those operations.

## Documentation

- [VHS commands and prerequisites](https://github.com/charmbracelet/vhs) · [ttyd](https://github.com/tsl0922/ttyd) · [FFmpeg](https://ffmpeg.org/documentation.html)
- Releases: [VHS](https://github.com/charmbracelet/vhs/releases) · [ttyd](https://github.com/tsl0922/ttyd/releases)
