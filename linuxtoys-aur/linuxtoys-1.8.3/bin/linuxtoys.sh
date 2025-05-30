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
    if [ -f "$HOME/.local/${langfile}_${current_ltver}" ]; then
        return
    else
        rm -f "$HOME/.local/.ltlang-"* 2>/dev/null
        curl -fLo $HOME/.local/${langfile}_${current_ltver} https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/lang/${langfile}_${current_ltver}
    fi

}

# updater
current_ltver="1.8.3"
ver_upd () {

    local ver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/ver)
    if [[ "$ver" != "$current_ltver" ]]; then
        if whiptail --title "$msg001" --yesno "$msg002" 8 78; then
            cd $HOME
            wget https://github.com/psygreg/linuxtoys/releases/latest/download/PKGBUILD
            wget https://github.com/psygreg/linuxtoys/releases/latest/download/linuxtoys.install
            nohup xterm -e "bash -c 'whiptail --title \"$msg003\" --msgbox \"$msg004\" 8 78 && makepkg -si && whiptail --title \"$msg003\" --msgbox \"$msg005\" 8 78 && rm PKGBUILD && rm linuxtoys.install'" >/dev/null 2>&1 && disown
            exit 0
        fi
    fi

}

# set up firewall (ufw)
ufw_in () {

    if whiptail --title "$msg006" --yesno "$msg007" 8 78; then
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
        if pacman -Qi "flatpak" 2>/dev/null 1>&2; then
            sudo pacman -S --noconfirm flatpak
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
    if whiptail --title "$msg016" --yesno "$msg017" 8 78; then
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
        whiptail --title "$msg021" --msgbox "$msg022" 10 78
    fi

}

# enable Chaotic AUR repo
chaotic_in () {

    cd $HOME
    sudo pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com
    sudo pacman-key --lsign-key 3056513887B78AEB
    sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst'
    sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst'
    curl -O https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/linuxtoys-aur/resources/script.sed
    sudo sed -i -f script.sed /etc/pacman.conf
    sudo pacman -Sy
    whiptail --title "$msg023" --msgbox "$msg024" 8 78
    rm script.sed

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
            if pacman -Qi "$pac" 2>/dev/null 1>&2; then
                continue
            else
                sudo pacman -S --noconfirm "$pac"
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
            if pacman -Qi "$pac" 2>/dev/null 1>&2; then 
                continue
            else
                sudo pacman -S --noconfirm "$pac"
            fi
        done
        if command -v flatpak &> /dev/null; then
            flatpak install --or-update org.freedesktop.Platform.VulkanLayer.MangoHud
        fi
        whiptail --title "$msg006" --msgbox "$msg029" 8 78
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

# install pipewire audio plugin for OBS Studio
obs_pipe () {

    if pacman -Qi "pipewire" 2>/dev/null 1>&2; then
        if whiptail --title "$msg006" --yesno "$msg082" 8 78; then
            cd $HOME
            curl -O https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/pipewire-obs.sh
            chmod +x pipewire-obs.sh
            ./pipewire-obs.sh
            rm pipewire-obs.sh
        fi
    else
        whiptail --title "$msg030" --msgbox "$msg083" 8 78
    fi

}

# install LACT for overclocking and fan control
lact_in () {

    if whiptail --title "$msg006" --yesno "$msg032" 8 78; then
        sudo pacman -S --noconfirm lact
    fi

}

# pull and install Resolve with my PKGBUILD
resolve_in () {

    if whiptail --title "$msg006" --yesno "$msg033" 8 78; then
        whiptail --title "$msg006" --msgbox "$msg034" 12 78
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

    if whiptail --title "$msg006" --yesno "$msg035" 8 78; then
        # patching
        sudo pacman -S --noconfirm linux-cachyos linux-cachyos-headers
        if command -v dracut >/dev/null 2>&1; then
            sudo dracut -f --regenerate-all
        elif command -v mkinitcpio >/dev/null 2>&1; then
            sudo mkinitcpio -P
        fi
        sudo grub-mkconfig -o /boot/grub/grub.cfg
        whiptail --title "$msg006" --msgbox "$msg036" 8 78
    fi

}

# install ROCm for AMD GPU computing
rocm_in () { 

    local GPU=$(lspci | grep -i 'radeon .*')
    if [[ -n "$GPU" ]]; then
        if whiptail --title "$msg006" --yesno "$msg037" 8 78; then
            local packages=(amd-comgr hsa-rocr rccl rocalution rocblas rocfft rocm-smi-lib rocsolver rocsparse rocm-device-libs rocm-smi rocminfo hipcc hiprand hiprtc radeontop rocm-opencl-runtime ocl-icd clinfo)
            for pac in "${packages[@]}"; do
                if pacman -Qi "$pac" 2>/dev/null 1>&2; then 
                    continue
                else
                    sudo pacman -S --noconfirm "$pac"
                fi
            done
            sudo usermod -aG render,video $USER
            whiptail --title "$msg006" --msgbox "$msg036" 8 78
        fi
    else
        whiptail --title "$msg039" --msgbox "$msg040" 8 78
    fi

}

# disable split lock mitigate for extra performance in some games
split_disable () {

    if whiptail --title "$msg041" --yesno "$msg042" 12 78; then
        if [ ! -f /etc/sysctl.d/99-splitlock.conf ]; then
            echo 'kernel.split_lock_mitigate=0' | sudo tee /etc/sysctl.d/99-splitlock.conf >/dev/null
            whiptail --title "$msg041" --msgbox "$msg022" 8 78
        else
            whiptail --title "$msg041" --msgbox "$msg043" 8 78
        fi
    fi

}

# logger
logfile="$HOME/.local/linuxtoys-log.txt"
exec 2> >(tee "$logfile" >&2)

# language and upd checks
det_langfile
source $HOME/.local/${langfile}_${current_ltver}
ver_upd

# main menu
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
        "10" "$msg053" \
        "11" "$msg054" \
        "12" "$msg055" \
        "13" "$msg056" \
        "14" "$msg057" \
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
    10) chaotic_in ;;
    11) resolve_in ;;
    12) grubtrfs_t ;;
    13) docker_t ;;
    14) kernel_in ;;
    15) rocm_in ;;
    16 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done
