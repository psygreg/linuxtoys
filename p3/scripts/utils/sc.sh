#!/bin/bash
# name: StreamController
# version: 1.0
# description: sc_desc
# icon: streamcontroller

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive com.core447.StreamController