# Reproducible Terminal Recordings

Use VHS for executable terminal demonstrations; [fmind-visuals](../SKILL.md) owns presentation choices. The owning project defines the explanation, output location, and delivery.

## Workflow

1. **Pretest with synthetic inputs**: use synthetic inputs and a disposable working directory. Test the command and its exit status before recording; VHS typing a command does not assert that it succeeded.
1. **Preflight tools and fonts**: preflight `vhs --version`, `ttyd --version`, `ffmpeg -version`, the demonstrated executable, and the selected font. Of these, only `ffmpeg` is global on the workstation: declare `vhs` with `mise use --pin vhs` in the `mise.toml` of the project that owns the recording, or of the disposable directory, and add `ttyd = { version = "<exact>", os = ["linux"] }` beside it. Upstream ttyd has no macOS release asset, so qualify a supported local build or a reviewed container before recording there. A successful `vhs validate` does not prove these runtime dependencies or the browser are available.
1. **Copy [demo.tape](../templates/demo.tape) into the disposable directory**: set dimensions, font, typing speed, and short holds deliberately. Keep waits bounded; use `Wait` for observable output when timing varies, with a process deadline as the outer bound.
1. **Copy the pinned palette as `theme.tape`**: `cp ~/.agents/themes/vhs/fmind.tape theme.tape`. Fmind recordings use this [fmind/theme](https://github.com/fmind/theme) file unchanged, and the template sources it; for another brand, write one `Set Theme {...}` line with that brand's 16 ANSI colors, background, foreground, cursor, and selection. Diagram colors follow `~/.agents/DESIGN.md` through [renderers.md](renderers.md).
1. **Render in a clean, bounded environment**: render with a clean environment and a deadline. Save the Python supervisor below as `record.py` and run `mise exec -- python record.py <font-file>` so PATH contains resolved tool directories rather than home-dependent shims. On Linux, `fc-match -f '%{file}' 'GoogleSansCode Nerd Font Mono'` locates the font; inspect the returned family before accepting a fallback. Copy that reviewed font into the temporary home. The supervisor discards inherited credentials and shell setup, and terminates its process group on timeout or interruption:
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
1. **Inspect frames and retain sources**: inspect the beginning, command output, and final frame for legibility, clipping, font fallback, private data, and sufficient reading time. VHS captures `Screenshot` on the next recorded frame: keep a short `Sleep` after it, including at the end of a tape, and verify the PNG exists. Retain `.tape`, `theme.tape`, synthetic fixture inputs, and the export together; record tool versions and the theme source revision. Provide a static frame and text equivalent for readers who cannot use animation.

## Gotchas

- **A tape is executable input**: review every `Type`, `Source`, `Env`, and output path before running an external tape. `Hide` hides frames, not side effects or logs.
- **Construct the environment explicitly**: a temporary HOME removes personal shell files; also remove inherited `BASH_ENV`, prompt commands, and credentials by constructing the environment explicitly. Add only the variables the demonstrated command needs.
- **Diagnose missing dependencies explicitly**: VHS may need to provision a browser on first use. Diagnose missing dependencies or fonts explicitly; do not mistake a partial export for success.
- **Recording excludes publishing**: `vhs publish`, `--publish`, and `vhs serve` expose artifacts or services. Local recording does not include those operations.

## Documentation

- [VHS commands and prerequisites](https://github.com/charmbracelet/vhs) · [ttyd](https://github.com/tsl0922/ttyd) · [FFmpeg](https://ffmpeg.org/documentation.html)
- Releases: [VHS](https://github.com/charmbracelet/vhs/releases) · [ttyd](https://github.com/tsl0922/ttyd/releases)
