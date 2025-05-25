#!/bin/bash
# functions

# updater
current_ltver="1.7.7"
ver_upd () {

    local ver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/ver)
    if [[ "$ver" != "$current_ltver" ]]; then
        if whiptail --title "Update available" --yesno "Do you wish to download and install the new version?" 8 78; then
            cd $HOME
            wget https://github.com/psygreg/linuxtoys/releases/latest/download/linuxtoys-${ver}-1.amd64.rpm
            if [ "$ID_LIKE" == "suse" ]; then
                nohup xterm -e "bash -c 'whiptail --title \"Updater\" --msgbox \"Close LinuxToys now to continue.\" 8 78 && sudo zypper in ${HOME}/linuxtoys_${ver}-1_amd64.rpm -y && whiptail --title \"Updater\" --msgbox \"Update complete.\" 8 78 && rm ${HOME}/linuxtoys_${ver}-1_amd64.rpm'" >/dev/null 2>&1 && disown
            else
                nohup xterm -e "bash -c 'whiptail --title \"Updater\" --msgbox \"Close LinuxToys now to continue.\" 8 78 && sudo dnf in ${HOME}/linuxtoys_${ver}-1_amd64.rpm -y && whiptail --title \"Updater\" --msgbox \"Update complete.\" 8 78 && rm ${HOME}/linuxtoys_${ver}-1_amd64.rpm'" >/dev/null 2>&1 && disown  
            fi
            exit 0
        fi
    fi

}

# set up firewall (ufw)
ufw_in () {

    if whiptail --title "Firewall Setup" --yesno "This will install and enable a basic firewall setup for your safety. Proceed?" 8 78; then
        local packages=(ufw gufw)
        for pac in "${packages[@]}"; do
            if rpm -qi "$pac" 2>/dev/null 1>&2; then
                continue
            else
                if [ "$ID_LIKE" == "suse" ]; then
                    sudo zypper in "$pac" -y
                else
                    sudo dnf in "$pac" -y
                fi
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
            if rpm -qi "$pac" 2>/dev/null 1>&2; then
                continue
            else
                if [ "$ID_LIKE" == "suse" ]; then
                    sudo zypper in "$pac" -y
                else
                    sudo dnf in "$pac" -y
                fi
            fi
        done
        if command -v flatpak &> /dev/null; then
            flatpak install --or-update -y org.freedesktop.Platform.VulkanLayer.gamescope
        fi
        whiptail --title "Installation complete" --msgbox "You may toggle and adjust settings on Lutris. You can also use gamemode on Steam games by setting 'gamemoderun %command%' in the launch options." 10 78
    fi

}

