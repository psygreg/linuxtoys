#!/bin/bash
# name: susefix
# version: 1.0
# description: susefix_desc
# icon: suse.svg
# compat: suse
# optimized-only: yes
# revert: no

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
if is_suse; then
    sudo_rq
    sudo setsebool -P selinuxuser_execmod 1
    zeninf "$msg022"
else
    nonfatal "$msg073"
fi