#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
# icon: nvidia.svg
# compat: debian
# reboot: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
cd $HOME
# add Nvidia repository for Debian
wget https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb
sleep 1
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sleep 1
sudo apt-get update
sleep 1
sudo apt-get install -y cuda-drivers
sleep 1
sudo update-initramfs -u
sleep 1
sudo update-grub
zeninf "$msg036"