#!/bin/bash
# name: Telegram
# version: 1.0
# description: New era of messaging
# icon: telegram.png

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.telegram.desktop

