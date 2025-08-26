#!/bin/bash
# name: Ungoogled Chromium
# version: 1.0
# description: Ungoogled Chromium
# icon: ungoogled_chromium.png

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../../libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub io.github.ungoogled_software.ungoogled_chromium
