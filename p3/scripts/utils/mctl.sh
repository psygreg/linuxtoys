#!/bin/bash
# name: Mission Center
# version: 1.0
# description: mctl_desc
# icon: mctl.svg
# compat: ubuntu, debian, fedora, suse, cachy, arch, ostree
# repo: https://missioncenter.io

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_flat io.missioncenter.MissionCenter
zeninf "$msg018"