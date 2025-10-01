#!/bin/bash
# name: Déjà Dup Backups
# version: 1.0
# description: Protect yourself from data loss
# icon: dejadup.png

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.gnome.DejaDup

