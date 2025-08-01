#!/bin/bash
# functions

# updater
current_ltver="4.0"
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
wget -q -O - "https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/README.md" > /dev/null || { whiptail --title "Disconnected" --msgbox "LinuxToys requires an internet connection to proceed." 8 78; exit 1; }
# call linuxtoys turbobash lib
sleep 1
source linuxtoys.lib
# logger
logfile="$HOME/.local/linuxtoys-log.txt"
_log_
# language and upd checks
_lang_
source ${langfile}
sleep 1
ver_upd

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
        "" \
        "$msg124" \
        "GitHub" \
        "${msg275}" \
        "$msg059" \
        --height=500 --width=360)
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
    "$msg227") subscript="pdefaults" && _invoke_ ;;
    "$msg199") supmenu="csupermenu" && _invoke_ ;;
    # 7) subscript="uniwine" && _invoke_ ;; -- disabled option
    "$msg124") zeninf "$msg125";;
    "GitHub") xdg-open https://github.com/psygreg/linuxtoys ;;
    "${msg275}") xdg-open https://ko-fi.com/psygreg ;;
    "$msg059") break ;;
    *) echo "Invalid Option" ;;
    esac
done
