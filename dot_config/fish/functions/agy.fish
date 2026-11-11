# Docs: https://fishshell.com/docs/current/cmds/function.html
# Put mise shims ahead of the launch directory's activated tool paths so agy's `bash -c` calls
# resolve each project's pins, and disable gh/gcloud prompts. Non-interactive callers (Zellij Alt a,
# antigravity-cli-daemon.service.d/path.conf) replace fish via `exec` so MainPID stays on agy.
function agy --description "Run agy with mise shims first and no gh or gcloud prompts"
    set -lx PATH $HOME/.local/share/mise/shims $PATH
    set -lx GH_PROMPT_DISABLED 1
    set -lx CLOUDSDK_CORE_DISABLE_PROMPTS 1
    if status is-interactive
        command agy $argv
    else
        exec agy $argv
    end
end
