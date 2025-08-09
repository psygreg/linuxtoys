#!/bin/bash

# set up firewall (ufw)
ufw_in () {

    if zenity --question --text "$msg007" --width 360 --height 300; then
        local _packages=(ufw gufw)
        _install_
        if command -v ufw &> /dev/null; then
            sudo ufw default deny incoming
            sudo ufw default allow outgoing
            sudo ufw enable
        fi
        zeninf "$msg008"
    fi

}

# configure swapfile
swapfile_t () {

    if zenity --question --text "$msg010" --width 360 --height 300; then
        local subscript="swapper"
        _invoke_
    fi

}

# 'cleartype'-like settings for Linux
lucidglyph_in () {

    local tag=$(curl -s "https://api.github.com/repos/maximilionus/lucidglyph/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    local ver="${tag#v}"
    if zenity --question --text "$msg020" --width 360 --height 300; then 
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
        zeninf "$msg022"
    fi

}

# set up grub-btrfs for snapshots on boot menu
grubtrfs_t () {

    if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
        local subscript="grub-btrfs-installer"
        _invoke_
    else
        nonfatal "$msg031"
    fi

}

# Nvidia driver installer for Fedora/SUSE/Debian - it is a montrosity, but it works, trust me bro
nvidia_in () {

    local GPU=$(lspci | grep -iE 'vga|3d' | grep -i nvidia)
    if [[ -n "$GPU" ]]; then
        if [[ "$ID_LIKE" =~ (rhel|fedora|suse) ]] || [[ "$ID" =~ (fedora|suse) ]] || [ "$ID" = "debian" ]; then

            while true; do

                CHOICE=$(zenity --list --title "Nvidia Drivers" \
                --column="$msg067" \
                "$msg068" \
                "$msg069" \
                "$msg070" \
                --height=330 --width=360)

                if [ $? -ne 0 ]; then
                    break
                fi

                case $CHOICE in
                "$msg068") if [[ "$ID_LIKE" == *suse* ]]; then
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
                         sudo apt-get update
                         sudo apt-get install cuda-drivers
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
                "$msg069") if [[ "$ID_LIKE" == *suse* ]]; then
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
                "$msg070") break ;;
                *) echo "Invalid Option" ;;
                esac

            done

        else
            nonfatal "$msg077"
        fi
    else
        nonfatal "$msg071"
    fi

}

# fix SELinux policies for gaming on openSUSE
fix_se_suse () {

    if [[ "$ID_LIKE" == *suse* ]]; then
        sudo setsebool -P selinuxuser_execmod 1
        zeninf "$msg022"
    else
        nonfatal "$msg073"
    fi

}

# install proper codec support on openSUSE
suse_codecs () {

    if zenity --question --text "$msg080" --width 360 --height 300; then
        if [[ "$ID_LIKE" == *suse* ]]; then
            insta opi
            sudo opi codecs
            zeninf "$msg018"
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
            if rpm -qi rpmfusion-free-release || rpm -qi rpmfusion-nonfree-release; then
                local _packages=(libavcodec-freeworld)
            else
                wget https://download1.rpmfusion.org/free/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
                wget https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
                insta rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
                rm rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
                local _packages=(libavcodec-freeworld)
            fi
            _install_
        else
            zeninf "$msg077"
        fi
    fi

}

# install flatpak support
flatpak_in () {

    if [ ! -f /.autopatch.state ]; then
        if zenity --question --text "$msg012" --width 360 --height 300; then
            flatpak_in_lib
            if command -v flatpak &> /dev/null; then
                zeninf "$msg015"
                if [ "$ID" == "ubuntu" ]; then
                    insta gnome-software gnome-software-plugin-flatpak gnome-software-plugin-snap
                fi
            fi
            zeninf "$msg014"
        fi
    else
        nonfatal "$msg234"
    fi

}

# linux kernel power saving optimized settings when on battery
psaver () {

    if [ ! -f /.autopatch.state ]; then
        if zenity --question --text "$msg176" --width 360 --height 300; then
            psave_lib
        fi
    else
        nonfatal "$msg234"
    fi

}

