#!/bin/bash
# name: minfreefix
# version: 1.0
# description: minfreefix_desc
# icon: preload.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy
# optimized-only: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/optimizers.lib"
free_mem_fix
zeninf "$rebootmsg" # while immediate rebooting is not necessary, so I won