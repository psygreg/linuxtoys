#!/bin/bash
# name: Cargo
# version: 1.0
# description: cargo_desc
# icon: cargo.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
curl https://sh.rustup.rs -sSf | sh
zeninf $"Operations completed."