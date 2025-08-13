#!/bin/bash
# NAME: LibreOffice
# VERSION: 1.0
# DESCRIPTION: libreoffice_desc
# ICON: libreoffice-startcenter

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive org.libreoffice.LibreOffice
