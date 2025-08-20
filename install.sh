#!/bin/bash
echo "================== LINUXTOYS QUICK-INSTALLER ===================="
echo "Do you wish to install or update LinuxToys? (y/n)"
read -r answer
if [[ "${answer,,}" != "y" ]]; then
    echo "===== CANCELLED ====="
    echo "Installation aborted."
    sleep 3
    exit 100
fi
cd $HOME || { echo "============ ERROR ============="; echo "Fatal error: cannot change directory"; exit 2; }
tag=$(curl -s "https://api.github.com/repos/psygreg/linuxtoys/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
if command -v rpm-ostree &>/dev/null; then
    wget "https://github.com/psygreg/linuxtoys/releases/download/${tag}/linuxtoys-${tag}-1.x86_64.rpm"
    if rpm -qi linuxtoys &>/dev/null; then
        sudo rpm-ostree remove linuxtoys
        sudo rpm-ostree install "linuxtoys-${tag}-1.x86_64.rpm"
    else
        sudo rpm-ostree install "linuxtoys-${tag}-1.x86_64.rpm"
    fi
    rm "linuxtoys-${tag}-1.x86_64.rpm"
    echo "================== SUCCESS ===================="
    echo "LinuxToys installed or updated! Reboot to apply."
    sleep 3
    exit 0
else
    . /etc/os-release
    if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
        wget "https://github.com/psygreg/linuxtoys/releases/download/${tag}/linuxtoys_${tag}-1_amd64.deb"
        sudo apt install -y "./linuxtoys_${tag}-1_amd64.deb"
        rm "linuxtoys_${tag}-1_amd64.deb"
    elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
        wget "https://github.com/psygreg/linuxtoys/releases/download/${tag}/linuxtoys-${tag}-1.x86_64.rpm"
        sudo dnf install "./linuxtoys-${tag}-1.x86_64.rpm" -y
        rm "linuxtoys-${tag}-1.x86_64.rpm"
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
        wget "https://github.com/psygreg/linuxtoys/releases/download/${tag}/linuxtoys-${tag}-1-x86_64.pacman"
        sudo pacman -U --noconfirm "./linuxtoys-${tag}-1-x86_64.pacman"
        rm "linuxtoys-${tag}-1-x86_64.pacman"
    else
        echo "========== ERROR ============"
        echo "Unsupported operating system."
        sleep 3
        exit 1
    fi
fi
echo "========== SUCCESS ============"
echo "LinuxToys installed or updated!"
sleep 3
exit 0