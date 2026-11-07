# Docs: https://fishshell.com/docs/current/cmds/fish_config.html#theme-files
# Select the data-only fmind theme (a chezmoi external from github.com/fmind/theme).
# `theme choose` sets global colors per session; interactive shells only (about 8 ms).
if status is-interactive; and test -r $__fish_config_dir/themes/fmind.theme
    fish_config theme choose fmind
end
