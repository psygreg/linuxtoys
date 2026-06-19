#!/bin/bash
# name: Figma
# version: 1.0
# description: figma_desc
# icon: figma.svg
# repo: https://github.com/arximus88/figma-linux-next

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
prep_tmp
figma_ver=$(curl -s https://api.github.com/repos/arximus88/figma-linux-next/releases/latest | grep '"tag_name"' | cut -d '"' -f4 | sed 's/^v//')
wget "https://github.com/arximus88/figma-linux-next/releases/download/v${figma_ver}/figma-linux-next_${figma_ver}_linux_x86_64.AppImage"
pkg_appimage "figma-linux-next_${figma_ver}_linux_x86_64.AppImage"
zeninf "$finishmsg"
