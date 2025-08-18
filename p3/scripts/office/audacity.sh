#!/bin/bash
# NAME: Audacity
# VERSION: 1.0
# DESCRIPTION: audacity_desc
# icon: audacity

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive org.audacityteam.Audacity
