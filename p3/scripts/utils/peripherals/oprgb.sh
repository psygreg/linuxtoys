#!/bin/bash
# name: OpenRGB
# version: 1.0
# description: oprgb_desc
# icon: openrgb.svg
# repo: https://openrgb.org

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
pkg_flat org.openrgb.OpenRGB
if is_fedora || is_ostree; then
    sudo_rq
    rpmfusion_chk
    pkg_install openrgb-udev-rules
else
    prep_tmp
    wget https://openrgb.org/releases/release_0.9/60-openrgb.rules
    sudo_rq
    prep_create /usr/lib/udev/rules.d/60-openrgb.rules
    copy_ -f 60-openrgb.rules /usr/lib/udev/rules.d/
    sudo udevadm control --reload-rules && sudo udevadm trigger
fi
zeninf "$msg036"