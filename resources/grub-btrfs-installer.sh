#!/bin/bash
# functions

# check dependencies
dep_check () {

    local dependencies=()
    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
        dependencies=(newt btrfs-progs grub2 bash gawk inotify-tools)
    elif [ "$ID" == "arch" ] || [[ "$ID_LIKE" =~ (arch) ]]; then
        dependencies=(libnewt btrfs-progs grub bash gawk inotify-tools)
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        dependencies=(whiptail btrfs-progs grub bash gawk inotify-tools)
    fi
    for dep in "${dependencies[@]}"; do
        if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
            if rpm -qi "$dep" 2>/dev/null 1>&2; then
                continue
            else
                if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
                    sudo zypper in "$dep" -y
                else
                    sudo dnf in "$dep" -y
                fi
            fi
        elif [ "$ID" == "arch" ] || [[ "$ID_LIKE" =~ (arch) ]]; then
            if pacman -Qi "$dep" 2>/dev/null 1>&2; then
                continue
            else
                sudo pacman -S --noconfirm "$dep"
            fi
        elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
            if dpkg -s "$dep" 2>/dev/null 1>&2; then
                continue
            else
                sudo apt install -y "$dep"
            fi
        fi
    done

}

# install grub-btrfs and set up automatic snapshot listing
grubtrfs_in () {

    cd $HOME
    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
        sudo dnf rm snapper -y
        sudo dnf in snapper btrfs-assistant -y
        sudo snapper -c root create-config /
        sudo snapper -c root create --command dnf
    elif [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
        sudo zypper rm snapper -y
        sudo zypper in snapper btrfs-assistant -y
        sudo snapper -c root create-config /
        sudo snapper -c root create --command zypper
    elif [ "$ID" == "arch" ] || [[ "$ID_LIKE" =~ (arch) ]]; then
        sudo pacman -Rsn --noconfirm snapper
        sudo pacman -S --noconfirm snapper
        sudo snapper -c root create-config /
        sudo snapper -c root create --command pacman
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        sudo apt purge -y snapper
        sudo apt install -y snapper btrfs-assistant
        sudo snapper -c root create-config /
        sudo snapper -c root create --command apt
    fi
    sudo systemctl enable snapper-boot.timer
    sudo systemctl enable snapper-cleanup.timer
    sudo systemctl start snapper-cleanup.timer
    git clone https://github.com/Antynea/grub-btrfs.git
    cd grub-btrfs
    sudo make install
    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
        sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    elif [ "$ID" == "arch" ] || [[ "$ID_LIKE" =~ (arch) ]]; then
        sudo grub-mkconfig -o /boot/grub/grub.cfg
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        sudo update-grub
    fi
    sudo systemctl enable grub-btrfsd
    sudo systemctl start grub-btrfsd

}

# runtime
. /etc/os-release
dep_check
if whiptail --title "Grub-Btrfs Installer" --yesno "This will list snapshots in your GRUB. It will only work if your root filesystem is btrfs. Proceed?" 8 78; then
    grubtrfs_in
    whiptail --title "Grub-Btrfs Installer" --msgbox "Installation successful."
    cd ..
    rm -rf grub-btrfs
    exit 0
fi