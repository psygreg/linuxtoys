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
    timeout 15 flatpak run org.gimp.GIMP
    prep_dir_edit "$HOME/.config/GIMP" "$HOME/.local/share/applications"
    prep_tmp_noram
    git clone --depth=1 https://github.com/Diolinux/PhotoGIMP.git || fatal "Unable to clone remote for PhotoGIMP"
    copy_ -rf PhotoGIMP/.config/* ~/.config/ || fatal "Unable to copy .config files"
    copy_ -rf PhotoGIMP/.local/* ~/.local/ || fatal "Unable to copy .local files"
fi
zeninf "$finishmsg"
