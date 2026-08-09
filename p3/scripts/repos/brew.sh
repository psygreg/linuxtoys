#!/bin/bash
# name: Homebrew
# version: 1.0
# description: brew_desc
# icon: brew.png
# repo: https://brew.sh/
# revert: no

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
askpass
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
info "$finishmsg"