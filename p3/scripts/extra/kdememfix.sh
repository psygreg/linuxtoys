#!/bin/bash
# name: Plasma VRAM Fix
# version: 1.0
# description: kdememfix_desc
# icon: preload.svg
# desktop: plasma
# compat: none
# optimized-only: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/optimizers.lib"
plasma_mem_fix
zeninf "$rebootmsg" # while immediate rebooting is not necessary, so I won´t lock the reboot header option, it is still required for the environment variable to take effect.