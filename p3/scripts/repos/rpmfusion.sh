#!/bin/bash
# name: RPM Fusion
# version: 1.0
# description: rpmfusion_desc
# icon: rpmfusion
# compat: fedora, ostree

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
rpmfusion_chk