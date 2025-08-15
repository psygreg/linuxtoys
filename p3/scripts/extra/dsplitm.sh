#!/bin/bash
# name: dsplitm
# version: 1.0
# description: dsplitm_desc
# icon: help-about
# compat: ubuntu, debian, suse, fedora, arch, cachy
# reboot: yes

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/optimizers.lib"
. /etc/os-release
if [ ! -f "$HOME/.local/.autopatch.state" ]; then
    dsplitm_lib
else
    nonfatal "$msg234"
fi