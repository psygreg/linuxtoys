#!/bin/bash
# name: GPU Screen Recorder
# version: 1.0
# description: gsr_desc
# icon: gsr.png
# repo: https://git.dec05eba.com/?p=about

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
# request sudo, GSR needs to be installed on system level
sudo_rq
flatpak_in_lib
_flatpak_add_remote_$ID_
flatpak install --or-update --system --noninteractive flathub com.dec05eba.gpu_screen_recorder