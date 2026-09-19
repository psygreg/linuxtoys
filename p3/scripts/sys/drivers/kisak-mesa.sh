#!/bin/bash
# name: Kisak-Mesa
# description: kisak_desc
# icon: kisak.svg
# compat: ubuntu
# nocontainer
# revert: no
# reboot: yes
# gpu: AMD, Intel

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
sudo add-apt-repository ppa:kisak/kisak-mesa -y
sudo apt update
sudo apt upgrade -y
zeninf "$rebootmsg"