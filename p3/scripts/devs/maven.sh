#!/bin/bash
# name: Maven
# version: 1.0
# description: mvn_desc
# icon: maven

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_packages=(maven)
sudo_rq
_install_