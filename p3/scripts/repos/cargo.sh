#!/bin/bash
# name: Cargo
# version: 1.0
# description: cargo_desc
# icon: cargo.svg
# repo: https://github.com/rust-lang/cargo
# revert: solus


# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
if is_solus; then
    pkg_install rustup
else
    curl https://sh.rustup.rs -sSf | sh
fi
zeninf "$msg018"