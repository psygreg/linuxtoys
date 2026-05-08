#!/bin/bash
# name: Cockpit Client
# version: 1.0
# description: cockpitclient_desc
# icon: cockpit.png
# repo: https://cockpit-project.org/

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_flat org.cockpit_project.CockpitClient
zeninf "$msg018"