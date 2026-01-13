#!/bin/bash
# name: Piper
# version: 1.0
# description: piper_desc
# icon: piper.svg
# reboot: yes
# repo: https://github.com/libratbag/piper

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
if [[ $ID =~ "ubuntu" ]] || [[ $ID =~ "debian" ]] || [[ $ID_LIKE == *ubuntu* ]]; then
    _packages=(ratbagd)
elif is_arch || is_cachy; then
    _packages=(libratbag)
elif is_fedora || is_ostree; then
    _packages=(libratbag-ratbagd)
elif is_suse; then
    _packages=(libratbag-tools)
fi
_install_
flatpak_in_lib
flatpak_install -y --system --noninteractive flathub org.freedesktop.Piper
zeninf "$finishmsg"
