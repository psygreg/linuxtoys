#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
# icon: nvidia.svg
# compat: solus
# reboot: yes
# nocontainer
# gpu: Nvidia

source "$SCRIPT_DIR/libs/linuxtoys.bash"
_lang_

askpass
pkg_install nvidia-open-current
bootloader_upd
info "$rebootmsg"