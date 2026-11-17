#!/bin/bash
# name: Pacstall
# version: 1.0
# description: pacstall_desc
# icon: pacstall.png
# repo: https://pacstall.dev
# compat: debian, ubuntu
# revert: no
# architectures: x86_64, aarch64
# requires-script-api: 1

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
sudo bash -c "$(wget -q https://pacstall.dev/q/install -O -)"
zeninf "$msg018"