#!/bin/bash
# name: Intel Xe Driver
# version: 1.0
# description: intelxe_desc
# icon: intel.png
# reboot: yes
# gpu: Intel
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/optimizers.lib"
sudo_rq
intel_xe_lib
zeninf "$msg036"