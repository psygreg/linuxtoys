#!/bin/bash
# name: pNPm
# version: 1.0
# description: Fast, disk space efficient package manager
# icon: pnpm.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_

type -p node || { sudo_rq; _packages=(nodejs); _install_; }

curl -fsSL https://get.pnpm.io/install.sh | sh -