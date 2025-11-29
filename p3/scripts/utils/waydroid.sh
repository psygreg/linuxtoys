#!/bin/bash
# name: Waydroid
# version: 1.0
# description: waydroid_desc
# icon: waydroid.svg
# compat: fedora, ostree, debian, ubuntu, arch, cachy, ublue
# nocontainer
# gpu: Amd, Intel
# repo: https://waydro.id/

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    sudo_rq
    _packages=(waydroid)
    if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
        sudo apt install -y curl ca-certificates
        curl -s https://repo.waydro.id | sudo bash
        sleep 1
        _packages+=(python3-venv)
    fi
    _install_
    sudo systemctl enable --now waydroid-container
    waydroid init -c https://ota.waydro.id/system -v https://ota.waydro.id/vendor -s GAPPS
    if command -v firewall-cmd &> /dev/null; then # fedora rules for waydroid networking
        sudo firewall-cmd --zone=trusted --add-interface=waydroid0 --permanent
    elif command -v ufw &> /dev/null; then # other systems with ufw
        sudo ufw allow 53
        sudo ufw allow 67
        sudo ufw default allow FORWARD     
    fi
    sudo iptables -P FORWARD ACCEPT # forward policy accept for iptables
    if zenity --question --title="Waydroid" --text="$msg283" --width 300 --height 300; then
        waydroid session stop
        sudo waydroid container stop
        cd $HOME
        git clone https://github.com/casualsnek/waydroid_script
        cd waydroid_script
        pip_lib
        python3 -m venv venv
        venv/bin/pip install -r requirements.txt
        # Detect CPU vendor for proper ARM translation layer
        CPU_VENDOR=$(grep -m1 'vendor_id' /proc/cpuinfo | awk '{print $3}')
        if [[ "$CPU_VENDOR" == "GenuineIntel" ]]; then
            sudo venv/bin/python3 main.py install libhoudini
        elif [[ "$CPU_VENDOR" == "AuthenticAMD" ]]; then
            sudo venv/bin/python3 main.py install libndk
        fi
        cd ..
        sudo rm -rf waydroid_script
    fi
    zeninf "$msg284"
    xdg-open https://docs.waydro.id/faq/google-play-certification
else
    fatal "$msg219"
    exit 1
fi