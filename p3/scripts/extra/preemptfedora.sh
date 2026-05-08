#!/bin/bash
# name: preemptfedora
# description: preempt_desc
# icon: cpu-x.png
# compat: fedora, ostree
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
preempt_lib
zeninf "$finishmsg"