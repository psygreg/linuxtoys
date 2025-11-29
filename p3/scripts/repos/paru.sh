#!/bin/bash
# name: Paru
# version: 1.0
# description: paru_desc
# icon: archpkg.png
# compat: arch
# repo: https://github.com/Morganamilo/paru

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
zenwrn "$msg294"
sudo_rq

_packages=(base-devel)
_install_

git clone --branch paru-bin --single-branch https://github.com/archlinux/aur.git /tmp/paru-bin
makepkg -fcCd OPTIONS=-debug -D /tmp/paru-bin && {
	sudo pacman --noconfirm -U /tmp/paru-bin/paru-bin-*.tar.zst && { zeninf "$msg018"; };
} || { fatal "$msg077"; }