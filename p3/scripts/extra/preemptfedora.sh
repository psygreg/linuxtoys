#!/bin/bash
# name: preemptfedora
# description: preempt_desc
# icon: cpu-x.png
# compat: fedora, ostree
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/optimizers.lib"
preempt_lib || fatal "Check logs for details on the error."
zeninf "$finishmsg"