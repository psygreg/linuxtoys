#!/bin/bash
# name: Kdenlive
# version: 1.0
# description: kdenlive_desc
# icon: kdenlive

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive org.kde.kdenlive
