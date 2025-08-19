#!/bin/bash
# name: GPU Screen Recorder
# version: 1.0
# description: gsr_desc
# icon: gsr

# --- Start of the script code ---
flatpak_in_lib
# request sudo, GSR needs to be installed on system level
sudo_rq
_flatpak_add_remote_$ID_
flatpak install --or-update --system --noninteractive flathub com.dec05eba.gpu_screen_recorder