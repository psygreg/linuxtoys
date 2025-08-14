#!/bin/bash
# name: LucidGlyph
# version: 1.0
# description: lg_desc
# icon: help-about
# compat: ubuntu, debian, arch, fedora, suse, cachy

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
tag=$(curl -s "https://api.github.com/repos/maximilionus/lucidglyph/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
ver="${tag#v}"
if zenity --question --text "$msg020" --width 360 --height 300; then 
    sudo_rq
    cd $HOME

    [ -f "${tag}.tar.gz" ] && rm -f "${tag}.tar.gz"

    wget -O "${tag}.tar.gz" "https://github.com/maximilionus/lucidglyph/archive/refs/tags/${tag}.tar.gz"
    tar -xvzf "${tag}.tar.gz"
    cd lucidglyph-${ver}
    chmod +x lucidglyph.sh
    sudo ./lucidglyph.sh install
    cd ..
    sleep 1
    rm -rf lucidglyph-${ver}
    zeninf "$msg022"
fi