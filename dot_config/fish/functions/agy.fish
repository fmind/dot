# Docs: https://fishshell.com/docs/current/cmds/function.html
# agy runs every agent command as a separate `bash -c` with the environment agy started with.
# An interactive fish PATH lists the launch directory's mise install paths ahead of the shims,
# so put the shims first: each command then resolves the current project's tool pins. gh and
# gcloud fail or take their default instead of waiting on a prompt no agent answers; agy itself
# already sets PAGER, GIT_PAGER, GIT_EDITOR, and GIT_TERMINAL_PROMPT for its commands.
# Non-interactive fish replaces itself with agy, so Zellij's Alt a pane runs the agy binary and the
# daemon's MainPID (antigravity-cli-daemon.service.d/path.conf) is agy; such callers must run agy
# as their last command, never inside a command substitution.
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
