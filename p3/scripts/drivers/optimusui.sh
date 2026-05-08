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
sudo_rq
if is_arch || is_ubuntu; then
    sudo add-apt-repository -y universe
    sudo apt update
    pkg_install bbswitch nvidia-prime
elif is_suse; then
    pkg_install bbswitch suse-prime
elif is_solus; then
    pkg_install bbswitch bbswitch-current
fi
pkg_flat de.z_ray.OptimusUI
zeninf "$msg018"
