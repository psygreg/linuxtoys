#!/bin/bash
# name: Topgrade
# version: 1.0
# description: topgrade_desc
# icon: topgrade.svg
# compat: debian, ubuntu, fedora, arch, suse
# repo: https://github.com/topgrade-rs/topgrade

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
sudo_rq
pip_lib
pipx install topgrade
zeninf "$msg018"