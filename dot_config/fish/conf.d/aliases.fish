# Docs: https://fishshell.com/docs/current/index.html
if status is-interactive
    # a:agy
    abbr -a a agy
    # b:bat
    abbr -a b bat
    # c:gcloud
    abbr -a c gcloud
    abbr -a cl "gcloud auth login --update-adc"
    # d:docker
    abbr -a d docker
    # e:lazydocker
    abbr -a e lazydocker
    # f:fd
    abbr -a f fd
    # g:git
    abbr -a g git
    abbr -a gd gh-dash
    # h:lazygit
    abbr -a h lazygit
    # i:agy
    abbr -a i agy
    abbr -a iq "agy --prompt"
    # j:fkf
    abbr -a j 'fkf --base "$FKF_BASE"'
    # k:kubectl
    abbr -a k kubectl
    # l:lsd
    alias lsd="lsd --icon=always --git --group-directories-first --date=relative --literal"
    alias ls="lsd"
    abbr -a l "lsd --long --all"
    abbr -a la "lsd --all"
    abbr -a ll "lsd --long"
    abbr -a lg "lsd --long --git"
    abbr -a lt "lsd --tree"
    # m:mise
    abbr -a m mise
    abbr -a mr "mise run"
    # n:npm
    abbr -a n npm
    # o:clear
    abbr -a o clear
    # p:python
    abbr -a p python3
    abbr -a pt ptpython
    # q:fzf
    abbr -a q fzf
    # r:ripgrep
    abbr -a r rg
    # s:ssh
    abbr -a s ssh
    # t:tofu
    abbr -a t tofu
    # u:uv
    abbr -a u uv
    abbr -a ur "uv run"
    # v:nvim
    abbr -a v nvim
    abbr -a vi nvim
    # w:zellij
    abbr -a w zellij
    abbr -a wa "zellij run --close-on-exit -- agy"
    # x:xh
    abbr -a x xh
    # y:yazi
    abbr -a y yazi
end
