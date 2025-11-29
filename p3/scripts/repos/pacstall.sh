#!/bin/bash
# name: Pacstall
# version: 1.0
# description: pacstall_desc
# icon: pacstall.png
# repo: https://pacstall.dev
# compat: debian, ubuntu

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
sudo bash -c "$(wget -q https://pacstall.dev/q/install -O -)"
zeninf "$msg018"