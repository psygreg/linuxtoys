#!/bin/bash
# name: NeoVim
# version: 1.0
# description: nvim_desc
# icon: neovim.svg
# repo: https://neovim.io

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install neovim
zeninf "$msg018"