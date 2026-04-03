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
_flatpaks=(
    org.gnome.World.PikaBackup
)
_flatpak_
zeninf "$msg018"