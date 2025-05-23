#!/bin/bash
# functions

# updater
current_ltver="1.7.5"
ver_upd () {

    local ver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/ver)
    if [[ "$ver" != "$current_ltver" ]]; then
        if whiptail --title "Update available" --yesno "Do you wish to download and install the new version?" 8 78; then
            cd $HOME
            wget https://github.com/psygreg/linuxtoys/releases/latest/download/PKGBUILD
            nohup gnome-terminal -- bash -c "whiptail --title 'Updater' --msgbox 'Close LinuxToys now to continue.' 8 78 && makepkg -si && whiptail --title 'Updater' --msgbox 'Update complete.' 8 78 && rm PKGBUILD" >/dev/null 2>&1 & disown
            exit 0
        fi
    fi

}

# set up firewall (ufw)
ufw_in () {

    if whiptail --title "Firewall Setup" --yesno "This will install and enable a basic firewall setup for your safety. Proceed?" 8 78; then
        local packages=(ufw gufw)
        for pac in "${packages[@]}"; do
            if pacman -Qi "$pac" 2>/dev/null 1>&2; then
                continue
            else
                sudo pacman -S --noconfirm "$pac"
            fi
        done
        if command -v ufw &> /dev/null; then
            sudo ufw default deny incoming
            sudo ufw default allow outgoing
            sudo ufw enable
        fi
        whiptail --title "Firewall Setup" --msgbox "Setup completed. You can change settings with the Firewall Settings app." 8 78
    fi

}

# configure swapfile
swapfile_t () {

    if whiptail --title "Shader Booster" --yesno "This creates a swapfile, that can be used to deal with memory pressure. Proceed?" 8 78; then
        curl -O https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/swapper.sh
        chmod +x swapper.sh
        ./swapper.sh
        rm swapper.sh
    fi
    
}

# enable flatpaks (for Ubuntu and flavours)
flatpak_in () {

    # ask confirmation before proceeding
    if whiptail --title "Enabling Flatpaks" --yesno "This will enable Flatpaks and add the Flathub source to your system. Proceed?" 8 78; then
        # installation
        if pacman -Qi "flatpak" 2>/dev/null 1>&2; then
            sudo pacman -S --noconfirm flatpak
            flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
            flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo --system
            # notify that a reboot is required to enable flatpaks
            whiptail --title "Flatpaks Enabled" --msgbox "Reboot to add it to PATH and show apps in the menu." 8 78
        else
            whiptail --title "Flatpaks Enabled" --msgbox "Flatpaks already enabled in your system." 8 78
        fi
    fi

}

# install gnome-software and plugins
gsoftware_in () {

    # ask confirmation before proceeding
    if whiptail --title "Installing Gnome Software" --yesno "This will install the Software app as a flatpak front-end. Proceed?" 8 78; then
        # installation
        local packages=(gnome-software gnome-software-plugin-flatpak)
        for pac in "${packages[@]}"; do
            if pacman -Qi "$pac" 2>/dev/null 1>&2; then
                continue
            else
                sudo pacman -S --noconfirm "$pac"
            fi
        done
        # confirm completion
        whiptail --title "Gnome Software Installed" --msgbox "Installation successful." 8 78
    fi

}

# TODO enable Chaotic AUR repo
chaotic_in () {

    cd $HOME
    sudo pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com
    sudo pacman-key --lsign-key 3056513887B78AEB
    sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst'
    sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst'
    curl -O https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/linuxtoys-aur/resources/script.sed
    sudo sed -i -f script.sed /etc/pacman.conf
    whiptail --title "Chaotic AUR" --msgbox "Repository enabled successfully." 8 78
    rm script.sed

}

# fetch and patch shader cache using shader-booster
booster_in () {

    if whiptail --title "Shader Booster" --yesno "This will patch your shader cache size, fixing stutters in many games. Proceed?" 8 78; then
        # patching
        wget https://github.com/psygreg/shader-booster/releases/latest/download/patcher.sh
        chmod +x patcher.sh
        ./patcher.sh
        rm patcher.sh
    fi

}

# install mangohud and goverlay for game monitoring
mango_in () {

    if whiptail --title "Installing Mangohud and GOverlay" --yesno "This allows you to monitor game performance, similarly to RivaTuner on Windows. Proceed?" 8 78; then
        # installing
        local packages=(mangohud goverlay)
        for pac in "${packages[@]}"; do
            if pacman -Qi "$pac" 2>/dev/null 1>&2; then 
                continue
            else
                sudo pacman -S --noconfirm "$pac"
            fi
        done
        if command -v flatpak &> /dev/null; then
            flatpak install --or-update org.freedesktop.Platform.VulkanLayer.MangoHud
        fi
        whiptail --title "Mangohud and GOverlay installed" --msgbox "Configure your in-game overlay using GOverlay." 8 78
    fi

}

# set up grub-btrfs for snapshots on boot menu
grubtrfs_t () {

    if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
        cd $HOME
        curl -O https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/grub-btrfs-installer.sh
        chmod +x grub-btrfs-installer.sh
        ./grub-btrfs-installer.sh
        rm grub-btrfs-installer.sh
    else
        whiptail --title "Not a BTRFS filesystem" --msgbox "Your root filesystem is not BTRFS." 8 78
    fi

}

