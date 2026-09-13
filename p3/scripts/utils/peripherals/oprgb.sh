#!/bin/bash
# name: OpenRGB
# version: 1.0
# description: oprgb_desc
# icon: openrgb.svg
# repo: https://openrgb.org
# compat: !steamos

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_

fetch_openrgb_rules() {
    local REPO ASSET TAG URL
    REPO="CalcProgrammer1/OpenRGB"
    ASSET="60-openrgb.rules"
    TAG=$(curl -sL "https://api.github.com/repos/${REPO}/releases/latest" \
      | grep -Po '"tag_name":\s*"\K[^"]+')
    URL="https://github.com/${REPO}/releases/download/${TAG}/${ASSET}"
    wget "$URL"
}

pkg_fromrelease https://github.com/CalcProgrammer1/OpenRGB
if is_fedora || is_ostree || is_rhel; then
    askpass
    rpmfusion_chk
    pkg_install openrgb-udev-rules
else
    fetch_openrgb_rules
    askpass
    prep_create /usr/lib/udev/rules.d/60-openrgb.rules
    copy_ -f 60-openrgb.rules /usr/lib/udev/rules.d/
    sudo udevadm control --reload-rules && sudo udevadm trigger
fi
info "$msg036"