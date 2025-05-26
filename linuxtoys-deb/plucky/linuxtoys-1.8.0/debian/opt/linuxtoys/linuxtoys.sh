#!/bin/bash
# functions

# determine language
det_langfile () {

    local lang="${LANG:0:2}"
    local available=("pt")
    local ulang=""
    langfile=""

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
    if [ -f "$HOME/.local/$langfile" ]; then
        return
    else
        curl -fLo $HOME/.local/$langfile https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/lang/${langfile}
    fi

}

# updater
current_ltver="1.8.0"
ver_upd () {

    local ver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/ver)
    if [[ "$ver" != "$current_ltver" ]]; then
        if whiptail --title "$msg001" --yesno "$msg002" 8 78; then
            cd $HOME
            wget https://github.com/psygreg/linuxtoys/releases/latest/download/linuxtoys_${ver}-1_amd64.deb
            nohup xterm -e "bash -c 'whiptail --title \"$msg003\" --msgbox \"$msg004\" 8 78 && sudo dpkg -i ${HOME}/linuxtoys_${ver}-1_amd64.deb -y && whiptail --title \"$msg003\" --msgbox \"$msg005\" 8 78 && rm ${HOME}/linuxtoys_${ver}-1_amd64.deb'" >/dev/null 2>&1 && disown
            exit 0
        fi
    fi

}

# set up firewall (ufw)
ufw_in () {

    if whiptail --title "$msg006" --yesno "$msg007" 8 78; then
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
        whiptail --title "$msg006" --msgbox "$msg008" 8 78
    fi

}

# configure swapfile
swapfile_t () {

    if whiptail --title "$msg009" --yesno "$msg010" 8 78; then
        curl -O https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/swapper.sh
        chmod +x swapper.sh
        ./swapper.sh
        rm swapper.sh
    fi
    
}

# enable flatpaks (for Ubuntu and flavours)
flatpak_in () {

    # ask confirmation before proceeding
    if whiptail --title "$msg011" --yesno "$msg012" 8 78; then
        # installation
        if dpkg -s "flatpak" 2>/dev/null 1>&2; then
            sudo apt install -y flatpak
            flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
            flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo --system
            # notify that a reboot is required to enable flatpaks
            whiptail --title "$msg013" --msgbox "$msg014" 8 78
        else
            whiptail --title "$msg013" --msgbox "$msg015" 8 78
        fi
    fi

}

# install gnome-software and plugins
gsoftware_in () {

    # ask confirmation before proceeding
    if whiptail --title "$msg016" --yesno "$msg060" 8 78; then
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
        whiptail --title "$msg016" --msgbox "$msg018" 8 78
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
        whiptail --title "$msg019" --msgbox "$msg022" 10 78
    fi

}

# fetch and patch shader cache using shader-booster
booster_in () {

    if whiptail --title "$msg025" --yesno "$msg026" 8 78; then
        # patching
        wget https://github.com/psygreg/shader-booster/releases/latest/download/patcher.sh
        chmod +x patcher.sh
        ./patcher.sh
        rm patcher.sh
    fi

}

# download and properly install gamemode and gamescope
gamescope_in () {

    if whiptail --title "$msg006" --yesno "$msg027" 12 78; then
        local packages=(gamemode gamescope)
        for pac in "${packages[@]}"; do
            if dpkg -s "$pac" 2>/dev/null 1>&2; then
                continue
            else
                sudo apt install -y "$pac"
            fi
        done
        if command -v flatpak &> /dev/null; then
            flatpak install --or-update -y org.freedesktop.Platform.VulkanLayer.gamescope/x86_64/23.08
        fi
        whiptail --title "$msg006" --msgbox "$msg066" 12 78
    fi

}

# install mangohud and goverlay for game monitoring
mango_in () {

    if whiptail --title "$msg006" --yesno "$msg028" 8 78; then
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
        whiptail --title "$msg006" --msgbox "$msg029" 8 78
    fi

}

