#!/bin/bash
# name: Signal Desktop
# version: 1.0
# description: signal_desc
# icon: signal.png
# repo: https://signal.org/

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.signal.Signal

