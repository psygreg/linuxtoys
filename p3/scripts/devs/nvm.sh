#!/bin/bash
# name: Node Version Manager
# version: 1.0
# description: nvm_desc
# icon: nvm.svg
# repo: https://github.com/nvm-sh

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_ostree; then
    if [ ! -d "$HOME/.nvm" ]; then
    # revert to 'manual install' procedure, script doesn't work properly for atomic Fedora
        pkg_install nodejs npm
        prep_dir "$HOME/.nvm"
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
    prep_tmp
    wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
fi
# Configure npm to install global packages in user directory to avoid permission issues
prep_dir "$HOME/.npm-global"
npm config set prefix "$HOME/.npm-global"
# Add npm-global to shell config files
NPM_PATH_CONFIG='
# Add npm-global bin to PATH
if ! echo "$PATH" | grep -q "$HOME/.npm-global/bin"; then
    export PATH="$HOME/.npm-global/bin:$PATH"
fi'
for shell_config in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$shell_config" ] && ! grep -q ".npm-global/bin" "$shell_config"; then
        echo "$NPM_PATH_CONFIG" >> "$shell_config"
    fi
done
npm i --global yarn
# basic usage instruction prompt
zeninf "$msg136"
xdg-open https://github.com/nvm-sh/nvm?tab=readme-ov-file#usage