# install mangohud and goverlay for game monitoring
mango_in () {

    if whiptail --title "Installing Mangohud and GOverlay" --yesno "This allows you to monitor game performance, similarly to RivaTuner on Windows. Proceed?" 8 78; then
        # installing
        local packages=(mangohud goverlay)
        for pac in "${packages[@]}"; do
            if rpm -qi "$pac" 2>/dev/null 1>&2; then
                continue
            else
                if [ "$ID_LIKE" == "suse" ]; then
                    sudo zypper in "$pac" -y
                else
                    sudo dnf in "$pac" -y
                fi
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

# download and install DaVinci Resolve on Fedora-based distros and openSUSE (TODO autoresolverpm)
resolve_in () {

    if whiptail --title "DaVinci Resolve Installer" --yesno "This will download, convert to a deb package and install Resolve (either Free or Studio). Proceed?" 8 78; then
        whiptail --title "DaVinci Resolve Installer" --msgbox "REMINDER: you will need a license key or dongle to use the Studio version, which should be purchased from Blackmagic Design." 8 78
        wget -O autoresolverpm.sh https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolverpm.sh
        chmod +x autoresolverpm.sh
        ./autoresolverpm.sh
        rm autoresolverpm.sh
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

# install ROCm for AMD GPU computing
rocm_in () {

    whiptail --title "ROCm Installer" --msgbox "This will install ROCm in your system, and is ONLY meant for AMD graphics cards, GCN2 or newer." 8 78
    if whiptail --title "ROCm Installer" --yesno "This may not work outside Fedora and its spins. Proceed?" 8 78; then
        local packages=()
        if [ "$ID_LIKE" == "suse" ]; then
            packages=(libamd_comgr2 libhsa-runtime64-1 librccl1 librocalution0 librocblas4 librocfft0 librocm_smi64_1 librocsolver0 librocsparse1 rocm-device-libs rocm-smi rocminfo hipcc libhiprand1 libhiprtc-builtins5 radeontop rocm-opencl ocl-icd clinfo)
        else
            packages=(rocm-comgr rocm-runtime rccl rocalution rocblas rocfft rocm-smi rocsolver rocsparse rocm-device-libs rocminfo rocm-hip hiprand hiprtc radeontop rocm-opencl ocl-icd clinfo)
        fi
        for pac in "${packages[@]}"; do
            if rpm -qi "$pac" 2>/dev/null 1>&2; then
                continue
            else
                if [ "$ID_LIKE" == "suse" ]; then
                    sudo zypper in "$pac" -y
                else
                    sudo dnf in "$pac" -y
                fi
            fi
        done
        sudo usermod -aG render,video $USER
        whiptail --title "ROCm Installer" --msgbox "Installation complete. Reboot to apply changes." 8 78
    fi

}

# Nvidia driver installer - it is a montrosity, but it works, trust me bro
nvidia_in () {

    while :; do

        CHOICE=$(whiptail --title "Nvidia Driver Installation" --menu "Choose your version:" 25 78 16 \
        "0" "Current cards (GeForce 900 series or newer)" \
        "1" "Older cards (GeForce 600 and 700 series)" \
        "2" "Cancel" 3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
            # Exit the script if the user presses Esc
            break
        fi

        case $CHOICE in
        0) if [ "$ID_LIKE" == "suse" ]; then
                local REPO_ALIAS="nvidia"
                case "$VERSION_ID" in
                    *Tumbleweed*)
                        REPO_URL="https://download.nvidia.com/opensuse/tumbleweed"
                        ;;
                    15.*)
                        REPO_URL="https://download.nvidia.com/opensuse/leap/$VERSION_ID"
                        ;;
                    *)
                        whiptail --title "Unsupported openSUSE version" --msgbox "Unsupported openSUSE version: $VERSION_ID" 8 78
                        ;;
                esac
                if zypper lr | grep -q "^${REPO_ALIAS}\s"; then
                    continue
                else
                    sudo zypper ar -f "$REPO_URL" "nvidia"
                fi
                sudo zypper install x11-video-nvidiaG06 nvidia-computeG06 -y
           else
                if ! sudo dnf repolist | grep -q "rpmfusion-free"; then
                    sudo dnf in https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm 
                fi
                if ! sudo dnf repolist | grep -q "rpmfusion-nonfree"; then
                    sudo dnf in https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm -y
                fi
                sudo dnf in akmod-nvidia xorg-x11-drv-nvidia-cuda -y
           fi 
           sudo dracut -f --regenerate-all ;;
        1) if [ "$ID_LIKE" == "suse" ]; then
                local REPO_ALIAS="nvidia"
                case "$VERSION_ID" in
                    *Tumbleweed*)
                        REPO_URL="https://download.nvidia.com/opensuse/tumbleweed"
                        ;;
                    15.*)
                        REPO_URL="https://download.nvidia.com/opensuse/leap/$VERSION_ID"
                        ;;
                    *)
                        whiptail --title "Unsupported openSUSE version" --msgbox "Unsupported openSUSE version: $VERSION_ID" 8 78
                        ;;
                esac
                if zypper lr | grep -q "^${REPO_ALIAS}\s"; then
                    continue
                else
                    sudo zypper ar -f "$REPO_URL" "nvidia"
                fi
                sudo zypper install x11-video-nvidiaG05 nvidia-computeG05 -y
           else
                if ! sudo dnf repolist | grep -q "rpmfusion-free"; then
                    sudo dnf in https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm 
                fi
                if ! sudo dnf repolist | grep -q "rpmfusion-nonfree"; then
                    sudo dnf in https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm -y
                fi
                sudo dnf in xorg-x11-drv-nvidia-470xx akmod-nvidia-470xx xorg-x11-drv-nvidia-470xx-cuda -y
           fi 
           sudo dracut -f --regenerate-all ;;
        2 | q) break ;;
        *) echo "Invalid Option" ;;
        esac
    done

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

