#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
# icon: nvidia
# compat: debian
# reboot: yes
# nocontainer

# --- Start of the script code ---
cd $HOME
# add Nvidia repository for Debian
wget https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sleep 1
sudo apt-get update
sudo apt-get install cuda-drivers