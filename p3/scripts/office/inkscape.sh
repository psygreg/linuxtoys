#!/bin/bash
# name: Inkscape
# version: 1.0
# description: inkscape_desc

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive org.inkscape.Inkscape
