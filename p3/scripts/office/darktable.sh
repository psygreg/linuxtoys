#!/bin/bash
# name: Darktable
# version: 1.0
# description: darktable_desc

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive org.darktable.Darktable
