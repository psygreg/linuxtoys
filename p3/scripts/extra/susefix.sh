#!/bin/bash
# name: susefix
# version: 1.0
# description: susefix_desc
# icon: suse.svg
# compat: suse

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
if [[ "$ID_LIKE" == *suse* ]]; then
    sudo_rq
    sudo setsebool -P selinuxuser_execmod 1
    zeninf "$msg022"
else
    nonfatal "$msg073"
fi