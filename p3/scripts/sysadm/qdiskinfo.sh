#!/bin/bash
# name: QDiskInfo
# description: qdi_desc
# version: 1.0
# icon: qdiskinfo.svg
# repo: https://github.com/edisionnano/QDiskInfo

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
prep_tmp_noram
qdi_ver=$(curl -s https://api.github.com/repos/edisionnano/QDiskInfo/releases/latest | grep '"tag_name"' | cut -d '"' -f4)
wget "https://github.com/edisionnano/QDiskInfo/releases/download/${qdi_ver}/QDiskInfo-x86_64.AppImage"
pkg_appimage "QDiskInfo-x86_64.AppImage"
zeninf "$finishmsg"