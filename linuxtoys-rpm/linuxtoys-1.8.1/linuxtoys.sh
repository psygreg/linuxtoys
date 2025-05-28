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
        curl -fLo $HOME/.local/${langfile}_${current_ltver} https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/lang/${langfile}_${current_ltver}
    fi

}

# updater
current_ltver="1.8.1"
ver_upd () {

    local ver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/ver)
    if [[ "$ver" != "$current_ltver" ]]; then
        if whiptail --title "$msg001" --yesno "$msg002" 8 78; then
            cd $HOME
            wget https://github.com/psygreg/linuxtoys/releases/latest/download/linuxtoys-${ver}-1.amd64.rpm
            if [ "$ID_LIKE" == "suse" ]; then
                nohup xterm -e "bash -c 'whiptail --title \"$msg003\" --msgbox \"$msg004\" 8 78 && sudo zypper in ${HOME}/linuxtoys_${ver}-1.amd64.rpm -y && whiptail --title \"$msg003\" --msgbox \"$msg005\" 8 78 && rm ${HOME}/linuxtoys_${ver}-1.amd64.rpm'" >/dev/null 2>&1 && disown
            else
                nohup xterm -e "bash -c 'whiptail --title \"$msg003\" --msgbox \"$msg004\" 8 78 && sudo dnf in ${HOME}/linuxtoys_${ver}-1.amd64.rpm -y && whiptail --title \"$msg003\" --msgbox \"$msg005\" 8 78 && rm ${HOME}/linuxtoys_${ver}-1.amd64.rpm'" >/dev/null 2>&1 && disown  
            fi
            exit 0
        fi
    fi

}

# set up firewall (ufw)
ufw_in () {

    if whiptail --title "$msg006" --yesno "$msg007" 8 78; then
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

# install proper codecs on openSUSE
suse_codecs () {

    if whiptail --title "$msg006" --yesno "$msg080" 8 78; then
        if [ "$ID_LIKE" == "suse" ]; then
            sudo zypper in opi -y
            sudo opi codecs
            whiptail --title "$msg006" --msgbox "$msg018" 8 78
        else
            whiptail --title "$msg006" --msgbox "$msg077" 8 78
        fi
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

# download and install DaVinci Resolve on Fedora-based distros and openSUSE (TODO autoresolverpm)
resolve_in () {

    if whiptail --title "$msg006" --yesno "$msg033" 8 78; then
        whiptail --title "$msg006" --msgbox "$msg034" 8 78
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

    local GPU=$(lspci | grep -i 'radeon .*')
    if [[ $GPU == *' radeon '* ]]; then
        if whiptail --title "$msg006" --yesno "$msg037" 8 78; then
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
            whiptail --title "$msg006" --msgbox "$msg036" 8 78
        fi
    else
        whiptail --title "$msg039" --msgbox "$msg040" 8 78
    fi

}

# Nvidia driver installer - it is a montrosity, but it works, trust me bro
nvidia_in () {

    local GPU=$(lspci | grep -i '.* vga .* nvidia .*')
    if [[ $GPU == *' nvidia '* ]]; then
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
        whiptail --title "$msg039" --msgbox "$msg071" 8 78
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

# fix SELinux policies for gaming on openSUSE
fix_se_suse () {

    if [ "$ID_LIKE" == "suse" ]; then
        sudo setsebool -P selinuxuser_execmod 1
        whiptail --title "$msg072" --msgbox "$msg022" 8 78
    else
        whiptail --title "$msg072" --msgbox "$msg073" 8 78
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

kernel_in () {

    if [ "$ID_LIKE" == "rhel fedora" ]; then
        kernel_menu
    elif [ "$ID_LIKE" == "fedora" ]; then
        kernel_menu
    else
        whiptail --title "$msg074" --msgbox "$msg077" 8 78
    fi

}

# logger
logfile="$HOME/.local/linuxtoys-log.txt"
exec 2> >(tee "$logfile" >&2)

# language and upd checks
det_langfile
source $HOME/.local/$langfile
. /etc/os-release
ver_upd

# main menu
while :; do

    CHOICE=$(whiptail --title "LinuxToys" --menu "LinuxToys ${current_ltver}" 25 78 16 \
        "0" "$msg044" \
        "1" "$msg045" \
        "2" "$msg048" \
        "3" "$msg049" \
        "4" "$msg081" \
        "5" "$msg041" \
        "6" "$msg050" \
        "7" "$msg051" \
        "8" "$msg052" \
        "9" "$msg054" \
        "10" "$msg055" \
        "11" "$msg056" \
        "12" "$msg057" \
        "13" "$msg078" \
        "14" "$msg058" \
        "15" "$msg079" \
        "16" "$msg059" 3>&1 1>&2 2>&3)

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
    4) suse_codecs ;;
    5) split_disable ;;
    6) gamescope_in ;;
    7) mango_in ;;
    8) lact_in ;;
    9) resolve_in ;;
    10) grubtrfs_t ;;
    11) docker_t ;;
    12) kernel_in ;;
    13) nvidia_in ;;
    14) rocm_in ;;
    15) fix_se_suse ;;
    16 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done
