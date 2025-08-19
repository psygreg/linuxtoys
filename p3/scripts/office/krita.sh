#!/bin/bash
# name: Krita
# version: 1.0
# description: krita_desc
# icon: krita

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.kde.krita
