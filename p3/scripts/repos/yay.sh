#!/bin/bash
# name: Yay
# version: 1.0
# description: Yet another yogurt. Pacman wrapper and AUR helper written in go.
# icon: archpkg.png
# compat: arch

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
sudo_rq

_packages=(base-devel)
_install_

git clone --branch yay-bin --single-branch https://github.com/archlinux/aur.git /tmp/yay-bin
makepkg -fcCd OPTIONS=-debug -D /tmp/yay-bin && {
	sudo pacman --noconfirm -U /tmp/yay-bin/yay-bin-*.tar.zst && { zeninf "$msg018"; };
} || { fatal "$msg077"; }