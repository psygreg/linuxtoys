#!/bin/bash
# name: Helium Browser
# version: 1.0
# description: helium_desc
# icon: helium.png
# repo: https://helium.computer

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
prep_tmp_noram

helium_ver=$(curl -s "https://api.github.com/repos/imputnet/helium-linux/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
{ [ -z "$helium_ver" ] && fatal "Failed to fetch latest Helium version"; }
wget https://github.com/imputnet/helium-linux/releases/download/$helium_ver/helium-$helium_ver-x86_64.AppImage || fatal "Failed to download Helium AppImage"
pkg_appimage "helium-$helium_ver-x86_64.AppImage"

zeninf "$finishmsg"