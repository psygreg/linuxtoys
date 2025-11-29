#!/bin/bash
# name: codecfix
# version: 1.0
# description: codecfix_desc
# icon: codec.svg
# compat: suse, fedora, ostree

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
sudo_rq
if [[ "$ID_LIKE" == *suse* ]]; then
    sudo zypper in -y opi
    sudo opi codecs
    zeninf "$msg018"
elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
    rpmfusion_chk
    _packages=(libavcodec-freeworld gstreamer1-plugins-ugly)
    _install_
    zeninf "$msg018"
else
    zeninf "$msg077"
fi
