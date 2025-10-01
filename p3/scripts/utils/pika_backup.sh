#!/bin/bash
# name: Pika Backup
# version: 1.0
# description: Keep your data safe
# icon: pikabackup.png

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.gnome.World.PikaBackup

