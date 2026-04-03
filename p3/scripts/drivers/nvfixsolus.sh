#!/bin/bash
# name: Solus OS Nvidia Fix
# version: 1.0
# description: nvfixsolus_desc
# icon: nvidia.svg
# compat: solus
# reboot: yes
# nocontainer

source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
nvidia_solus_lib
zeninf "$rebootmsg"