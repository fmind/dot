# Docs: https://github.com/charmbracelet/vhs
# Copy ~/.agents/themes/vhs/fmind.tape as theme.tape before validation.
Require python
Require ttyd
Require ffmpeg
Output demo.gif
Set Shell bash
Set FontFamily "GoogleSansCode Nerd Font Mono"
Set FontSize 22
Set Width 1000
Set Height 420
Set TypingSpeed 35ms
Set Framerate 15
Set CursorBlink false
Source theme.tape
Type `python -c 'print("Hello, Ada!")'`
Enter
Sleep 2s
Screenshot final.png
# Screenshot captures the next frame; keep recording past the request.
Sleep 200ms
