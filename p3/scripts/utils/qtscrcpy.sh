#!/bin/bash
# name: QtScrcpy
# description: qtscrcpy_desc
# icon: qtscrcpy.png
# repo: https://github.com/barry-ran/QtScrcpy
# new

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

get_qtscrcpy () {
    local download_url
    download_url=$(curl -s "https://api.github.com/repos/barry-ran/QtScrcpy/releases/latest" | grep -oP '"browser_download_url": "\K(.*\.AppImage)(?=")')
    wget -O qtscrcpy.appimage "$download_url"
}

prep_tmp_noram
get_qtscrcpy
pkg_appimage qtscrcpy.appimage
zeninf "$finishmsg"