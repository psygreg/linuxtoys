#!/bin/bash
# name: Krita
# version: 1.0
# description: krita_desc

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive org.kde.krita
