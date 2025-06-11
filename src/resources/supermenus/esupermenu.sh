#!/bin/bash

# set up firewall (ufw)
ufw_in () {

    if whiptail --title "$msg006" --yesno "$msg007" 8 78; then
        local _packages=(ufw gufw)
        _install_
        if command -v ufw &> /dev/null; then
            sudo ufw default deny incoming
            sudo ufw default allow outgoing
            sudo ufw enable
        fi
        local title="$msg006"
        local msg="$msg008"
        _msgbox_
    fi

}

# configure swapfile
swapfile_t () {

    if whiptail --title "$msg009" --yesno "$msg010" 8 78; then
        local subscript="swapper"
        _invoke_
    fi

}

# 'cleartype'-like settings for Linux
lucidglyph_in () {

    local tag=$(curl -s "https://api.github.com/repos/maximilionus/lucidglyph/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    local ver="${tag#v}"
    if whiptail --title "$msg019" --yesno "$msg020" 8 78; then  
        cd $HOME
        wget https://github.com/maximilionus/lucidglyph/archive/refs/tags/${tag}.tar.gz
        tar -xvzf v0.11.0.tar.gz 
        cd lucidglyph-${ver}
        chmod +x lucidglyph.sh
        sudo ./lucidglyph.sh install
        cd ..
        rm -rf lucidglyph-${ver}
        local title="$msg021"
        local msg="$msg022"
        _msgbox_
    fi

}

# set up grub-btrfs for snapshots on boot menu 
grubtrfs_t () {

    if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
        local subscript="grub-btrfs-installer"
        _invoke_
    else
        local title="$msg030"
        local msg="$msg031"
        _msgbox_
    fi

}

# Nvidia driver installer for Fedora/SUSE/Debian - it is a montrosity, but it works, trust me bro
nvidia_in () {

    local GPU=$(lspci | grep -iE 'vga|3d' | grep -i nvidia)
    if [[ -n "$GPU" ]]; then
        if [[ "$ID_LIKE" =~ (rhel|fedora|suse) ]] || [[ "$ID" =~ (fedora|suse) ]] || [ "$ID" = "debian" ]; then

            while :; do

                CHOICE=$(whiptail --title "$msg006" --menu "$msg067" 25 78 16 \
                "0" "$msg068" \
                "1" "$msg069" \
                "2" "$msg070" 3>&1 1>&2 2>&3)

                exitstatus=$?
                if [ $exitstatus != 0 ]; then
                    # Exit the script if the user presses Esc
                    return
                fi

                case $CHOICE in
                0) if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
                        local REPO_ALIAS="nvidia"
                        case "$VERSION_ID" in
                            *Tumbleweed*)
                                REPO_URL="https://download.nvidia.com/opensuse/tumbleweed"
                                ;;
                            15.*)
                                REPO_URL="https://download.nvidia.com/opensuse/leap/$VERSION_ID"
                                ;;
                            *)
                                local title="Unsupported openSUSE version"
                                local msg="Unsupported version $VERSION_ID"
                                _msgbox_
                                ;;
                        esac
                        if zypper lr | grep -q "^${REPO_ALIAS}\s"; then
                            continue
                        else
                            sudo zypper ar -f "$REPO_URL" "nvidia"
                        fi
                        insta x11-video-nvidiaG06 nvidia-computeG06
                   elif [ "$ID" = "debian" ]; then
                         wget https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb
                         sudo dpkg -i cuda-keyring_1.1-1_all.deb
                         sudo apt update
                         insta cuda-drivers nvidia-open
                   else
                        if ! sudo dnf repolist | grep -q "rpmfusion-free"; then
                            insta https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
                        fi
                        if ! sudo dnf repolist | grep -q "rpmfusion-nonfree"; then
                            insta https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
                        fi
                        insta akmod-nvidia xorg-x11-drv-nvidia-cuda
                   fi 
                   sudo dracut -f --regenerate-all ;;
                1) if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
                        local REPO_ALIAS="nvidia"
                        case "$VERSION_ID" in
                            *Tumbleweed*)
                                REPO_URL="https://download.nvidia.com/opensuse/tumbleweed"
                                ;;
                            15.*)
                                REPO_URL="https://download.nvidia.com/opensuse/leap/$VERSION_ID"
                                ;;
                            *)
                                local title="Unsupported openSUSE version"
                                local msg="Unsupported version $VERSION_ID"
                                _msgbox_
                                ;;
                        esac
                        if zypper lr | grep -q "^${REPO_ALIAS}\s"; then
                            continue
                        else
                            sudo zypper ar -f "$REPO_URL" "nvidia"
                        fi
                        insta x11-video-nvidiaG05 nvidia-computeG05
                   elif [ "$ID" = "debian" ]; then
                        wget https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb
                        sudo dpkg -i cuda-keyring_1.1-1_all.deb
                        sudo apt update
                        insta cuda-drivers-470
                   else
                        if ! sudo dnf repolist | grep -q "rpmfusion-free"; then
                            insta https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
                        fi
                        if ! sudo dnf repolist | grep -q "rpmfusion-nonfree"; then
                            insta https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
                        fi
                        insta xorg-x11-drv-nvidia-470xx akmod-nvidia-470xx xorg-x11-drv-nvidia-470xx-cuda
                   fi 
                   sudo dracut -f --regenerate-all ;;
                2 | q) break ;;
                *) echo "Invalid Option" ;;
                esac

            done
            
        else
            local title="$msg039"
            local msg="$msg077"
            _msgbox_
        fi
    else
        local title="$msg039"
        local msg="$msg071"
        _msgbox_
    fi

}

