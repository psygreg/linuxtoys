#!/bin/bash
# name: Nvidia Drivers (v470)
# version: 1.0
# description: nv_desc_470
# icon: nvidia.svg
# compat: arch
# reboot: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
# needs chaotic AUR
chaotic_aur_lib
sudo pacman -S nvidia-470xx-dkms nvidia-470xx-utils nvidia-470xx-settings
cd $HOME
# set proper DRM mode on systemd
wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/10-nvidia.conf
sudo cp 10-nvidia.conf /etc/modprobe.d/
sleep 1
rm 10-nvidia.conf
# refresh boot image
sudo mkinitcpio -P
zenity --info --title="Nvidia Drivers" --text=$"Reboot your system to apply the changes." --width 300 --height 300