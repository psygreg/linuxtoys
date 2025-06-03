#!/bin/bash

# determine language
det_langfile () {

    local lang="${LANG:0:2}"
    local available=("pt")
    local ulang=""

    if [[ " ${available[*]} " == *"$lang"* ]]; then
        ulang="$lang"
    else
        ulang="en"
    fi
    if [ $ulang == "pt" ]; then
        langfile=".ltlang-pt"
    else
        langfile=".ltlang-en"
    fi

}

# set up firewall (ufw)
ufw_in () {

    if whiptail --title "$msg006" --yesno "$msg007" 8 78; then
        local packages=(ufw gufw)
        if [[ "$ID_LIKE" =~ (rhel|fedora|suse) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
            for pac in "${packages[@]}"; do
                if rpm -qi "$pac" 2>/dev/null 1>&2; then
                    continue
                else
                    if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
                        sudo zypper in "$pac" -y
                    else
                        sudo dnf in "$pac" -y
                    fi
                fi
            done
        elif [[ "$ID" =~ (arch|cachyos) ]] || [[ "$ID_LIKE" =~ (arch) ]]; then
            for pac in "${packages[@]}"; do
                if pacman -Qi "$pac" 2>/dev/null 1>&2; then
                    continue
                else
                    sudo pacman -S --noconfirm "$pac"
                fi
            done
        elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
            for pac in "${packages[@]}"; do
                if dpkg -s "$pac" 2>/dev/null 1>&2; then
                    continue
                else
                    sudo apt install -y "$pac"
                fi
            done
        fi
        if command -v ufw &> /dev/null; then
            sudo ufw default deny incoming
            sudo ufw default allow outgoing
            sudo ufw enable
        fi
        whiptail --title "$msg006" --msgbox "$msg008" 8 78
    fi

}

# configure swapfile
swapfile_t () {

    if whiptail --title "$msg009" --yesno "$msg010" 8 78; then
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/swapper.sh
        chmod +x swapper.sh
        ./swapper.sh
        rm swapper.sh
    fi

}

# 'cleartype'-like settings for Linux
lucidglyph_in () {

    local lgver="0.11.0"
    if whiptail --title "$msg019" --yesno "$msg020" 8 78; then  
        cd $HOME
        wget https://github.com/maximilionus/lucidglyph/archive/refs/tags/v${lgver}.tar.gz
        tar -xvzf v0.11.0.tar.gz 
        cd lucidglyph-${lgver}
        chmod +x lucidglyph.sh
        sudo ./lucidglyph.sh install
        cd ..
        rm -rf lucidglyph-${lgver}
        whiptail --title "$msg021" --msgbox "$msg022" 10 78
    fi

}

# set up grub-btrfs for snapshots on boot menu 
grubtrfs_t () {

    if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
        whiptail --title "$msg030" --msgbox "$msg077" 8 78
    else
        if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
            cd $HOME
            wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/grub-btrfs-installer.sh
            chmod +x grub-btrfs-installer.sh
            ./grub-btrfs-installer.sh
            rm grub-btrfs-installer.sh
        else
            whiptail --title "$msg030" --msgbox "$msg031" 8 78
        fi
    fi

}

# Nvidia driver installer for Fedora/SUSE - it is a montrosity, but it works, trust me bro
nvidia_in () {

    local GPU=$(lspci | grep -i '.* vga .* nvidia .*')
    if [[ $GPU == *' nvidia '* ]]; then
        if [[ "$ID_LIKE" =~ (rhel|fedora|suse) ]] || [[ "$ID" =~ (fedora|suse) ]]; then

            while :; do

                CHOICE=$(whiptail --title "$msg006" --menu "$msg067" 25 78 16 \
                "0" "$msg068" \
                "1" "$msg069" \
                "2" "$msg070" 3>&1 1>&2 2>&3)

                exitstatus=$?
                if [ $exitstatus != 0 ]; then
                    # Exit the script if the user presses Esc
                    break
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
                                whiptail --title "Unsupported openSUSE version" --msgbox "Unsupported openSUSE version: $VERSION_ID" 8 78
                                ;;
                        esac
                        if zypper lr | grep -q "^${REPO_ALIAS}\s"; then
                            continue
                        else
                            sudo zypper ar -f "$REPO_URL" "nvidia"
                        fi
                        sudo zypper in x11-video-nvidiaG06 nvidia-computeG06 -y
                   else
                        if ! sudo dnf repolist | grep -q "rpmfusion-free"; then
                            sudo dnf in https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm -y
                        fi
                        if ! sudo dnf repolist | grep -q "rpmfusion-nonfree"; then
                            sudo dnf in https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm -y
                        fi
                        sudo dnf in akmod-nvidia xorg-x11-drv-nvidia-cuda -y
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
                                whiptail --title "Unsupported openSUSE version" --msgbox "Unsupported openSUSE version: $VERSION_ID" 8 78
                                ;;
                        esac
                        if zypper lr | grep -q "^${REPO_ALIAS}\s"; then
                            continue
                        else
                            sudo zypper ar -f "$REPO_URL" "nvidia"
                        fi
                        sudo zypper in x11-video-nvidiaG05 nvidia-computeG05 -y
                   else
                        if ! sudo dnf repolist | grep -q "rpmfusion-free"; then
                            sudo dnf in https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm -y
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
            
        else
            whiptail --title "$msg039" --msgbox "$msg077" 8 78
        fi
    else
        whiptail --title "$msg039" --msgbox "$msg071" 8 78
    fi

}

# fix SELinux policies for gaming on openSUSE 
fix_se_suse () {

    if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
        sudo setsebool -P selinuxuser_execmod 1
        whiptail --title "$msg072" --msgbox "$msg022" 8 78
    else
        whiptail --title "$msg072" --msgbox "$msg073" 8 78
    fi

}

# install proper codec support on openSUSE
suse_codecs () {

    if whiptail --title "$msg006" --yesno "$msg080" 8 78; then
        if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
            sudo zypper in opi -y
            sudo opi codecs
            whiptail --title "$msg006" --msgbox "$msg018" 8 78
        else
            whiptail --title "$msg030" --msgbox "$msg077" 8 78
        fi
    fi

}

# install flatpak support
flatpak_in () {

    # ask confirmation before proceeding
    if whiptail --title "$msg011" --yesno "$msg012" 8 78; then
        # installation
        if command -v flatpak &> /dev/null; then
            if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
                sudo apt install -y flatpak
            elif [[ "$ID" =~ (arch|cachyos) ]] || [[ "$ID_LIKE" =~ (arch) ]]; then
                sudo pacman -S --noconfirm flatpak
            fi
            flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
            flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo --system
            # notify that a reboot is required to enable flatpaks
            whiptail --title "$msg013" --msgbox "$msg014" 8 78
        else
            whiptail --title "$msg013" --msgbox "$msg015" 8 78
        fi
    fi

}

# enable Chaotic AUR repo for Arch
chaotic_in () {

    if [[ "$ID" =~ (arch|cachyos) ]] || [[ "$ID_LIKE" =~ (arch) ]]; then
        cd $HOME
        sudo pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com
        sudo pacman-key --lsign-key 3056513887B78AEB
        sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst'
        sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst'
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/linuxtoys-aur/resources/script.sed
        sudo sed -i -f script.sed /etc/pacman.conf
        sudo pacman -Sy
        whiptail --title "$msg023" --msgbox "$msg024" 8 78
        rm script.sed
    else
        whiptail --title "$msg030" --msgbox "$msg077" 8 78
    fi

}

# install linux-cachyos optimized kernel
kernel_in () {

    if [ "$ID" == "cachyos" ]; then
        whiptail --title "$msg030" --msgbox "$msg077" 8 78
    else
        if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
            # summon installer
            wget -O cachyos-deb.sh https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/linuxtoys/cachyos-deb.sh
            chmod +x cachyos-deb.sh
            ./cachyos-deb.sh
            rm cachyos-deb.sh
            # clean old kernels
            dpkg --list | grep -v $(uname -r) | grep -E 'linux-image-[0-9]|linux-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
            dpkg --list | grep -v $(uname -r) | grep -E 'custom-kernel-[0-9]|custom-kernel-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
            whiptail --title "$msg006" --msgbox "$msg036" 8 78
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
            kernel_menu
        elif [ "$ID" == "arch" ] || [[ "$ID_LIKE" =~ (arch) ]]; then
            chaotic_in
            sudo pacman -S --noconfirm linux-cachyos linux-cachyos-headers
            if command -v dracut >/dev/null 2>&1; then
                sudo dracut -f --regenerate-all
            elif command -v mkinitcpio >/dev/null 2>&1; then
                sudo mkinitcpio -P
            fi
            sudo grub-mkconfig -o /boot/grub/grub.cfg
            whiptail --title "$msg006" --msgbox "$msg036" 8 78
        else
            whiptail --title "$msg074" --msgbox "$msg077" 8 78
        fi
    fi

}

# CachyOS kernel for Fedora
kernel_compat () {

    sudo dnf copr enable bieszczaders/kernel-cachyos
    sudo dnf install kernel-cachyos kernel-cachyos-devel-matched
    sudo setsebool -P domain_kernel_load_modules on
    sudo dracut -f --regenerate-all
    sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    whiptail --title "$msg006" --msgbox "$msg036" 8 78

}

kernel_performance () {

    sudo dnf copr enable bieszczaders/kernel-cachyos-lto
    sudo dnf install kernel-cachyos-lto kernel-cachyos-lto-devel-matched
    sudo setsebool -P domain_kernel_load_modules on
    sudo dracut -f --regenerate-all
    sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    whiptail --title "$msg006" --msgbox "$msg036" 8 78

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

# runtime
det_langfile
current_ltver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/ver)
source $HOME/.local/${langfile}_${current_ltver}
. /etc/os-release
# extras menu
while :; do

    CHOICE=$(whiptail --title "Extras Supermenu" --menu "LinuxToys ${current_ltver}" 25 78 16 \
        "0" "$msg044" \
        "1" "$msg045" \
        "2" "$msg046" \
        "3" "$msg048" \
        "4" "$msg055" \
        "5" "$msg057" \
        "6" "$msg081" \
        "7" "$msg079" \
        "8" "$msg078" \
        "9" "$msg053" \
        "10" "$msg059" 3>&1 1>&2 2>&3)

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
    5) kernel_in ;;
    6) suse_codecs ;;
    7) fix_se_suse ;;
    8) nvidia_in ;;
    9) chaotic_in ;;
    10 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done