# fix SELinux policies for gaming on openSUSE 
fix_se_suse () {

    if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
        sudo setsebool -P selinuxuser_execmod 1
        local title="$msg072"
        local msg="$msg022"
        _msgbox_
    else
        local title="$msg072"
        local msg="$msg073"
        _msgbox_
    fi

}

# install proper codec support on openSUSE
suse_codecs () {

    if whiptail --title "$msg006" --yesno "$msg080" 8 78; then
        if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
            insta opi
            sudo opi codecs
            local title="$msg006"
            local msg="$msg018"
            _msgbox_
        else
            local title="$msg030"
            local msg="$msg077"
            _msgbox_
        fi
    fi

}

# install flatpak support
flatpak_in () {

    if whiptail --title "$msg011" --yesno "$msg012" 8 78; then
        flatpak_in_lib
        if command -v flatpak &> /dev/null; then
            whiptail --title "$msg013" --msgbox "$msg015" 8 78
        else
            if [ "$ID" == "ubuntu" ]; then
                insta gnome-software gnome-software-plugin-flatpak gnome-software-plugin-snap
            fi
        fi
        local title="$msg013"
        local msg="$msg014"
        _msgbox_
    fi

}

# linux kernel power saving optimized settings when on battery
psaver () {

    if whiptail --title "$msg006" --yesno "$msg176" 12 78; then
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            sudo add-apt-repository ppa:linrunner/tlp
            sudo apt update
        fi
        insta powertop tlp tlp-rdw smartmontools ethtool
        sudo systemctl enable tlp.service
        sudo systemctl enable NetworkManager-dispatcher.service
        sudo systemctl mask systemd-rfkill.service systemd-rfkill.socket
        cd $HOME
        git clone https://github.com/AdnanHodzic/auto-cpufreq.git
        cd auto-cpufreq && sudo ./auto-cpufreq-installer
        cd ..
        rm -rf auto-cpufreq
        sudo auto-cpufreq --install
        flatpak_in_lib
        flatpak install --or-update -y com.github.d4nj1.tlpui --system
        local title="$msg006"
        local msg="$msg036"
        _msgbox_
    fi

}

# install linux-cachyos optimized kernel
kernel_in () {

    if [ "$ID" == "cachyos" ]; then
        local title="$msg030"
        local msg="$msg077"
        _msgbox_
    else
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            # summon installer
            if whiptail --title "CachyOS Kernel" --yesno "$msg150" 12 78; then
                bash <(curl -s https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/linuxtoys/cachyos-deb.sh) -s
            else
                bash <(curl -s https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/linuxtoys/cachyos-deb.sh)
            fi
            # clean old kernels
            dpkg --list | grep -v $(uname -r) | grep -E 'linux-image-[0-9]|linux-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
            dpkg --list | grep -v $(uname -r) | grep -E 'custom-kernel-[0-9]|custom-kernel-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
            local title="$msg006"
            local msg="$msg036"
            _msgbox_
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
            kernel_menu
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            chaotic_aur_lib
            insta linux-cachyos linux-cachyos-headers
            if command -v dracut >/dev/null 2>&1; then
                sudo dracut -f --regenerate-all
            elif command -v mkinitcpio >/dev/null 2>&1; then
                sudo mkinitcpio -P
            fi
            sudo grub-mkconfig -o /boot/grub/grub.cfg
            local title="$msg006"
            local msg="$msg036"
            _msgbox_
        else
            local title="$msg074"
            local msg="$msg077"
            _msgbox_
        fi
    fi

}

# CachyOS kernel for Fedora
kernel_compat () {

    sudo dnf copr enable bieszczaders/kernel-cachyos
    sudo insta kernel-cachyos kernel-cachyos-devel-matched
    sudo setsebool -P domain_kernel_load_modules on
    sudo dracut -f --regenerate-all
    sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    local title="$msg006"
    local msg="$msg036"
    _msgbox_

}

kernel_performance () {

    sudo dnf copr enable bieszczaders/kernel-cachyos-lto
    sudo insta kernel-cachyos-lto kernel-cachyos-lto-devel-matched
    sudo setsebool -P domain_kernel_load_modules on
    sudo dracut -f --regenerate-all
    sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    local title="$msg006"
    local msg="$msg036"
    _msgbox_

}

kernel_menu () {

    while :; do
        CHOICE=$(whiptail --title "LinuxToys" --menu "$msg074" 25 78 16 \
    	    "0" "$msg075" \
            "1" "$msg076" \
            "2" "$msg070" 3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
            # Exit the script if the user presses Esc
            return
        fi

        case $CHOICE in
        0) kernel_compat ;;
        1) kernel_performance ;;
        3 | q) break ;;
        *) echo "Invalid Option" ;;
        esac
    done

}

# runtime
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
# extras menu
while :; do

    CHOICE=$(whiptail --title "Extras Supermenu" --menu "LinuxToys ${current_ltver}" 25 78 16 \
        "0" "$msg044" \
        "1" "$msg045" \
        "2" "$msg046" \
        "3" "$msg048" \
        "4" "$msg055" \
        "5" "$msg177" \
        "6" "$msg057" \
        "7" "$msg081" \
        "8" "$msg079" \
        "9" "$msg078" \
        "10" "$msg053" \
        "11" "$msg059" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        break
    fi

    case $CHOICE in
    0) ufw_in ;;
    1) swapfile_t ;;
    2) flatpak_in ;;
    3) lucidglyph_in ;;
    4) grubtrfs_t ;;
    5) psaver ;;
    6) kernel_in ;;
    7) suse_codecs ;;
    8) fix_se_suse ;;
    9) nvidia_in ;;
    10) chaotic_aur_lib ;;
    11 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done