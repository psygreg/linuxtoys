#!/bin/bash
# name: Mise
# version: 1.0
# description: mise_desc
# icon: mise.svg
# repo: https://github.com/jdx/mise

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
if [ -f $HOME/.bashrc ]; then
    prep_edit "$HOME/.bashrc"
    curl https://mise.run/bash | sh
    mise use -g usage
    prep_dir "$HOME/.local/share/bash-completion/"
    mise completion bash --include-bash-completion-lib > ~/.local/share/bash-completion/completions/mise
fi
if ! command -v rpm-ostree &>/dev/null; then
    # mise is not compatible with ZSH on ostree distros
    if [ -f $HOME/.zshrc ]; then
        prep_edit "$HOME/.zshrc"
        curl https://mise.run/zsh | sh
        mise use -g usage
        prep_dir "/usr/local/share/zsh/site-functions"
        mise completion zsh  > /usr/local/share/zsh/site-functions/_mise
    fi
fi
if [ -f $HOME/.config/fish/config.fish ]; then
    prep_edit "$HOME/.config/fish/config.fish"
    curl https://mise.run/fish | sh
    mise use -g usage
    prep_dir "$HOME/.config/fish/completions"
    mise completion fish > ~/.config/fish/completions/mise.fish
fi
zeninf "$msg282"
xdg-open https://mise.jdx.dev/walkthrough.html
exit 0
