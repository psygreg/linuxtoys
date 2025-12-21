#!/bin/bash
# name: KeePassXC
# version: 1.0
# description: keepassxc_desc
# icon: keepassxc.png
# repo: https://keepassxc.org

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.keepassxc.KeePassXC

