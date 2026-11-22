# Docs: https://fishshell.com/docs/current/cmds/fish_config.html#theme-files
# Select the data-only fmind theme (a chezmoi external from github.com/fmind/theme).
if status is-interactive; and test -f "$__fish_config_dir/themes/fmind.theme" -a -r "$__fish_config_dir/themes/fmind.theme"
    fish_config theme choose fmind
end
