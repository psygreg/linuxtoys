#!/bin/bash
# functions

# updater
current_ltver="2.1.2"
ver_upd () {
    local ver
    ver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/ver)
    if [[ "$ver" != "$current_ltver" ]]; then
        if whiptail --title "$msg001" --yesno "$msg002" 8 78; then
            cd "$HOME" || exit 1
            if [[ "$ID_LIKE" =~ (rhel|fedora|suse) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
                wget "https://github.com/psygreg/linuxtoys/releases/latest/download/linuxtoys-${ver}-1.amd64.rpm"
                if [[ "$ID_LIKE" == "suse" ]] || [[ "$ID" == "suse" ]]; then
                    nohup alacritty -e bash -c '
                        whiptail --title "'"$msg003"'" --msgbox "'"$msg004"'" 8 78 &&
                        sudo zypper in "'"$HOME"'/linuxtoys-'"$ver"'-1.amd64.rpm" -y &&
                        whiptail --title "'"$msg003"'" --msgbox "'"$msg005"'" 8 78 &&
                        rm -f "'"$HOME"'/linuxtoys-'"$ver"'-1.amd64.rpm"
                    ' >/dev/null 2>&1 &
                else
                    nohup alacritty -e bash -c '
                        whiptail --title "'"$msg003"'" --msgbox "'"$msg004"'" 8 78 &&
                        sudo dnf install "'"$HOME"'/linuxtoys-'"$ver"'-1.amd64.rpm" -y &&
                        whiptail --title "'"$msg003"'" --msgbox "'"$msg005"'" 8 78 &&
                        rm -f "'"$HOME"'/linuxtoys-'"$ver"'-1.amd64.rpm"
                    ' >/dev/null 2>&1 &
                fi
            elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [[ "$ID" == "debian" ]]; then
                wget "https://github.com/psygreg/linuxtoys/releases/latest/download/linuxtoys_${ver}-1_amd64.deb"
                nohup alacritty -e bash -c '
                    whiptail --title "'"$msg003"'" --msgbox "'"$msg004"'" 8 78 &&
                    sudo dpkg -i "'"$HOME"'/linuxtoys_'"$ver"'-1_amd64.deb" &&
                    whiptail --title "'"$msg003"'" --msgbox "'"$msg005"'" 8 78 &&
                    rm -f "'"$HOME"'/linuxtoys_'"$ver"'-1_amd64.deb"
                ' >/dev/null 2>&1 &
            elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]]; then
                wget "https://github.com/psygreg/linuxtoys/releases/latest/download/PKGBUILD"
                wget "https://github.com/psygreg/linuxtoys/releases/latest/download/linuxtoys.install"
                nohup alacritty -e bash -c '
                    whiptail --title "'"$msg003"'" --msgbox "'"$msg004"'" 8 78 &&
                    makepkg -si &&
                    whiptail --title "'"$msg003"'" --msgbox "'"$msg005"'" 8 78 &&
                    rm -f PKGBUILD linuxtoys.install
                ' >/dev/null 2>&1 &
            fi
            disown
            exit 0
        fi
    fi
}

# kernel update checker for debian/ubuntu
krn_chk () {

    if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        source $HOME/.local/kernelsetting
        if [ ${_psygreg_krn} == "yes" ]; then
            if [ $(uname -r) != $(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/psy-krn) ]; then
                if whiptail --title "$msg126" --yesno "$msg127" 8 78; then
                    bash <(curl -s https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/linuxtoys/cachyos-deb.sh) -s
                    # clean old kernels
                    dpkg --list | grep -v $(uname -r) | grep -E 'linux-image-[0-9]|linux-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
                    dpkg --list | grep -v $(uname -r) | grep -E 'custom-kernel-[0-9]|custom-kernel-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
                fi
            fi
        fi
    fi

}

# runtime
# logger
logfile="$HOME/.local/linuxtoys-log.txt"
exec 2> >(tee "$logfile" >&2)

# check internet connection
# ping google
ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1
if [ $? -ne 0 ]; then
    whiptail --title "Disconnected" --msgbox "LinuxToys requires an internet connection to proceed." 8 78
    exit 1
fi

# language and upd checks
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
det_langfile
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
. /etc/os-release
ver_upd
krn_chk

# main menu
while :; do

    CHOICE=$(whiptail --title "LinuxToys" --menu "LinuxToys ${current_ltver}" 25 78 16 \
        "0" "$msg120" \
        "1" "$msg121" \
        "2" "$msg122" \
        "3" "$msg123" \
        "4" "$msg143" \
        "" "" \
        "" "" \
        "5" "$msg124" \
        "6" "GitHub" \
        "7" "$msg059" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        find "$HOME" -maxdepth 1 -type f -name '*supermenu.sh' -exec rm -f {} + && break
    fi

    case $CHOICE in
    0) supmenu="usupermenu" && invoke_lib ;;
    1) supmenu="osupermenu" && invoke_lib ;;
    2) supmenu="gsupermenu" && invoke_lib ;;
    3) supmenu="esupermenu" && invoke_lib ;;
    4) supmenu="dsupermenu" && invoke_lib ;;
    5) whiptail --title "LinuxToys v${current_ltver}" --msgbox "$msg125" 8 78 ;;
    6) xdg-open https://github.com/psygreg/linuxtoys ;;
    7 | q) find "$HOME" -maxdepth 1 -type f -name '*supermenu.sh' -exec rm -f {} + && break ;;
    *) echo "Invalid Option" ;;
    esac
done
