#!/bin/bash
# name: Node Version Manager
# version: 1.0
# description: nvm_desc
# icon: nvm.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
sudo_rq
if command -v rpm-ostree &>/dev/null; then
    if [ ! -d "$HOME/.nvm" ]; then
    # revert to 'manual install' procedure, script doesn't work properly for atomic Fedora
        export NVM_DIR="$HOME/.nvm" && (
        git clone https://github.com/nvm-sh/nvm.git "$NVM_DIR"
        cd "$NVM_DIR"
        git checkout "git describe --abbrev=0 --tags --match "v[0-9]*" $(git rev-list --tags --max-count=1)"
        ) && \. "$NVM_DIR/nvm.sh"
        sleep 1
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
    else
        # update 'manually installed' NVM
        (
        cd "$NVM_DIR"
        git fetch --tags origin
        git checkout "git describe --abbrev=0 --tags --match "v[0-9]*" $(git rev-list --tags --max-count=1)"
        ) && \. "$NVM_DIR/nvm.sh"
    fi
else
    wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
    rm install.sh
fi
npm i --global yarn
# basic usage instruction prompt
zeninf $"NVM has been installed. Please restart your terminal or source your shell configuration file (e.g., .bashrc, .zshrc) to start using it. A browser window will now open with usage instructions."
xdg-open https://github.com/nvm-sh/nvm?tab=readme-ov-file#usage