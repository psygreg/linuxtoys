#!/bin/bash
# name: LM Studio
# description: lmstudio_desc
# icon: lmstudio.png
# repo: https://lmstudio.ai
# nocontainer

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

prep_tmp_noram
wget -O lmstudio.appimage https://lmstudio.ai/download/latest/linux/x64?format=AppImage
pkg_appimage lmstudio.appimage
zeninf "$finishmsg"