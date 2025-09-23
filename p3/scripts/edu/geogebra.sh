#!/bin/bash
# name: GeoGebra
# version: 1.0
# description: geogebra_desc
# icon: geogebra.png

# --- Start of the script code ---
. /etc/os-release
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.geogebra.GeoGebra