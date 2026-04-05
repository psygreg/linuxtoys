#!/bin/bash
# name: OptimusUI
# version: 1.0
# description: optimusui_desc
# icon: optimusui.svg
# reboot: yes
# nocontainer
# gpu: nvidia
# compat: arch, ubuntu, suse, solus

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/$langfile.lib"
sudo_rq
if is_arch || is_ubuntu; then
    sudo add-apt-repository -y universe
    sudo apt update
    _packages=(bbswitch nvidia-prime)
elif is_suse; then
    _packages=(bbswitch suse-prime)
elif is_solus; then
    _packages=(bbswitch bbswitch-current)
fi
_install_
_flatpaks=(
    de.z_ray.OptimusUI
)
_flatpak_
zeninf "$msg018"
