#!/bin/bash
# name: susefix
# version: 1.0
# description: susefix_desc
# icon: suse.svg
# compat: suse

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
if [[ "$ID_LIKE" == *suse* ]]; then
    sudo_rq
    sudo setsebool -P selinuxuser_execmod 1
    zeninf $"SELinux policy has been updated."
else
    nonfatal $"This script is only for OpenSUSE-based distributions."
fi