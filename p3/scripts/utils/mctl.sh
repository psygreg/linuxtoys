#!/bin/bash
# name: Mission Center
# version: 1.0
# description: mctl_desc
# icon: mctl
# compat: ubuntu, debian, fedora, suse, cachy, arch, ostree

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive io.missioncenter.MissionCenter