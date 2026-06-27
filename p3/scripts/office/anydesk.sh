#!/bin/bash
# NAME: AnyDesk
# VERSION: 1.0
# DESCRIPTION: anydesk_desc
# icon: anydesk.svg
# repo: https://www.anydesk.com
# compat: fedora, ostree, rhel, debian, ubuntu

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
prep_tmp_noram
anydesk_ver="8.0.3-1" # needs routine update checks
if is_ubuntu || is_debian; then
    wget "https://download.anydesk.com/linux/anydesk_${anydesk_ver}_amd64.deb"
    pkg_fromfile "./anydesk_${anydesk_ver}_amd64.deb"
else
    wget "https://download.anydesk.com/linux/anydesk_${anydesk_ver}_x86_64.rpm"
    pkg_fromfile "./anydesk_${anydesk_ver}_x86_64.rpm"
fi
zeninf "$finishmsg"
