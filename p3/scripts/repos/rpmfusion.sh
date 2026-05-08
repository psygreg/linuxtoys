#!/bin/bash
# name: RPM Fusion
# version: 1.0
# description: rpmfusion_desc
# icon: rpmfusion.svg
# compat: fedora, ostree
# repo: https://rpmfusion.org

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
sudo_rq
rpmfusion_chk
zeninf "$msg018"