# Docs: https://fishshell.com/docs/current/index.html
fish_add_path -ag /usr/local/bin /usr/local/sbin
if test (uname) = Darwin
    fish_add_path -mg /opt/homebrew/bin /opt/homebrew/sbin
end
fish_add_path -mg ~/.local/bin
# Scripts do not run interactive mise activation, so they need the static shims.
if not status is-interactive
    fish_add_path -mg ~/.local/share/mise/shims
end
