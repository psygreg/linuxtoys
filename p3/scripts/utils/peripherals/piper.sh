#!/bin/bash
# name: Piper
# version: 1.0
# description: piper_desc
# icon: piper.svg
# reboot: yes

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
if [[ $ID =~ "ubuntu" ]] || [[ $ID =~ "debian" ]] || [[ $ID_LIKE == *ubuntu* ]]; then
    _packages=(ratbagd)
else
    _packages=(libratbag)
fi
_install_
flatpak_in_lib
flatpak install -y --system --noninteractive flathub org.freedesktop.Piper
zeninf "$finishmsg"