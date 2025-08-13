#!/bin/bash
# name: susefix
# version: 1.0
# description: susefix_desc
# icon: help-about
# compat: suse

# --- Start of the script code ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../libs/linuxtoys.lib"
. /etc/os-release
# language
_lang_
source "$SCRIPT_DIR/../libs/lang/${langfile}.lib"
if [[ "$ID_LIKE" == *suse* ]]; then
    sudo_rq
    sudo setsebool -P selinuxuser_execmod 1
    zeninf "$msg022"
else
    nonfatal "$msg073"
fi