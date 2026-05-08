#!/bin/bash
# name: VLC
# description: vlc_desc
# icon: vlc.svg
# compat: fedora, suse, ubuntu, debian, arch, ostree, cachy, solus
# repo: https://www.videolan.org/vlc/

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
sudo_rq
pkg_install vlc
if is_fedora || is_ostree; then
    rpmfusion_chk
    pkg_install libavcodec-freeworld
elif is_suse; then
    pkg_install opi
    sudo opi codecs
fi
zeninf "$msg018"
