#!/bin/bash
# functions

# updater
current_ltver="1.7.6"
ver_upd () {

    local ver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/ver)
    if [[ "$ver" != "$current_ltver" ]]; then
        if whiptail --title "Update available" --yesno "Do you wish to download and install the new version?" 8 78; then
            cd $HOME
            wget https://github.com/psygreg/linuxtoys/releases/latest/download/linuxtoys_${ver}-1_amd64.deb
            nohup gnome-terminal -- bash -c "whiptail --title 'Updater' --msgbox 'Close LinuxToys now to continue.' 8 78 && sudo dpkg -i linuxtoys_${ver}-1_amd64.deb && whiptail --title 'Updater' --msgbox 'Update complete.' 8 78 && rm linuxtoys_${ver}-1_amd64.deb" >/dev/null 2>&1 & disown
            exit 0
        fi
    fi

}

# set up firewall (ufw)
ufw_in () {

    if whiptail --title "Firewall Setup" --yesno "This will install and enable a basic firewall setup for your safety. Proceed?" 8 78; then
        local packages=(ufw gufw)
        for pac in "${packages[@]}"; do
            if dpkg -s "$pac" 2>/dev/null 1>&2; then
                continue
            else
                sudo apt install -y "$pac"
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
        if dpkg -s "flatpak" 2>/dev/null 1>&2; then
            sudo apt install -y flatpak
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
    if whiptail --title "Installing Gnome Software" --yesno "This will install the Software app (and necessary plugins) as apt and flatpak front-end. Proceed?" 8 78; then
        # installation
        local packages=(gnome-software gnome-software-plugin-flatpak)
        for pac in "${packages[@]}"; do
            if dpkg -s "$pac" 2>/dev/null 1>&2; then
                continue
            else
                sudo apt install -y "$pac"
            fi
        done
        if command -v snap &> /dev/null; then
            if dpkg -s "gnome-software-plugin-snap" 2>/dev/null 1>&2; then
                return
            else
                sudo apt install -y gnome-software-plugin-snap
            fi
        fi
        # confirm completion
        whiptail --title "Gnome Software Installed" --msgbox "Installation successful." 8 78
    fi

}


