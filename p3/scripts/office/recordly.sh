#!/bin/bash
# name: Recordly
# description: recordly_desc
# icon: recordly.png
# repo: https://recordly.dev
# new

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
prep_tmp_noram

recordly_ver=$(curl -s "https://api.github.com/repos/webadderallorg/Recordly/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
{ [ -z "$recordly_ver" ] && fatal "Failed to fetch latest Recordly version"; }
wget "https://github.com/webadderallorg/Recordly/releases/download/$recordly_ver/Recordly-linux-x64.AppImage" || fatal "Failed to download Recordly AppImage"
pkg_appimage "Recordly-linux-x64.AppImage"

zeninf "$finishmsg"