#!/bin/bash
# NAME: GIMP (& PhotoGIMP)
# VERSION: 3.0
# DESCRIPTION: gimp_desc
# icon: gimp

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.gimp.GIMP
if zenity --question --text "$msg253" --width 360 --height 300; then
    zeninf "$msg254"
    flatpak run org.gimp.GIMP & sleep 1
    PID=($(pgrep -f "gimp"))
    if [ -z "$PID" ]; then
        echo "Failed to find Flatpak process."
        exit 1
    fi
    echo "Found Flatpak app running as PID $PID"
    sleep 20
    for ID in "${PID[@]}"; do
        kill "$ID"
    done
    wait "$PID" 2>/dev/null
    git clone https://github.com/Diolinux/PhotoGIMP.git
    cd PhotoGIMP
    cp -rf .config/* $HOME/.config/
    cp -rf .local/* $HOME/.local/
    cd ..
    rm -rf PhotoGIMP
fi