#!/bin/bash
# name: FreeCAD
# version: 1.0
# description: freecad_desc

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive org.freecad.FreeCAD
