# Docs: https://fishshell.com/docs/current/index.html
if status is-interactive
    # a:agy
    abbr -a a agy
    abbr -a ac "agy --continue"
    abbr -a ai "agy --prompt-interactive"
    abbr -a ap "agy --print"
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
    # i:fastfetch
    abbr -a i fastfetch
    # k:kubectl
    abbr -a k kubectl
    # l:lsd
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
    # o:open
    if test (uname) = Darwin
        abbr -a o open
    else
        alias open=xdg-open
        abbr -a o xdg-open
    end
    # p:python
    abbr -a p python3
    abbr -a pt ptpython
    # q:fzf
    abbr -a q fzf
    # r:ripgrep
    # Truncate long lines for people only; agents inherit RIPGREP_CONFIG_PATH and need full matches.
    alias rg="rg --max-columns=150 --max-columns-preview"
    abbr -a r rg
    # s:ssh
    abbr -a s ssh
    # t:tofu
    abbr -a t tofu
    # u:uv
    abbr -a u uv
    abbr -a uf "uv run --frozen"
    abbr -a ur "uv run"
    abbr -a ux uvx
    # v:nvim
    abbr -a v nvim
    abbr -a vd "nvim -d"
    abbr -a vi nvim
    abbr -a vs "nvim -"
    # w:zellij
    abbr -a w zellij
    abbr -a wa "zellij run --close-on-exit -- agy"
    # x:xh
    abbr -a x xh
    # y:yazi
    abbr -a y yazi
end
