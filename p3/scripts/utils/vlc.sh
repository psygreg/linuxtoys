#!/bin/bash
# name: VLC
# description: vlc_desc
# icon: vlc.svg
# compat: fedora, suse, ubuntu, debian, arch, ostree, cachy

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
sudo_rq
_packages=(vlc)
if [ "$ID" == "fedora" ] || [ "$ID" == "rhel" ] ||  [[ "$ID_LIKE" =~ "fedora" ]]; then
    rpmfusion_chk
    _packages+=(libavcodec-freeworld)
elif [ "$ID" = "suse" ] || [[ "$ID" =~ "opensuse" ]] || [[ "$ID_LIKE" =~ "suse" ]]; then
    sudo zypper in -y opi
    sudo opi codecs
fi
_install_
zeninf "$msg018"