# install LACT for overclocking and fan control
lact_in () {

    if whiptail --title "$msg006" --yesno "$msg032" 8 78; then
        if command -v flatpak &> /dev/null; then
            flatpak install -y io.github.ilya_zlobintsev.LACT
        else
            whiptail --title "$msg006" --msgbox "$msg061" 8 78
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
        whiptail --title "$msg030" --msgbox "$msg031" 8 78
    fi

}

# download and properly install FireAlpaca as a .deb package
firealpaca_in () {

    if whiptail --title "$msg006" --yesno "$msg062" 8 78; then
        # patching
        wget https://github.com/psygreg/firealpaca-deb/releases/latest/download/installer.sh
        chmod +x installer.sh
        ./installer.sh
        rm installer.sh
    fi

}

# download and install DaVinci Resolve as a deb package
resolve_in () {

    if whiptail --title "$msg006" --yesno "$msg033" 8 78; then
        whiptail --title "$msg006" --msgbox "$msg034" 8 78
        wget -O autoresolvedeb.sh https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolvedeb.sh
        chmod +x autoresolvedeb.sh
        ./autoresolvedeb.sh
        rm autoresolvedeb.sh
    fi

}

# install linux-cachyos optimized kernel
kernel_in () {

    if whiptail --title "$msg006" --yesno "$msg063" 8 78; then
        # patching
        wget -O cachyos-deb.sh https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/linuxtoys/cachyos-deb.sh
        chmod +x cachyos-deb.sh
        ./cachyos-deb.sh
        rm cachyos-deb.sh
    fi

}

# install ROCm for AMD GPU computing
rocm_in () {

    local GPU=$(lspci | grep -i 'radeon .*')
    if [[ $GPU == *' radeon '* ]]; then
        whiptail --title "$msg006" --msgbox "$msg037" 8 78
        if whiptail --title "$msg006" --yesno "$msg038" 8 78; then
            local packages=(libamd-comgr2 libhsa-runtime64-1 librccl1 librocalution0 librocblas0 librocfft0 librocm-smi64-1 librocsolver0 librocsparse0 rocm-device-libs-17 rocm-smi rocminfo hipcc libhiprand1 libhiprtc-builtins5 radeontop rocm-opencl-icd ocl-icd-libopencl1 clinfo)
            for pac in "${packages[@]}"; do
                if dpkg -s "$pac" 2>/dev/null 1>&2; then
                    continue
                else
                    sudo apt install -y "$pac"
                fi
            done
            sudo usermod -aG render,video $USER
            whiptail --title "$msg006" --msgbox "$msg036" 8 78
        fi
    else
        whiptail --title "$msg039" --msgbox "$msg040" 8 78
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

# disable split lock mitigate for extra performance in some games
split_disable () {

    if whiptail --title "$msg041" --yesno "$msg042" 12 78; then
        if [ ! -f /etc/sysctl.d/99-splitlock.conf ]; then
            echo 'kernel.split_lock_mitigate=0' | sudo tee /etc/sysctl.d/99-splitlock.conf >/dev/null
            whiptail --title "$msg041" --msgbox "$msg036" 8 78
        else
            whiptail --title "$msg041" --msgbox "$msg043" 8 78
        fi
    fi

}

# main menu
det_langfile
source $HOME/.local/$langfile
. /etc/os-release
ver_upd
while :; do

    CHOICE=$(whiptail --title "LinuxToys" --menu "LinuxToys ${current_ltver}" 25 78 16 \
        "0" "$msg044" \
        "1" "$msg045" \
        "2" "$msg046" \
        "3" "$msg047" \
        "4" "$msg048" \
        "5" "$msg049" \
        "6" "$msg041" \
        "7" "$msg050" \
        "8" "$msg051" \
        "9" "$msg052" \
        "10" "$msg064" \
        "11" "$msg054" \
        "12" "$msg055" \
        "13" "$msg056" \
        "14" "$msg065" \
        "15" "$msg058" \
        "16" "$msg059" 3>&1 1>&2 2>&3)

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
