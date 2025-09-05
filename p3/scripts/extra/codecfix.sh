#!/bin/bash
# name: codecfix
# version: 1.0
# description: codecfix_desc
# icon: codec.svg
# compat: suse, fedora, ostree

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
if [[ "$ID_LIKE" == *suse* ]]; then
    sudo zypper in -y opi
    sudo opi codecs
    zeninf $"Operations completed."
elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
    rpmfusion_chk
    _packages=(libavcodec-freeworld)
    _install_
    zeninf $"Operations completed."
else
    zeninf $"This script is not compatible with your operating system."
fi