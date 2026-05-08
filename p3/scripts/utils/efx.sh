#!/bin/bash
# name: EasyEffects
# version: 1.0
# description: efx_desc
# icon: efx.svg
# repo: https://github.com/wwmm/easyeffects

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
sudo_rq
pkg_flat com.github.wwmm.easyeffects
zeninf "$msg018"