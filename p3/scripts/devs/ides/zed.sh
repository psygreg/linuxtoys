#!/bin/bash
# name: Zed
# version: 1.0
# description: zed_desc
# icon: zed.png
# repo: https://zed.dev

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub dev.zed.Zed