# fix SELinux policies for gaming on openSUSE
fix_se_suse () {

    if [ "$ID_LIKE" == "suse" ]; then
        sudo setsebool -P selinuxuser_execmod 1
        whiptail --title "SELinux Fixer" --msgbox "All done. Reboot to take effect." 8 78
    else
        whiptail --title "SELinux Fixer" --msgbox "Invalid Operating System. This should only be executed in openSUSE." 8 78
    fi

}

# CachyOS kernel for Fedora
kernel_compat () {

    sudo dnf copr enable bieszczaders/kernel-cachyos
    sudo dnf install kernel-cachyos kernel-cachyos-devel-matched
    sudo setsebool -P domain_kernel_load_modules on
    sudo dracut -f --regenerate-all
    sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    whiptail --title "CachyOS Kernel Installer" --msgbox "Installation complete. Reboot for changes to take effect." 8 78

}

kernel_performance () {

    sudo dnf copr enable bieszczaders/kernel-cachyos-lto
    sudo dnf install kernel-cachyos-lto kernel-cachyos-lto-devel-matched
    sudo setsebool -P domain_kernel_load_modules on
    sudo dracut -f --regenerate-all
    sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    whiptail --title "CachyOS Kernel Installer" --msgbox "Installation complete. Reboot for changes to take effect." 8 78

}

kernel_menu () {

    while :; do
        CHOICE=$(whiptail --title "LinuxToys" --menu "CachyOS Kernel Installation" 25 78 16 \
    	    "0" "Install GCC kernel (compatibility)" \
            "1" "Install ThinLTO kernel (performance)" \
            "2" "Return" 3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
            # Exit the script if the user presses Esc
            break
        fi

        case $CHOICE in
        0) kernel_compat ;;
        1) kernel_performance ;;
        3 | q) break ;;
        *) echo "Invalid Option" ;;
        esac
    done

}

kernel_in () {

    if [ "$ID_LIKE" == "rhel fedora" ]; then
        kernel_menu
    elif [ "$ID_LIKE" == "fedora" ]; then
        kernel_menu
    else
        whiptail --title "CachyOS Kernel Installer" --msgbox "Your operating system is not compatible." 8 78
    fi

}

# main menu
. /etc/os-release
ver_upd
while :; do

    CHOICE=$(whiptail --title "LinuxToys" --menu "LinuxToys ${current_ltver}" 25 78 16 \
        "0" "Set up a basic Firewall" \
        "1" "Configure a Swapfile" \
        "2" "Set up Lucidglyph - 'ClearType' for Linux" \
        "3" "Apply Shader Booster" \
        "4" "Disable Split Lock Mitigate" \
        "5" "Install Gamemode and Gamescope" \
        "6" "Install Mangohud and GOverlay" \
        "7" "Install LACT Overclock & Fan Control" \
        "8" "Install or update DaVinci Resolve" \
        "9" "Set up GRUB-Btrfs" \
        "10" "Set up Docker + Portainer" \
        "11" "Instal linux-cachyos Kernel" \
        "12" "Install ROCm for AMD GPUs" \
        "13" "Fix SELinux policies for WINE/Proton" \
        "14" "Exit" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        break
    fi

    case $CHOICE in
    0) ufw_in ;;
    1) swapfile_t ;;
    2) lucidglyph_in ;;
    3) booster_in ;;
    4) split_disable ;;
    5) gamescope_in ;;
    6) mango_in ;;
    7) lact_in ;;
    8) resolve_in ;;
    9) grubtrfs_t ;;
    10) docker_t ;;
    11) kernel_in ;;
    12) rocm_in ;;
    13) fix_se_suse ;;
    14 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done
