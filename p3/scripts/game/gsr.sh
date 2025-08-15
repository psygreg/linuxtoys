#!/bin/bash
# name: GPU Screen Recorder
# version: 1.0
# description: gsr_desc

# --- Start of the script code ---
flatpak_in_lib
# request sudo, GSR needs to be installed on system level
sudo_rq
flatpak install --or-update --system --noninteractive com.dec05eba.gpu_screen_recorder