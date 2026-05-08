#!/bin/bash
# name: Stoat
# version: 1.0
# description: stoat_desc
# icon: stoat.png
# repo: https://stoat.chat
# compat: none

# TODO REWORK WHEN APP IS STABLE
# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
tag=$(curl -s "https://api.github.com/repos/stoatchat/for-desktop/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
ver="${tag#v}"
prep_tmp
[ -f "Stoat-linux-x64-${ver}.zip" ] && rm -f "Stoat-linux-x64-${ver}.zip"
wget -O "Stoat-linux-x64-${ver}.zip" "https://github.com/stoatchat/for-desktop/releases/download/${tag}/Stoat-linux-x64-${ver}.zip"
unzip "Stoat-linux-x64-${ver}.zip"

prep_dir "$HOME/.local/share/stoat"
cp -rf Stoat-linux-x64/* ~/.local/share/stoat # install or update
fetch_from_mirror "stoat.png" \
    "https://raw.githubusercontent.com/psygreg/linuxtoys/master/p3/app/icons/stoat.png" \
    "https://git.linux.toys/psygreg/linuxtoys/raw/branch/master/p3/app/icons/stoat.png"
prep_dir "$HOME/.local/share/icons/hicolor/256x256/apps"
prep_create "$HOME/.local/share/icons/hicolor/256x256/apps/stoat.png"
cp stoat.png ~/.local/share/icons/hicolor/256x256/apps/stoat.png
fetch_from_mirror "stoat-chat.desktop" \
    "https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/stoat/stoat-chat.desktop" \
    "https://git.linux.toys/psygreg/linuxtoys/raw/branch/master/resources/stoat/stoat-chat.desktop"
sed -i "s|/home/psygreg|${HOME}|g" stoat-chat.desktop
prep_dir "$HOME/.local/share/applications"
prep_create "$HOME/.local/share/applications/stoat-chat.desktop"
cp stoat-chat.desktop ~/.local/share/applications/
chmod +x ~/.local/share/applications/stoat-chat.desktop
rm -rf Stoat-linux-x64-${ver}.zip Stoat-linux-x64 stoat.png stoat-chat.desktop
