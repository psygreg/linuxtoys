#!/bin/bash
# NAME: GIMP (& PhotoGIMP)
# VERSION: 3.0
# DESCRIPTION: gimp_desc
# icon: gimp.svg
# repo: https://www.gimp.org

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.gimp.GIMP
if zenity --question --text "$msg253" --width 360 --height 300; then
    zeninf "$msg254"
    flatpak run org.gimp.GIMP --batch-interpreter=plug-in-script-fu-eval -b "(gimp-quit 0)" && {
        git clone --depth=1 https://github.com/Diolinux/PhotoGIMP.git /tmp/photogimp && {
            (
                cp -rvf /tmp/photogimp/.config/* ~/.config/ && cp -rvf /tmp/photogimp/.local/* ~/.local/
            ) && { zeninf "$msg018"; } || { fatal "Unable to complete installation"; }
        }
    }
fi