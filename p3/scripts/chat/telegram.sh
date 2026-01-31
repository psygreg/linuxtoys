#!/bin/bash
# name: Telegram
# version: 1.0
# description: telegram_desc
# icon: telegram.png
# repo: https://desktop.telegram.org/

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.telegram.desktop

