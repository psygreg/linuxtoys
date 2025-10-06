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
    flatpak run org.gimp.GIMP &
    GIMP_PID=$!
    sleep 10
    if ! kill -0 "$GIMP_PID" 2>/dev/null; then
        echo "Failed to start GIMP."
        exit 1
    fi
    echo "Found GIMP running as PID $GIMP_PID"
    sleep 15
    kill "$GIMP_PID"
    wait "$GIMP_PID" 2>/dev/null
    cd $HOME
    git clone https://github.com/Diolinux/PhotoGIMP.git
    cd PhotoGIMP
    cp -rf .config/* $HOME/.config/
    cp -rf .local/* $HOME/.local/
    cd ..
    rm -rf PhotoGIMP
fi