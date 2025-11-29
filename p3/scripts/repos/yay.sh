#!/bin/bash
# name: Yay
# version: 1.0
# description: yay_desc
# icon: archpkg.png
# compat: arch
# repo: https://github.com/Jguer/yay

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
zenwrn "$msg294"
sudo_rq

_packages=(base-devel)
_install_

git clone --branch yay-bin --single-branch https://github.com/archlinux/aur.git /tmp/yay-bin
makepkg -fcCd OPTIONS=-debug -D /tmp/yay-bin && {
	sudo pacman --noconfirm -U /tmp/yay-bin/yay-bin-*.tar.zst && { zeninf "$msg018"; };
} || { fatal "$msg077"; }