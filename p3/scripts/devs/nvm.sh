#!/bin/bash
# name: Node Version Manager
# version: 1.0
# description: nvm_desc
# icon: nvm

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
rm install.sh
npm i --global yarn
# basic usage instruction prompt
zeninf "$msg136"
xdg-open https://github.com/nvm-sh/nvm?tab=readme-ov-file#usage