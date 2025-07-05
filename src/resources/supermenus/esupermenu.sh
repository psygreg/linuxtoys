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

        [ -f "${tag}.tar.gz" ] && rm -f "${tag}.tar.gz"

        wget -O "${tag}.tar.gz" "https://github.com/maximilionus/lucidglyph/archive/refs/tags/${tag}.tar.gz"
        tar -xvzf "${tag}.tar.gz"
        cd lucidglyph-${ver}
        chmod +x lucidglyph.sh
        sudo ./lucidglyph.sh install
        cd ..
        sleep 1
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
                0) if [[ "$ID_LIKE" == *suse* ]]; then
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
                         insta cuda-drivers
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
                1) if [[ "$ID_LIKE" == *suse* ]]; then
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

    if [[ "$ID_LIKE" == *suse* ]]; then
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
        if [[ "$ID_LIKE" == *suse* ]]; then
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
        psave_lib
    fi

}

touchegg_t () {

    local tag=$(curl -s "https://api.github.com/repos/JoseExposito/touchegg/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    if whiptail --title "$msg006" --yesno "$msg200" 12 78; then
        cd $HOME
        if [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "ubuntu" ]; then
            sudo add-apt-repository ppa:touchegg/stable
            sudo apt update
            insta touchegg
        elif [ "$ID" == "debian" ] || [[ "$ID_LIKE" == *debian* ]]; then
            wget https://github.com/JoseExposito/touchegg/archive/refs/tags/touchegg_${tag}_amd64.deb
            sudo dpkg -i touchegg_${tag}_amd64.deb
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ] || [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ] || [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            insta touchegg
            sudo systemctl enable touchegg.service
            sudo systemctl start touchegg
        else
            title="$msg006"
            msg="$msg077"
            _msgbox_
        fi
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
                psycachy_lib
            else
                bash <(curl -s https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/src/cachyos-deb.sh)
            fi
            # clean old kernels
            dpkg --list | grep -v $(uname -r) | grep -E 'linux-image-[0-9]|linux-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
            dpkg --list | grep -v $(uname -r) | grep -E 'custom-kernel-[0-9]|custom-kernel-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
            cachyos_sysd_lib
            local title="$msg006"
            local msg="$msg036"
            _msgbox_
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
            fedora_cachyos_menu_lib
            cachyos_sysd_lib
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            cachyos_arch_lib
            cachyos_sysd_lib
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

# install linux subsystem for windows
lsw_in () {

    {
        echo "$msg209"
        echo "$msg210"
        echo "$msg211"
        echo "$msg212"
        echo "$msg213"
        echo "$msg214"
        echo "$msg215"
        echo "$msg216"
    } > txtbox
    whiptail --textbox txtbox 12 80
    if whiptail --title "LSW" --yesno "$msg217" 12 78; then
        cd $HOME
        bash <(curl -s https://raw.githubusercontent.com/psygreg/lsw/refs/heads/main/src/lsw-in.sh)
        sleep 1
        rm txtbox
    fi

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
        "4" "$msg207" \
        "5" "$msg055" \
        "6" "$msg177" \
        "7" "$msg201" \
        "8" "$msg057" \
        "9" "$msg081" \
        "10" "$msg079" \
        "11" "$msg078" \
        "12" "$msg053" \
        "13" "$msg209" \
        "14" "$msg059" 3>&1 1>&2 2>&3)

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
    4) total_kb=$(grep MemTotal /proc/meminfo | awk '{ print $2 }')
       total_gb=$(( total_kb / 1024 / 1024 ))
       _cram=$(( total_gb ))
       if (( _cram < 16 )); then
          preload_lib
       else
          title="Preload"
          msg="$msg228"
          _msgbox_
       fi
       ;;
    5) grubtrfs_t ;;
    6) psaver ;;
    7) touchegg_t ;;
    8) kernel_in ;;
    9) suse_codecs ;;
    10) fix_se_suse ;;
    11) nvidia_in ;;
    12) chaotic_aur_lib ;;
    13) lsw_in ;;
    14 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done