# Docs: https://fishshell.com/docs/current/cmds/fish_config.html#theme-files
# Select the data-only fmind theme (a chezmoi external from github.com/fmind/theme).
if status is-interactive; and test -f "$__fish_config_dir/themes/fmind.theme" -a -r "$__fish_config_dir/themes/fmind.theme"
    set -l __dot_theme "$__fish_config_dir/themes/fmind.theme"
    set -l __dot_theme_mtime (path mtime -- "$__dot_theme" 2>/dev/null); or set __dot_theme_mtime 0
    set -l __dot_expected "# $__dot_theme|$__dot_theme_mtime"
    set -l __dot_cache_root "$HOME/.cache"
    if set -q XDG_CACHE_HOME; and string match -q '/*' -- "$XDG_CACHE_HOME"
        set __dot_cache_root "$XDG_CACHE_HOME"
    end
    set -l __dot_cache_dir "$__dot_cache_root/fish"
    set -l __dot_theme_cache "$__dot_cache_dir/theme-fmind.fish"
    set -l __dot_theme_loaded 0
    if test -d "$__dot_cache_dir" -a ! -L "$__dot_cache_dir" -a -O "$__dot_cache_dir" -a -f "$__dot_theme_cache" -a ! -L "$__dot_theme_cache" -a -O "$__dot_theme_cache" -a -s "$__dot_theme_cache"
        read -l __dot_header <"$__dot_theme_cache"
        if test "$__dot_header" = "$__dot_expected"
            source "$__dot_theme_cache"
            set __dot_theme_loaded 1
        end
    end
    if test $__dot_theme_loaded -eq 0
        if fish_config theme choose fmind
            set -l __dot_vars (set -gn | string match -r '^fish_(?:pager_)?color_.*')
            if test (count $__dot_vars) -gt 0; and mkdir -p -m 700 "$__dot_cache_dir" 2>/dev/null; and test -d "$__dot_cache_dir" -a ! -L "$__dot_cache_dir" -a -O "$__dot_cache_dir" -a -w "$__dot_cache_dir"
                set -l __dot_tmp "$__dot_theme_cache.$fish_pid.tmp"
                begin
                    printf '%s\n' "$__dot_expected"
                    for __dot_var in $__dot_vars
                        printf 'set -g -- %s %s\n' "$__dot_var" (string join ' ' -- (string escape -- $$__dot_var))
                    end
                end >"$__dot_tmp" 2>/dev/null; and mv -f "$__dot_tmp" "$__dot_theme_cache" 2>/dev/null; or rm -f "$__dot_tmp" 2>/dev/null
            end
        end
    end
end
