#!/bin/bash
# name: Cockpit Client
# version: 1.0
# description: cockpitclient_desc
# icon: cockpit.png
# repo: https://cockpit-project.org/

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub org.cockpit_project.CockpitClient
zeninf "$msg018"
