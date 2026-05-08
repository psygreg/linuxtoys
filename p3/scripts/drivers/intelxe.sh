#!/bin/bash
# name: Intel Xe Driver
# version: 1.0
# description: intelxe_desc
# icon: intel.png
# reboot: yes
# gpu: Intel
# compat: !fedora, !solus
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
sudo_rq
intel_xe_lib
zeninf "$msg036"