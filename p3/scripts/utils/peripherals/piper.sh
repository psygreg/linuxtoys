#!/bin/bash
# name: Piper
# version: 1.0
# description: piper_desc
# icon: piper.svg
# reboot: yes
# repo: https://github.com/libratbag/piper

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
if is_debian || is_ubuntu; then
    pkg_install ratbagd
elif is_arch || is_cachy || is_solus; then
    pkg_install libratbag
elif is_fedora || is_ostree; then
    pkg_install libratbag-ratbagd
elif is_suse; then
    pkg_install libratbag-tools
fi
pkg_flat org.freedesktop.Piper
zeninf "$finishmsg"