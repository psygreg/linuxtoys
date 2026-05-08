#!/bin/bash
# name: Mullvad Browser
# version: 1.0
# description: Mullvad Browser
# icon: mullvad_browser.svg
# repo: https://mullvad.net/browser

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_flat net.mullvad.MullvadBrowser

