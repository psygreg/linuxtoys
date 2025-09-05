#!/bin/bash
# name: Homebrew
# version: 1.0
# description: brew_desc
# icon: brew.png

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
sudo_rq
curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | bash
zeninf $"Operations completed."