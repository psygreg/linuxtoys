#!/bin/bash
# name: Cargo
# version: 1.0
# description: cargo_desc
# icon: rust

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
curl https://sh.rustup.rs -sSf | sh
zeninf "$msg018"