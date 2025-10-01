#!/bin/bash
# name: Audacity
# version: 1.0
# description: Audacity is the world's most popular audio editing and recording app
# icon: audacity.png

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.audacityteam.Audacity

