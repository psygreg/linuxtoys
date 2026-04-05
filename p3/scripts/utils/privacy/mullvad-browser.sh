#!/bin/bash
# name: Mullvad Browser
# version: 1.0
# description: Mullvad Browser
# icon: mullvad_browser.svg
# repo: https://mullvad.net/browser

# --- Start of the script code ---
. /etc/os-release
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    net.mullvad.MullvadBrowser
)
_flatpak_
