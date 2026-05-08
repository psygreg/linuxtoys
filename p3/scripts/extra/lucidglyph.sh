#!/bin/bash
# name: LucidGlyph
# version: 1.0
# description: lg_desc
# icon: lucidglyph.svg
# compat: ubuntu, debian, arch, fedora, suse, cachy, !zorin, !solus
# nocontainer
# desktop: other
# repo: https://github.com/maximilionus/lucidglyph/tree/v0.11.0
# revert: internal

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
detect_lucidglyph() {
    # Check for system-wide installation metadata
    if [ -f "/usr/share/lucidglyph/info" ] || [ -f "/usr/share/freetype-envision/info" ]; then
        return 0
    fi
    # Check for user installation metadata
    if [ -f "$HOME/.local/share/lucidglyph/info" ]; then
        return 0
    fi
    # Check for fontconfig files as fallback detection
    if [ -d "/etc/fonts/conf.d" ] && find "/etc/fonts/conf.d" -name "*lucidglyph*" -o -name "*freetype-envision*" 2>/dev/null | grep -q .; then
        return 0
    fi
    if [ -d "$HOME/.config/fontconfig/conf.d" ] && find "$HOME/.config/fontconfig/conf.d" -name "*lucidglyph*" -o -name "*freetype-envision*" 2>/dev/null | grep -q .; then
        return 0
    fi
    # Check for environment markers
    if [ -f "/etc/environment" ] && grep -q "LUCIDGLYPH\|FREETYPE_ENVISION" "/etc/environment" 2>/dev/null; then
        return 0
    fi
    return 1
}
# Function to uninstall LucidGlyph
uninstall_lucidglyph() {
    if [ -f "/usr/share/lucidglyph/uninstaller.sh" ] && [ -x "/usr/share/lucidglyph/uninstaller.sh" ]; then
        sudo "/usr/share/lucidglyph/uninstaller.sh"
    elif [ -f "/usr/share/freetype-envision/uninstaller.sh" ] && [ -x "/usr/share/freetype-envision/uninstaller.sh" ]; then
        sudo "/usr/share/freetype-envision/uninstaller.sh"
    elif [ -f "$HOME/.local/share/lucidglyph/uninstaller.sh" ] && [ -x "$HOME/.local/share/lucidglyph/uninstaller.sh" ]; then
        "$HOME/.local/share/lucidglyph/uninstaller.sh"
    fi
}
# Check if LucidGlyph is already installed
if detect_lucidglyph; then
    if zenity --question --text "$msg285" --width 360 --height 300; then
        sudo_rq
        uninstall_lucidglyph
        zeninf "$msg036"
        exit 0
    else
        exit 100
    fi
fi
tag=$(curl -s "https://api.github.com/repos/maximilionus/lucidglyph/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
ver="${tag#v}"
sudo_rq
prep_tmp
[ -f "${tag}.tar.gz" ] && rm -f "${tag}.tar.gz"
wget -O "${tag}.tar.gz" "https://github.com/maximilionus/lucidglyph/archive/refs/tags/${tag}.tar.gz"
tar -xvzf "${tag}.tar.gz"
cd "lucidglyph-${ver}" || exit 1
chmod +x lucidglyph.sh
sudo ./lucidglyph.sh install
zeninf "$msg036"
