#!/bin/bash
# name: Intel Xe Driver
# version: 1.0
# description: intelxe_desc
# icon: intel.png
# reboot: yes
# gpu: Intel
# compat: !fedora, !solus, !rhel, !pika
# nocontainer
# hybridgpu: no

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
askpass
intel_xe_lib
info "$rebootmsg"