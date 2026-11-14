# Docs: https://fishshell.com/docs/current/cmds/function.html
# Strip mise installs/* entries and hook state so agy shells re-resolve workspace pins via shims,
# and disable gh/gcloud prompts. Non-interactive callers replace fish via `exec` for MainPID.
function agy --description "Run agy with mise shims first and no gh or gcloud prompts"
    set -l shims "$HOME/.local/share/mise/shims"
    set -l clean_path
    if test -d "$shims"
        set clean_path "$shims"
    end
    for entry in $PATH
        if test "$entry" = "$shims"; or string match -q "$HOME/.local/share/mise/installs/*" -- "$entry"
            continue
        end
        set -a clean_path "$entry"
    end
    set -l joined_path (string join : -- $clean_path)
    set -l bin (PATH="$joined_path" command -s agy); or return 127
    set -l env_args \
        -u MISE_SHELL \
        -u __MISE_DIFF \
        -u __MISE_ORIG_PATH \
        -u __MISE_SESSION \
        -u __MISE_SHIM \
        -u __MISE_ENV_CACHE_KEY \
        PATH="$joined_path" \
        GH_PROMPT_DISABLED=1 \
        CLOUDSDK_CORE_DISABLE_PROMPTS=1 \
        "$bin" $argv
    if status is-interactive
        command env $env_args
    else
        exec env $env_args
    end
end
