#!/bin/bash
# NAME: Zen Browser
# VERSION: 1.0
# DESCRIPTION: zen_desc
# icon: zenbrowser

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub app.zen_browser.zen
