#!/bin/bash
# name: Pika Backup
# version: 1.0
# description: pika_desc
# icon: pika.svg
# repo: https://apps.gnome.org/PikaBackup/

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub org.gnome.World.PikaBackup
zeninf "$msg018"
