#!/bin/bash
# name: gtk_bmg_fix
# version: 1.0
# description: gtk_bmg_fix_desc
# icon: intel.png
# reboot: yes
# gpu: Intel, Nvidia
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/optimizers.lib"
sudo_rq
fix_intel_gtk
zeninf "$msg036"