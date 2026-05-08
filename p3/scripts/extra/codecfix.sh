#!/bin/bash
# name: codecfix
# version: 1.0
# description: codecfix_desc
# icon: codec.svg
# compat: suse, fedora, ostree

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
sudo_rq
if is_suse; then
    pkg_install opi
    sudo opi codecs
    zeninf "$msg018"
elif is_fedora || is_ostree; then
    rpmfusion_chk
    pkg_install libavcodec-freeworld gstreamer1-plugins-ugly
    zeninf "$msg018"
else
    zeninf "$msg077"
fi
