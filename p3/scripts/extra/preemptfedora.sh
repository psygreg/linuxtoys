#!/bin/bash
# name: preemptfedora
# description: preempt_desc
# icon: cpu-x.png
# compat: fedora, ostree, rhel
# nocontainer

# --- Start of the script code ---
if is_fedora || is_rhel; then
    grubbyargs_upd 'preempt=full'
elif is_ostree; then
    kargs_upd 'preempt=full'
fi

zeninf "$finishmsg"