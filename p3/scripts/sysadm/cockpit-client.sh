#!/bin/bash
# name: Cockpit Client
# version: 1.0
# description: cockpitclient_desc
# icon: cockpit.png

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.cockpit_project.CockpitClient
zeninf $"Operations completed."