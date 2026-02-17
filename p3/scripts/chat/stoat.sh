#!/bin/bash
# name: Stoat
# version: 1.0
# description: stoat_desc
# icon: stoat.png
# repo: https://stoat.chat

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
tag=$(curl -s "https://api.github.com/repos/stoatchat/for-desktop/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
ver="${tag#v}"
cd "$HOME" || exit 1
[ -f "Stoat-linux-x64-${tag}.zip" ] && rm -f "Stoat-linux-x64-${tag}.zip"
wget -O "Stoat-linux-x64-${tag}.zip" "https://github.com/stoatchat/for-desktop/archive/refs/tags/Stoat-linux-x64-${tag}.zip"
unzip "Stoat-linux-x64-${tag}.zip"
cp -rf Stoat-linux-x64/* ~/.local/share/stoat # install or update
wget # TODO png icon file raw
wget # TODO desktop file raw
cp stoat.png ~/.local/share/icons/hicolor/256x256/apps/stoat.png
sed -i "s|/home/psygreg|$HOME|g" stoat-chat.desktop
cp stoat-chat.desktop ~/.local/share/applications/