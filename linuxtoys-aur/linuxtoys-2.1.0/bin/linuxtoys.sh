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
current_ltver="2.1.0"
ver_upd () {

    local ver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/ver)
    if [[ "$ver" != "$current_ltver" ]]; then
        if whiptail --title "$msg001" --yesno "$msg002" 8 78; then
            cd $HOME
            if [[ "$ID_LIKE" =~ (rhel|fedora|suse) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
                wget https://github.com/psygreg/linuxtoys/releases/latest/download/linuxtoys-${ver}-1.amd64.rpm
                if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
                    nohup xterm -e "bash -c 'whiptail --title \"$msg003\" --msgbox \"$msg004\" 8 78 && sudo zypper in ${HOME}/linuxtoys-${ver}-1.amd64.rpm -y && whiptail --title \"$msg003\" --msgbox \"$msg005\" 8 78 && rm ${HOME}/linuxtoys_${ver}-1.amd64.rpm'" >/dev/null 2>&1 && disown
                else
                    nohup xterm -e "bash -c 'whiptail --title \"$msg003\" --msgbox \"$msg004\" 8 78 && sudo dnf in ${HOME}/linuxtoys-${ver}-1.amd64.rpm -y && whiptail --title \"$msg003\" --msgbox \"$msg005\" 8 78 && rm ${HOME}/linuxtoys_${ver}-1.amd64.rpm'" >/dev/null 2>&1 && disown  
                fi
            elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
                wget https://github.com/psygreg/linuxtoys/releases/latest/download/linuxtoys_${ver}-1_amd64.deb
                nohup xterm -e "bash -c 'whiptail --title \"$msg003\" --msgbox \"$msg004\" 8 78 && sudo dpkg -i ${HOME}/linuxtoys_${ver}-1_amd64.deb && whiptail --title \"$msg003\" --msgbox \"$msg005\" 8 78 && rm ${HOME}/linuxtoys_${ver}-1_amd64.deb'" >/dev/null 2>&1 && disown
            elif [ "$ID" == "arch" ] || [[ "$ID_LIKE" =~ (arch) ]]; then
                wget https://github.com/psygreg/linuxtoys/releases/latest/download/PKGBUILD
                wget https://github.com/psygreg/linuxtoys/releases/latest/download/linuxtoys.install
                nohup xterm -e "bash -c 'whiptail --title \"$msg003\" --msgbox \"$msg004\" 8 78 && makepkg -si && whiptail --title \"$msg003\" --msgbox \"$msg005\" 8 78 && rm PKGBUILD && rm linuxtoys.install'" >/dev/null 2>&1 && disown
            fi
            exit 0
        fi
    fi

}

# kernel update checker for debian/ubuntu
krn_chk () {

    if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        source $HOME/.local/kernelsetting
        if [ ${_psygreg_krn} == "yes" ]; then
            if [ $(uname -r) != $(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/psy-krn) ]; then
                if whiptail --title "$msg126" --yesno "$msg127" 8 78; then
                    wget -O cachyos-deb.sh https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/linuxtoys/cachyos-deb.sh
                    chmod +x cachyos-deb.sh
                    ./cachyos-deb.sh
                    rm cachyos-deb.sh
                    # clean old kernels
                    dpkg --list | grep -v $(uname -r) | grep -E 'linux-image-[0-9]|linux-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
                    dpkg --list | grep -v $(uname -r) | grep -E 'custom-kernel-[0-9]|custom-kernel-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
                fi
            fi
        fi
    fi

}

# supermenu run
supermenu_run () {

    wget -nc -O ${supmenu}.sh https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/supermenus/${supmenu}.sh
    chmod +x ${supmenu}.sh
    ./${supmenu}.sh

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
det_langfile
source $HOME/.local/${langfile}_${current_ltver}
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
    0) supmenu="usupermenu" && supermenu_run ;;
    1) supmenu="osupermenu" && supermenu_run ;;
    2) supmenu="gsupermenu" && supermenu_run ;;
    3) supmenu="esupermenu" && supermenu_run ;;
    4) supmenu="dsupermenu" && supermenu_run ;;
    5) whiptail --title "LinuxToys v${current_ltver}" --msgbox "$msg125" 8 78 ;;
    6) xdg-open https://github.com/psygreg/linuxtoys ;;
    7 | q) find "$HOME" -maxdepth 1 -type f -name '*supermenu.sh' -exec rm -f {} + && break ;;
    *) echo "Invalid Option" ;;
    esac
done