# 'cleartype'-like settings for Linux
lucidglyph_in () {

    local lgver="0.11.0"
    if whiptail --title "LucidGlyph Setup" --yesno "This will set up improved font aliasing configuration, similar to Windows' ClearType. Proceed?" 8 78; then  
        cd $HOME
        wget https://github.com/maximilionus/lucidglyph/archive/refs/tags/v${lgver}.tar.gz
        tar -xvzf v0.11.0.tar.gz 
        cd lucidglyph-${lgver}
        chmod +x lucidglyph.sh
        sudo ./lucidglyph.sh install
        cd ..
        rm -rf lucidglyph-${lgver}
        whiptail --title "Setup Complete" --msgbox "Reboot to take effect." 10 78
    fi

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

# download and properly install gamemode and gamescope
gamescope_in () {

    if whiptail --title "Installer" --yesno "This will install gamemode and gamescope. Gamemode triggers a series of CPU usage optimizations for games, while Gamescope effectively does what Lossless Scaling can do on Windows. Proceed?" 12 78; then
        local packages=(gamemode gamescope)
        for pac in "${packages[@]}"; do
            if dpkg -s "$pac" 2>/dev/null 1>&2; then
                continue
            else
                sudo apt install -y "$pac"
            fi
        done
        if command -v flatpak &> /dev/null; then
            flatpak install --or-update -y org.freedesktop.Platform.VulkanLayer.gamescope
        fi
    fi

}

# install mangohud and goverlay for game monitoring
mango_in () {

    if whiptail --title "Installing Mangohud and GOverlay" --yesno "This allows you to monitor game performance, similarly to RivaTuner on Windows. Proceed?" 8 78; then
        # installing
        local packages=(mangohud goverlay)
        for pac in "${packages[@]}"; do
            if dpkg -s "$pac" 2>/dev/null 1>&2; then
                continue
            else
                sudo apt install -y "$pac"
            fi
        done
        if command -v flatpak &> /dev/null; then
            flatpak install --or-update org.freedesktop.Platform.VulkanLayer.MangoHud
        fi
        whiptail --title "Mangohud and GOverlay installed" --msgbox "Configure your in-game overlay using GOverlay." 8 78
    fi

}

# install LACT for overclocking and fan control
lact_in () {

    if whiptail --title "LACT Installation" --yesno "This will install LACT, an overclocking and fan control utility on your system. Proceed?" 8 78; then
        if command -v flatpak &> /dev/null; then
            flatpak install -y io.github.ilya_zlobintsev.LACT
        else
            whiptail --title "LACT Installation" --msgbox "This requires flatpak in your system. You may install it from the previous menu." 8 78
        fi
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

# download and properly install FireAlpaca as a .deb package
firealpaca_in () {

    if whiptail --title "FireAlpaca Installer" --yesno "This will install FireAlpaca from a deb package created from the original AppImage. Proceed?" 8 78; then
        # patching
        wget https://github.com/psygreg/firealpaca-deb/releases/latest/download/installer.sh
        chmod +x installer.sh
        ./installer.sh
        rm installer.sh
    fi

}

# download and install DaVinci Resolve as a deb package
resolve_in () {

    if whiptail --title "DaVinci Resolve Installer" --yesno "This will download, convert to a deb package and install Resolve (either Free or Studio). Proceed?" 8 78; then
        whiptail --title "DaVinci Resolve Installer" --msgbox "REMINDER: you will need a license key or dongle to use the Studio version, which should be purchased from Blackmagic Design." 8 78
        wget -O autoresolvedeb.sh https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolvedeb.sh
        chmod +x autoresolvedeb.sh
        ./autoresolvedeb.sh
        rm autoresolvedeb.sh
    fi

}

# install linux-cachyos optimized kernel
kernel_in () {

    if whiptail --title "CachyOS Custom Kernel Installer" --yesno "This will open the menu to set up a custom kernel from linux-cachyos patches. Proceed?" 8 78; then
        # patching
        wget -O cachyos-deb.sh https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/linuxtoys/cachyos-deb.sh
        chmod +x cachyos-deb.sh
        ./cachyos-deb.sh
        rm cachyos-deb.sh
    fi

}

# install ROCm for AMD GPU computing
rocm_in () {

    whiptail --title "ROCm Installer" --msgbox "This will install ROCm in your system, and is ONLY meant for AMD graphics cards, RDNA 2 or newer." 8 78
    if whiptail --title "ROCm Installer" --yesno "This may not work outside Ubuntu and its flavours. Proceed?" 8 78; then
        local packages=(libamd-comgr2 libhsa-runtime64-1 librccl1 librocalution0 librocblas0 librocfft0 librocm-smi64-1 librocsolver0 librocsparse0 rocm-device-libs-17 rocm-smi rocminfo hipcc libhiprand1 libhiprtc-builtins5 radeontop rocm-opencl-icd ocl-icd-libopencl1 clinfo)
        for pac in "${packages[@]}"; do
            if dpkg -s "$pac" 2>/dev/null 1>&2; then
                continue
            else
                sudo apt install -y "$pac"
            fi
        done
        sudo usermod -aG render,video $USER
        whiptail --title "ROCm Installer" --msgbox "Installation complete. Reboot to apply changes." 8 78
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

# install PPA for automatic updates on Ubuntu
ppa_in () {
	
	if whiptail --title "LinuxToys PPA" --yesno "This will not work outside latest Ubuntu. Proceed?" 8 78; then
        sudo add-apt-repository ppa:psygreg/linuxtoys
		sudo apt update
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
. /etc/os-release
ver_upd
while :; do

    CHOICE=$(whiptail --title "LinuxToys" --menu "LinuxToys ${current_ltver}" 25 78 16 \
        "0" "Set up a basic Firewall" \
        "1" "Configure a Swapfile" \
        "2" "Set up Flathub" \
        "3" "Set up Gnome Software" \
        "4" "Set up Lucidglyph - 'ClearType' for Linux" \
        "5" "Apply Shader Booster" \
        "6" "Disable Split Lock Mitigate" \
        "7" "Install Gamemode and Gamescope" \
        "8" "Install Mangohud and GOverlay" \
        "9" "Install LACT Overclock & Fan Control" \
        "10" "Install or update FireAlpaca" \
        "11" "Install or update DaVinci Resolve" \
        "12" "Set up GRUB-Btrfs" \
        "13" "Set up Docker + Portainer CE" \
        "14" "Compile and install/update linux-cachyos Kernel" \
        "15" "Install ROCm for AMD GPUs" \
        "16" "Exit" 3>&1 1>&2 2>&3)

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
    4) lucidglyph_in ;;
    5) booster_in ;;
    6) split_disable ;;
    7) gamescope_in ;;
    8) mango_in ;;
    9) lact_in ;;
    10) firealpaca_in ;;
    11) resolve_in ;;
    12) grubtrfs_t ;;
    13) docker_t ;;
    14) kernel_in ;;
    15) rocm_in ;;
    16 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done
