#!/bin/bash
# name: Nala
# description: nala_desc
# version: 1.0
# icon: terminal.svg
# compat: ubuntu, debian
# repo: https://gitlab.com/volian/nala

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
sudo apt install -y nala