# install LACT for overclocking and fan control
lact_in () {

    if whiptail --title "LACT Installation" --yesno "This will install LACT, an overclocking and fan control utility on your system. Proceed?" 8 78; then
        sudo pacman -S --noconfirm lact
    fi

}

# pull and install Resolve with my PKGBUILD
resolve_in () {

    if whiptail --title "DaVinci Resolve Installer" --yesno "This will download, convert to a deb package and install Resolve (either Free or Studio). Proceed?" 8 78; then
        whiptail --title "DaVinci Resolve Installer" --msgbox "REMINDER: you will need a license key or dongle to use the Studio version, which should be purchased from Blackmagic Design." 8 78
        wget -O autoresolvepkg.sh https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolvepkg.sh
        chmod +x autoresolvepkg.sh
        ./autoresolvepkg.sh
        rm autoresolvepkg.sh
    fi

}

# install docker and deploy Portainer web interface
docker_t () {

    cd $HOME
    curl -O https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/docker-installer.sh
    chmod +x docker-installer.sh
    ./docker-installer.sh
    rm docker-installer.sh

}

# install CachyOS kernel from Chaotic
kernel_in () {

    if whiptail --title "CachyOS Custom Kernel Installer" --yesno "This requires having installed the Chaotic-AUR repository first. Proceed?" 8 78; then
        # patching
        sudo pacman -S --noconfirm linux-cachyos
        if command -v dracut >/dev/null 2>&1; then
            sudo dracut -f --regenerate-all
        elif command -v mkinitcpio >/dev/null 2>&1; then
            sudo mkinitcpio -P
        fi
        sudo grub-mkconfig -o /boot/grub/grub.cfg
        whiptail --title "CachyOS Custom Kernel Installer" --msgbox "Installation complete. Reboot for changes to take effect." 8 78
    fi

}

# install ROCm for AMD GPU computing
rocm_in () { 

    whiptail --title "ROCm Installer" --msgbox "This will install ROCm in your system, and is ONLY meant for AMD graphics cards, RDNA 2 or newer." 8 78
    if whiptail --title "ROCm Installer" --yesno "This may not work outside Ubuntu and its flavours. Proceed?" 8 78; then
        local packages=(amd-comgr hsa-rocr rccl rocalution rocblas rocfft rocm-smi-lib rocsolver rocsparse rocm-device-libs rocm-smi rocminfo hipcc hiprand hiprtc radeontop rocm-opencl-runtime ocl-icd clinfo)
        for pac in "${packages[@]}"; do
            if pacman -Qi "$pac" 2>/dev/null 1>&2; then 
                continue
            else
                sudo pacman -S --noconfirm "$pac"
            fi
        done
        sudo usermod -aG render,video $USER
        whiptail --title "ROCm Installer" --msgbox "Installation complete. Reboot to apply changes." 8 78
    fi

}

# disable split lock mitigate for extra performance in some games
split_disable () {

    if whiptail --title "Disable Split Lock Mitigate" --yesno "Mitigating split locks can cause performance losses in games and older applications. This will disable that behaviour, and fix such performance losses. Proceed?" 8 78; then
        if [ ! -f /etc/sysctl.d/99-splitlock.conf ]; then
            echo 'kernel.split_lock_mitigate=0' | sudo tee /etc/sysctl.d/99-splitlock.conf >/dev/null
            whiptail --title "Split Lock Mitigation Disabled" --msgbox "Reboot to apply changes." 8 78
        else
            whiptail --title "Split Lock Mitigation Disabled" --msgbox "Your system has already disabled Split Lock Mitigation." 8 78
        fi
    fi

}

# main menu
ver_upd
while :; do

    CHOICE=$(whiptail --title "LinuxToys" --menu "LinuxToys ${current_ltver}" 25 78 16 \
        "0" "Set up a basic Firewall" \
        "1" "Configure a Swapfile" \
        "2" "Set up Flathub" \
        "3" "Set up Gnome Software" \
        "4" "Apply Shader Booster" \
        "5" "Disable Split Lock Mitigate" \
        "6" "Install Mangohud and GOverlay" \
        "7" "Install LACT Overclock & Fan Control" \
        "8" "Add Chaotic-AUR repository" \
        "9" "Install or update DaVinci Resolve" \
        "10" "Set up GRUB-Btrfs" \
        "11" "Set up Docker + Portainer CE" \
        "12" "Install linux-cachyos Kernel" \
        "13" "Install ROCm for AMD GPUs" \
        "14" "Exit" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        break
    fi

    case $CHOICE in
    0) ufw_in ;;
    1) swapfile_t ;;
    2) flatpak_in ;;
    3) gsoftware_in ;;
    4) booster_in ;;
    5) split_disable ;;
    6) mango_in ;;
    7) lact_in ;;
    8) chaotic_in ;;
    9) resolve_in ;;
    10) grubtrfs_t ;;
    11) docker_t ;;
    12) kernel_in ;;
    13) rocm_in ;;
    14 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done
