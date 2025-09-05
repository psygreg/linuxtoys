#!/bin/bash
# name: Topgrade
# version: 1.0
# description: topgrade_desc
# icon: topgrade.svg
# compat: debian, ubuntu, fedora, arch, suse

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
pip_lib
pip install topgrade
zeninf $"Operations completed."