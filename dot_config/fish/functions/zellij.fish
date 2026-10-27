# Docs: https://fishshell.com/docs/current/cmds/function.html
# Zellij only auto-serializes sessions that SessionLayoutMetadata::is_dirty() considers modified
# (more than one pane or a non-shell command), and kill-session exits without serializing.
# Save the layout explicitly after background creation and before kill-session so 1-pane
# directory sessions stay in EXITED (resurrectable) state; delete-session (d) still removes them.
function zellij --description "Run zellij and persist background or killed sessions for resurrection"
    if test (count $argv) -ge 2
        switch $argv[1]
            case k kill-session
                set -l target ""
                for arg in $argv[2..-1]
                    switch $arg
                        case -h --help
                            set target ""
                            break
                        case '-*'
                            continue
                        case '*'
                            if test -z "$target"
                                set target $arg
                            end
                    end
                end
                if test -n "$target"
                    command zellij --session "$target" action save-session >/dev/null 2>&1
                end
            case a attach
                set -l background 0
                set -l target ""
                set -l skip_next 0
                for arg in $argv[2..-1]
                    if test $skip_next -eq 1
                        set skip_next 0
                        continue
                    end
                    switch $arg
                        case --
                            break
                        case -h --help options help
                            set background 0
                            break
                        case --index -t --token --ca-cert
                            set skip_next 1
                        case '--index=*' '--token=*' '--ca-cert=*'
                            continue
                        case --create-background
                            set background 1
                        case '--*'
                            continue
                        case '-*'
                            if string match -q -- '*h*' $arg
                                set background 0
                                break
                            end
                            if string match -q -- '*b*' $arg
                                set background 1
                            end
                        case '*'
                            if test -z "$target"
                                set target $arg
                            end
                    end
                end
                if test $background -eq 1 -a -n "$target"
                    command zellij $argv
                    set -l exit_status $status
                    if test $exit_status -eq 0
                        command zellij --session "$target" action save-session >/dev/null 2>&1
                    end
                    return $exit_status
                end
        end
    end
    command zellij $argv
end
