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
zenwrn "$msg294"
sudo_rq

pkg_install base-devel
git clone --branch yay-bin --single-branch https://github.com/archlinux/aur.git /tmp/yay-bin
cd /tmp/yay-bin && makepkg -s && {
	pkg_fromfile /tmp/yay-bin/yay-bin-*.tar.zst && { zeninf "$msg018"; };
} || { fatal "$msg077"; }