# Docs: https://fishshell.com/docs/current/index.html
# PLUGINS
if status is-interactive
    # Cache static tool init scripts keyed by binary path, resolved mtime, script mtime, and arguments.
    function __dot_source_cached --argument-names name tool
        command -q $tool; or return
        set -l bin (command -s $tool)
        set -l resolved (path resolve -- "$bin" 2>/dev/null); or set resolved "$bin"
        set -l bin_mtime (path mtime -- "$resolved" 2>/dev/null); or set bin_mtime 0
        set -l self (status filename)
        set -l self_mtime (path mtime -- "$self" 2>/dev/null); or set self_mtime 0
        set -l cmd $argv[2..]
        set -l expected "# $bin|$resolved|$bin_mtime|$self_mtime|"(string join ' ' -- $cmd)
        set -l cache_root "$HOME/.cache"
        if set -q XDG_CACHE_HOME; and string match -q '/*' -- "$XDG_CACHE_HOME"
            set cache_root "$XDG_CACHE_HOME"
        end
        set -l cache_dir "$cache_root/fish/init"
        set -l cache "$cache_dir/$name.fish"
        if test -d "$cache_dir" -a ! -L "$cache_dir" -a -O "$cache_dir" -a -f "$cache" -a ! -L "$cache" -a -O "$cache" -a -s "$cache"
            read -l header <"$cache"
            if test "$header" = "$expected"
                source "$cache"
                return
            end
        end
        if mkdir -p -m 700 "$cache_dir" 2>/dev/null; and test -d "$cache_dir" -a ! -L "$cache_dir" -a -O "$cache_dir" -a -w "$cache_dir"
            set -l body "$cache.$fish_pid.body.tmp"
            set -l tmp "$cache.$fish_pid.tmp"
            if not $cmd >"$body"
                rm -f "$body" "$tmp" 2>/dev/null
                return
            end
            if not test -s "$body"
                rm -f "$body" "$tmp" 2>/dev/null
                return
            end
            if printf '%s\n' "$expected" >"$tmp" 2>/dev/null; and command cat -- "$body" >>"$tmp" 2>/dev/null; and mv -f "$tmp" "$cache" 2>/dev/null
                rm -f "$body" 2>/dev/null
                source "$cache"
                return
            end
            source "$body"
            rm -f "$body" "$tmp" 2>/dev/null
            return
        end
        $cmd | source
    end

    __dot_source_cached mise mise activate fish
    __dot_source_cached fzf fzf --fish
    __dot_source_cached atuin atuin init fish --disable-ai
    __dot_source_cached starship starship init fish --print-full-init
    __dot_source_cached zoxide zoxide init fish
    functions -e __dot_source_cached

    # Start once after shell initialization; keep Fish available if Zellij exits.
    function auto_zellij --on-event fish_prompt
        functions -e auto_zellij
        if status is-interactive
            and test -t 0 -a -t 1
            and command -q zellij
            and not set -q ZELLIJ
            and not set -q TMUX
            and not set -q NVIM
            and not set -q SSH_CONNECTION
            and not set -q SSH_CLIENT
            and not set -q SSH_TTY
            and not set -q CI
            and not set -q CLAUDECODE
            and not set -q ANTIGRAVITY_AGENT
            and test "$TERM_PROGRAM" != vscode
            and test "$TERM_PROGRAM" != agy
            and test "$TERM" != dumb
            command zellij attach --create main
        end
    end
end
