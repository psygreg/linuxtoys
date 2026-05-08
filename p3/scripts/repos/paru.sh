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
zenwrn "$msg294"
sudo_rq

pkg_install base-devel
git clone --branch paru-bin --single-branch https://github.com/archlinux/aur.git /tmp/paru-bin
cd /tmp/paru-bin && makepkg -s && {
	pkg_fromfile /tmp/paru-bin/paru-bin-*.tar.zst && { zeninf "$msg018"; };
} || { fatal "$msg077"; }