#!/bin/bash
# name: Blender
# version: 1.0
# description: blender_desc
# icon: blender

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.blender.Blender
