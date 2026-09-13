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
if [ ! -f /etc/apt/apt.conf.d/99-amd64v3 ] && [[ "$SUPPORTED" == *"supported"* ]]; then
    echo "CPU supports x86-64-v3, proceeding. This will take a while."
    prep_create /etc/apt/apt.conf.d/99-amd64v3
    echo 'APT::Architecture-Variants "amd64v3";' | sudo tee /etc/apt/apt.conf.d/99-amd64v3 > /dev/null
    sudo apt update
    sudo apt upgrade -y
    info "$rebootmsg"
else
    [ -f /etc/apt/apt.conf.d/99-amd64v3 ] && { { [ -n "$OPTIMIZER_RUN" ] && echo "$msg234"; } || info "$msg234" && exit 100; }
    { [ -n "$OPTIMIZER_RUN" ] && echo "CPU is not x86_64v3, skipping"; } || die "$incompatmsg"
fi