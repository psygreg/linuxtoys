#!/bin/bash
# name: Mise
# version: 1.0
# description: mise_desc
# icon: mise

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
# install mise
curl https://mise.run | sh
echo 'eval "$(~/.local/bin/mise activate bash)"' >> ~/.bashrc
echo 'eval "$(~/.local/bin/mise activate zsh)"' >> ~/.zshrc
echo '~/.local/bin/mise activate fish | source' >> ~/.config/fish/config.fish
# set up autocomplete feature
mise use -g usage
if [ -f $HOME/.bashrc ]; then
    mkdir -p ~/.local/share/bash-completion/
    mise completion bash --include-bash-completion-lib > ~/.local/share/bash-completion/completions/mise
fi
if [ -f $HOME/.zshrc ]; then
    mkdir -p /usr/local/share/zsh/site-functions
    mise completion zsh  > /usr/local/share/zsh/site-functions/_mise
fi
if [ -f $HOME/.config/fish/config.fish ]; then
    mkdir -p ~/.config/fish/completions
    mise completion fish > ~/.config/fish/completions/mise.fish
fi
zeninf "$msg282"
xdg-open https://mise.jdx.dev/walkthrough.html
exit 0