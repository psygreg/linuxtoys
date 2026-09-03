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
askpass

if ( is_intel && [[ -n $intel_arc ]] ) || is_nvidia; then
    if ! grep -q '^GSK_RENDERER=' /etc/environment 2>/dev/null; then
        prep_edit /etc/environment
        echo 'GSK_RENDERER=gl' | sudo tee -a /etc/environment
    fi
fi

info "$rebootmsg"