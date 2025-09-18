#!/bin/bash
# name: OpenRGB
# version: 1.0
# description: oprgb_desc
# icon: openrgb.svg

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.openrgb.OpenRGB
if [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
    sudo_rq
    rpmfusion_chk
    _packages=(openrgb-udev-rules)
    _install_
else
    cd $HOME
    wget https://openrgb.org/releases/release_0.9/60-openrgb.rules
    sudo_rq
    sudo cp 60-openrgb.rules /usr/lib/udev/rules.d/
    sudo udevadm control --reload-rules && sudo udevadm trigger
    rm 60-openrgb.rules
fi
zeninf "$msg036"