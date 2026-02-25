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
[ -f "Stoat-linux-x64-${ver}.zip" ] && rm -f "Stoat-linux-x64-${ver}.zip"
wget -O "Stoat-linux-x64-${ver}.zip" "https://github.com/stoatchat/for-desktop/releases/download/${tag}/Stoat-linux-x64-${ver}.zip"
unzip "Stoat-linux-x64-${ver}.zip"
mkdir -p ~/.local/share/stoat
cp -rf Stoat-linux-x64/* ~/.local/share/stoat # install or update
wget -O stoat.png "https://codeberg.org/psygreg/linuxtoys/raw/branch/master/p3/app/icons/stoat.png"
mkdir -p ~/.local/share/icons/hicolor/256x256/apps
cp stoat.png ~/.local/share/icons/hicolor/256x256/apps/stoat.png
wget -O stoat-chat.desktop "https://codeberg.org/psygreg/linuxtoys/raw/branch/master/resources/stoat/stoat-chat.desktop"
sed -i "s|/home/psygreg|${HOME}|g" stoat-chat.desktop
mkdir -p ~/.local/share/applications
cp stoat-chat.desktop ~/.local/share/applications/
chmod +x ~/.local/share/applications/stoat-chat.desktop
rm -rf Stoat-linux-x64-${ver}.zip Stoat-linux-x64 stoat.png stoat-chat.desktop
