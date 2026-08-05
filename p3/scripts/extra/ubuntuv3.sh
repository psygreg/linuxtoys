#!/bin/bash
# name: ubuntuv3
# description: ubuntuv3_desc
# icon: ubuntu.png
# compat: ubuntu
# reboot: yes
# nocontainer

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

# verificação de compatibilidade
SUPPORTED=$(/lib64/ld-linux-x86-64.so.2 --help | grep -i "x86-64-v3" | grep -i "supported" || echo "")
{ [[ "$SUPPORTED" == *"supported"* ]] && echo "CPU supports x86-64-v3, proceeding. This will take a while."; } || die "$hwincompat"

prep_create /etc/apt/apt.conf.d/99-amd64v3
echo 'APT::Architecture-Variants "amd64v3";' | sudo tee /etc/apt/apt.conf.d/99-amd64v3 > /dev/null
sudo apt update
sudo apt upgrade -y

info "$rebootmsg"