#!/bin/bash
# name: Microsoft CoreFonts
# version: 1.0
# description: mscf_desc
# icon: mscf.svg
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if [ ! -d "$HOME/.local/share/fonts/mscorefonts" ]; then
    pkg_install cabextract
    # get corefonts
    _sfpath="http://downloads.sourceforge.net/corefonts"
    fonts=($_sfpath/andale32.exe $_sfpath/arial32.exe $_sfpath/arialb32.exe $_sfpath/comic32.exe $_sfpath/courie32.exe $_sfpath/georgi32.exe
    $_sfpath/impact32.exe $_sfpath/times32.exe $_sfpath/trebuc32.exe $_sfpath/verdan32.exe $_sfpath/webdin32.exe)
    prep_tmp
    for i in "${fonts[@]}"; do
        wget $i
        cabextract $(basename $i) -d fonts
    done
    # install corefonts for user - flatpak and atomic compatible
    prep_dir ~/.local/share/fonts/mscorefonts
    copy_ -v fonts/*.ttf fonts/*.TTF ~/.local/share/fonts/mscorefonts/
    zeninf "$msg018"
fi
