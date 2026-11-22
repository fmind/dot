# Docs: https://fishshell.com/docs/current/index.html

set -g fish_greeting ''

if test -f ~/.private.fish -a ! -L ~/.private.fish -a -O ~/.private.fish -a -r ~/.private.fish
    source ~/.private.fish
end
