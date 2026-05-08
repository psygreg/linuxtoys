#!/bin/bash
# name: Shelly
# description: shelly_desc
# icon: shelly.png
# compat: arch
# repo: https://github.com/Seafoam-Labs/Shelly-ALPM

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install shelly
zeninf "$msg018"