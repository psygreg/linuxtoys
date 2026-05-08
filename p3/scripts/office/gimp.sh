#!/bin/bash
# NAME: GIMP (& PhotoGIMP)
# VERSION: 3.0
# DESCRIPTION: gimp_desc
# icon: gimp.svg
# repo: https://www.gimp.org

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_flat org.gimp.GIMP
if zenity --question --text "$msg253" --width 360 --height 300; then
    zeninf "$msg254"
    flatpak run org.gimp.GIMP --batch-interpreter=plug-in-script-fu-eval -b "(gimp-quit 0)" && {
        prep_dir_edit "$HOME/.config/GIMP" "$HOME/.local/share/applications"
        git clone --depth=1 https://github.com/Diolinux/PhotoGIMP.git /tmp/photogimp && {
            (
                copy_ -rvf /tmp/photogimp/.config/* ~/.config/ && copy_ -rvf /tmp/photogimp/.local/* ~/.local/
            ) && { zeninf "$msg018"; } || { fatal "Unable to complete installation"; }
        }
    }
fi