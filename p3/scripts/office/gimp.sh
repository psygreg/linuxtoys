#!/bin/bash
# NAME: GIMP (& PhotoGIMP)
# VERSION: 3.0
# DESCRIPTION: gimp_desc
# icon: gimp

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.gimp.GIMP
if zenity --question --text=$"This will install the PhotoGIMP patch for GIMP, making it look and feel more like Adobe Photoshop. This is optional. Proceed?" --width 360 --height 300; then
    zeninf $"Please wait while GIMP starts for the first time to create its configuration files..."
    flatpak run org.gimp.GIMP & sleep 10
    PID=($(pgrep -f "gimp"))
    if [ -z "$PID" ]; then
        echo "Failed to find Flatpak process."
        exit 1
    fi
    echo "Found Flatpak app running as PID $PID"
    sleep 15
    for ID in "${PID[@]}"; do
        kill "$ID"
    done
    wait "$PID" 2>/dev/null
    cd $HOME
    git clone https://github.com/Diolinux/PhotoGIMP.git
    cd PhotoGIMP
    cp -rf .config/* $HOME/.config/
    cp -rf .local/* $HOME/.local/
    cd ..
    rm -rf PhotoGIMP
fi