#!/bin/bash
# name: FreeCAD
# version: 1.0
# description: freecad_desc
# icon: freecad

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.freecad.FreeCAD
