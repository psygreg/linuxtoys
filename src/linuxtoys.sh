#!/bin/bash
# functions
fatal() {
    zenity --error --title "Fatal Error" --text "$1" --height=300 --width=300
    exit 1
}

# sudo request
sudo_rq () {
    zenity --password | sudo -Sv || fatal "Wrong password. Do you have sudo?"
}

# updater
current_ltver="4.3"
ver_upd () {
    local ver
    ver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/ver)
    if [[ "$ver" != "$current_ltver" ]]; then
        if zenity --question --title "$msg001" --text "$msg002" --width 300 --height 300; then
            zeninf "$msg157"
            xdg-open https://github.com/psygreg/linuxtoys/releases/latest         
        fi
    fi
}

# runtime
# check internet connection
# ping google
. /etc/os-release
wget -q -O - "https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/README.md" > /dev/null || fatal "LinuxToys requires an internet connection to proceed."
# call linuxtoys turbobash lib
sleep 1
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
# logger
logfile="$HOME/.local/linuxtoys-log.txt"
_log_
# language and upd checks
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
sleep 1
ver_upd
sudo_rq

# main menu
while true; do

    CHOICE=$(zenity --list --title "LinuxToys" \
        --column="$msg274"  \
        "$msg120" \
        "$msg121" \
        "$msg122" \
        "${msg123}" \
        "${msg143}" \
        "$msg227" \
        "$msg199" \
        "$msg279" \
        "" \
        "$msg124" \
        "Wiki" \
        "${msg275}" \
        "$msg059" \
        --height=530 --width=360)
        #"7" "UniWine" \ -- disabled option

    if [ $? -ne 0 ]; then
        find "$HOME" -maxdepth 1 -type f -name '*.sh' -exec rm -f {} + && break
   	fi

    case $CHOICE in
    "$msg120") supmenu="usupermenu" && _invoke_ ;;
    "$msg121") supmenu="osupermenu" && _invoke_ ;;
    "$msg122") supmenu="gsupermenu" && _invoke_ ;;
    "${msg123}") supmenu="esupermenu" && _invoke_ ;;
    "${msg143}") supmenu="dsupermenu" && _invoke_ ;;
    "$msg227") subscript="pdefaults" && unset supmenu && _invoke_ ;;
    "$msg199") supmenu="csupermenu" && _invoke_ ;;
    "$msg279") subscript="psypicks" && unset supmenu && _invoke_ ;;
    # 7) subscript="uniwine" && unset supmenu && _invoke_ ;; -- disabled option
    "$msg124") zeninf "$msg125";;
    "Wiki") xdg-open https://github.com/psygreg/linuxtoys/wiki ;;
    "${msg275}") xdg-open https://ko-fi.com/psygreg ;;
    "$msg059") break ;;
    *) echo "Invalid Option" ;;
    esac
done
