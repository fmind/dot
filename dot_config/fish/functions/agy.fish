# Docs: https://fishshell.com/docs/current/cmds/function.html
# agy runs every agent command as a separate `bash -c` with the environment agy started with.
# An interactive fish PATH lists the launch directory's mise install paths ahead of the shims,
# so put the shims first: each command then resolves the current project's tool pins, like
# the Remote Control daemon (antigravity-cli-daemon.service.d/path.conf). gh and gcloud then
# fail or take their default instead of waiting on a prompt no agent answers; agy itself
# already sets PAGER, GIT_PAGER, GIT_EDITOR, and GIT_TERMINAL_PROMPT for its commands.
function agy --description "Run agy with mise shims first and no gh or gcloud prompts"
    set -lx PATH $HOME/.local/share/mise/shims $PATH
    set -lx GH_PROMPT_DISABLED 1
    set -lx CLOUDSDK_CORE_DISABLE_PROMPTS 1
    command agy $argv
end
