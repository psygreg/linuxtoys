#!/bin/bash
# name: gtk_bmg_fix
# version: 1.0
# description: gtk_bmg_fix_desc
# icon: intel.png
# reboot: yes
# gpu: Intel, Nvidia
# nocontainer
# compat: !solus

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
sudo_rq
fix_intel_gtk
zeninf "$msg036"