#!/bin/bash
# name: KiCad
# version: 1.0
# description: kicad_desc
# icon: kicad

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive org.kicad.KiCad