touchegg_t () {

    local tag=$(curl -s "https://api.github.com/repos/JoseExposito/touchegg/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    if zenity --question --text "$msg200" --width 360 --height 300; then
        if [ "$XDG_SESSION_TYPE" != "wayland" ]; then
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
                nonfatal "$msg077"
            fi
        else
            nonfatal "$msg077"
        fi
    fi

}

# install linux-cachyos optimized kernel
kernel_in () {

    if [ "$ID" == "cachyos" ]; then
        nonfatal "$msg077"
    else
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            # summon installer
            if zenity --question --text "$msg150" --width 360 --height 300; then
                psycachy_lib
            fi
            zeninf "$msg036"
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
            fedora_cachyos_menu_lib
            cachyos_sysd_lib
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            cachyos_arch_lib
            cachyos_sysd_lib
            zeninf "$msg036"
        else
            nonfatal "$msg077"
        fi
    fi

}

# inet wireless daemon installer
iwd_summon () {

    if zenity --question --text "$msg244" --width 360 --height 300; then
        zenwrn "$msg243"
        local subscript="iwdwifi" && _invoke_
    fi

}

# install linux subsystem for windows
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

    zenity --text-info \
       --title="LSW" \
       --filename=txtbox \
       --checkbox="$msg276" \
       --width=400 --height=360
    
    if zenity --question --title "LSW" --text "$msg217" --height=300 --width=300; then
        cd $HOME
        bash <(curl -s https://raw.githubusercontent.com/psygreg/lsw/refs/heads/main/src/lsw-in.sh)
        sleep 1
        rm txtbox
    fi

}

# photogimp - for those who already have GIMP installed
photogimp_in () {

    if zenity --question --text "$msg253" --width 360 --height 300; then
        if flatpak list --app | grep -q org.gimp.GIMP; then
            zeninf "$msg254"
            flatpak run org.gimp.GIMP & sleep 1
            PID=($(pgrep -f "gimp"))
            if [ -z "$PID" ]; then
                echo "Failed to find Flatpak process."
                return 1
            fi
            echo "Found Flatpak app running as PID $PID"
            sleep 20
            for ID in "${PID[@]}"; do
                kill "$ID"
            done
            wait "$PID" 2>/dev/null
            git clone https://github.com/Diolinux/PhotoGIMP.git
            cd PhotoGIMP
            cp -rf .config/* $HOME/.config/
            cp -rf .local/* $HOME/.local/
            cd ..
            rm -rf PhotoGIMP
        else
            nonfatal "$msg255"
        fi
    fi

}

# preload installation
preload_in () {

    local total_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local total_gb=$(( total_kb / 1024 / 1024 ))
    _cram=$(( total_gb ))

    if (( _cram < 16 )); then
        if zenity --question --text "$msg228" --width 360 --height 300; then
            insta preload
            zeninf "$msg229"
        fi
    else
        nonfatal "$msg230"
    fi

}

# runtime
. /etc/os-release
source /usr/bin/linuxtoys/linuxtoys.lib
_lang_
source /usr/bin/linuxtoys/${langfile}
# extras menu
while true; do

    CHOICE=$(zenity --list --title "Extras Menu" \
        --column="" \
        "$msg044" \
        "$msg045" \
        "$msg046" \
        "$msg048" \
        "$msg207" \
        "PhotoGIMP" \
        "$msg055" \
        "$msg177" \
        "$msg201" \
        "iNet Wireless Daemon" \
        "$msg057" \
        "$msg081" \
        "$msg079" \
        "$msg078" \
        "$msg053" \
        "$msg233" \
        "$msg209" \
        "$msg059" \
        --height=660 --width=450 --separator="|")

    if [ $? -ne 0 ]; then
        break
    fi

    case $CHOICE in
    "$msg044") ufw_in ;;
    "$msg045") swapfile_t ;;
    "$msg046") flatpak_in ;;
    "$msg048") lucidglyph_in ;;
    "$msg207") preload_in ;;
    "PhotoGIMP") photogimp_in ;;
    "$msg055") grubtrfs_t ;;
    "$msg177") psaver ;;
    "$msg201") touchegg_t ;;
    "iNet Wireless Daemon") iwd_summon ;;
    "$msg057") kernel_in ;;
    "$msg081") suse_codecs ;;
    "$msg079") fix_se_suse ;;
    "$msg078") nvidia_in ;;
    "$msg053") chaotic_aur_lib ;;
    "$msg233") if [ ! -f /.autopatch.state ]; then
           debfixer_lib
        else
           title="AutoPatcher"
           msg="$msg234"
           _msgbox_
        fi
        ;;
    "$msg209") lsw_in ;;
    "$msg059") break ;;
    *) echo "Invalid Option" ;;
    esac
done
