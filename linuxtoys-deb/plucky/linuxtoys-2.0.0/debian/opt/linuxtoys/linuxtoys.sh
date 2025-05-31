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
current_ltver="2.0.0"
ver_upd () {

    local ver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/ver)
    if [[ "$ver" != "$current_ltver" ]]; then
        if whiptail --title "$msg001" --yesno "$msg002" 8 78; then
            cd $HOME
            if [[ "$ID_LIKE" =~ (rhel|fedora|suse) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
                wget https://github.com/psygreg/linuxtoys/releases/latest/download/linuxtoys-${ver}-1.amd64.rpm
                if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
                    nohup xterm -e "bash -c 'whiptail --title \"$msg003\" --msgbox \"$msg004\" 8 78 && sudo zypper in ${HOME}/linuxtoys_${ver}-1.amd64.rpm -y && whiptail --title \"$msg003\" --msgbox \"$msg005\" 8 78 && rm ${HOME}/linuxtoys_${ver}-1.amd64.rpm'" >/dev/null 2>&1 && disown
                else
                    nohup xterm -e "bash -c 'whiptail --title \"$msg003\" --msgbox \"$msg004\" 8 78 && sudo dnf in ${HOME}/linuxtoys_${ver}-1.amd64.rpm -y && whiptail --title \"$msg003\" --msgbox \"$msg005\" 8 78 && rm ${HOME}/linuxtoys_${ver}-1.amd64.rpm'" >/dev/null 2>&1 && disown  
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

# supermenu run
supermenu_run () {

    wget -O ${supmenu}.sh https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/supermenus/${supmenu}.sh
    chmod +x ${supmenu}.sh
    ./${supmenu}.sh
    rm ${supmenu}.sh

}

# logger
logfile="$HOME/.local/linuxtoys-log.txt"
exec 2> >(tee "$logfile" >&2)

# language and upd checks
det_langfile
source $HOME/.local/${langfile}_${current_ltver}
. /etc/os-release
ver_upd

# main menu
while :; do

    CHOICE=$(whiptail --title "LinuxToys" --menu "LinuxToys ${current_ltver}" 25 78 16 \
        "0" "$msg120" \
        "1" "$msg121" \
        "2" "$msg122" \
        "3" "$msg123" \
        "4" "$msg059" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        break
    fi

    case $CHOICE in
    0) supmenu="usupermenu" && supermenu_run ;;
    1) supmenu="osupermenu" && supermenu_run ;;
    2) supmenu="gsupermenu" && supermenu_run ;;
    3) supmenu="esupermenu" && supermenu_run ;;
    4 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done
