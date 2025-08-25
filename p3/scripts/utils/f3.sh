#!/bin/bash
# name: F3 (Fight Flash Fraud)
# version: 1.0
# description: f3_desc
# icon: utils.svg
# compat: ubuntu, debian, fedora, arch, suse, cachy
# nocontainer

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
_packages=(f3)
sudo_rq
_install_
zeninf "$msg018"
