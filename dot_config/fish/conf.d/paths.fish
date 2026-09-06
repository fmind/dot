# Docs: https://fishshell.com/docs/current/index.html
if test (uname) = Darwin
    fish_add_path -g /opt/homebrew/bin /opt/homebrew/sbin
end
fish_add_path -mg /usr/local/bin /usr/local/sbin
fish_add_path -mg ~/.local/bin
# Scripts do not run interactive mise activation, so they need the static shims.
if not status is-interactive
    fish_add_path -mg ~/.local/share/mise/shims
end
