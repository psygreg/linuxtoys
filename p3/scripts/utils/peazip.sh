#!/bin/bash
# name: PeaZip
# version: 1.0
# description: Free file archiver utility
# icon: peazip.png

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub io.github.peazip.PeaZip

