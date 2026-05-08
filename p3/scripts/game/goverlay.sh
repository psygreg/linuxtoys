#!/bin/bash
# name: GOverlay
# version: 1.0
# description: goverlay_desc
# icon: goverlay.svg
# repo: https://github.com/benjamimgois/goverlay

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install mangohud goverlay
if command -v flatpak &> /dev/null; then
    pkg_flat org.freedesktop.Platform.VulkanLayer.MangoHud org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/23.08 org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/24.08 org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/25.08
fi