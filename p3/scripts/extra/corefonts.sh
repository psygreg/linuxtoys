#!/bin/bash
# name: Microsoft CoreFonts
# version: 1.0
# description: mscf_desc
# icon: mscf.svg
# nocontainer

# --- Start of the script code ---
LT_PROGRAM="Microsoft CoreFonts"
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
if [ ! -d "$HOME/.local/share/fonts/mscorefonts" ]; then
    _packages=(cabextract)
    _install_
    # get corefonts
    _sfpath="http://downloads.sourceforge.net/corefonts"
    fonts=($_sfpath/andale32.exe $_sfpath/arial32.exe $_sfpath/arialb32.exe $_sfpath/comic32.exe $_sfpath/courie32.exe $_sfpath/georgi32.exe
    $_sfpath/impact32.exe $_sfpath/times32.exe $_sfpath/trebuc32.exe $_sfpath/verdan32.exe $_sfpath/webdin32.exe)
    cd $HOME
    for i in "${fonts[@]}"; do
        wget $i
        cabextract $(basename $i) -d fonts
    done
    # install corefonts for user - flatpak and atomic compatible
    mkdir -p ~/.local/share/fonts
    mkdir -p ~/.local/share/fonts/mscorefonts
    cp -v fonts/*.ttf fonts/*.TTF ~/.local/share/fonts/mscorefonts/
    rm *32.exe
    rm -r fonts
    zeninf $"Operations completed."
else
    if zenity --question --text=$"This program is already installed. Do you want to remove it?" --width 360 height 300; then
        rm -rf ~/.local/share/fonts/mscorefonts
        zeninf $"Operations completed."
    fi
    exit 100
fi