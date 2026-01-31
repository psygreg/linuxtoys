#!/bin/bash
# name: NeoVim
# version: 1.0
# description: nvim_desc
# icon: neovim.svg
# repo: https://neovim.io

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
_packages=(neovim)
sudo_rq
_install_
zeninf "$msg018"