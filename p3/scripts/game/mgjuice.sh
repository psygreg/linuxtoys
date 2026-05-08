#!/bin/bash
# name: MangoJuice
# version: 1.0
# description: mgjuice_desc
# icon: mangojuice.png
# repo: https://github.com/radiolamp/mangojuice

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install mangohud
pkg_flat com.valvesoftware.Steam.VulkanLayer.MangoHud \
org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/23.08 \
org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/24.08 \
org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/25.08 \
io.github.radiolamp.mangojuice