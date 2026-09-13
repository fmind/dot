# Docs: https://github.com/charmbracelet/vhs
# Generate theme.tape from the selected terminal palette before validation.
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
