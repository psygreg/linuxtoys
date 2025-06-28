#!/bin/bash

UHANDLER="${LINUXTOYS_UHANDLER}"

# give user a rundown of its capabilities
about_c () {

    {
        echo "$msg190"
        echo "$msg191"
        echo "$msg192"
    } > txtbox
    whiptail --textbox txtbox 12 80

}

# enable console mode
enabler_c () {

    if command -v flatpak &> /dev/null && flatpak list | grep -q 'com.valvesoftware.Steam'; then
        cd $HOME
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/consolemode/com.valvesoftware.Steam.desktop
        sudo cp com.valvesoftware.Steam.desktop $HOME/.config/autostart/
        flatpak override com.valvesoftware.Steam --talk-name=org.freedesktop.Flatpak
        flatpak override com.valvesoftware.Steam --filesystem=${HOME}/.local/share/flatpak
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/consolemode/com.heroicgameslauncher.hgl.desktop
        sudo cp com.heroicgameslauncher.hgl.desktop $HOME/.config/autostart/
        local title="$msg006"
        local msg="$msg197"
        _msgbox_
        xdg-open https://github.com/psygreg/linuxtoys/blob/main/src/resources/other/consolemode/console-${langfile}.md
        rm com.heroicgameslauncher.hgl.desktop
        rm com.valvesoftware.Steam.desktop
    else
        local title="$msg030"
        local msg="$msg196"
        _msgbox_
    fi

}

# disable console mode
disabler_c () {

    if [ -f "$HOME/.config/autostart/com.valvesoftware.Steam.desktop" ]; then
        sudo rm $HOME/.config/autostart/com.valvesoftware.Steam.desktop
    fi
    title="$msg006"
    msg="$msg198"
    _msgbox_

}

# open instructions in browser
instructions_c () {

    local title="$msg199"
    local msg="$msg203"
    _msgbox_
    xdg-open https://github.com/psygreg/linuxtoys/blob/main/src/resources/other/consolemode/console-${langfile}.md

}

# runtime
. /etc/os-release
source <(${UHANDLER} https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
_lang_
source <(${UHANDLER} https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
# menu
while :; do

    CHOICE=$(whiptail --title "LinuxToys" --menu "$msg195" 20 78 10 \
        "0" "$msg190" \
        "1" "$msg193" \
        "2" "$msg194" \
        "3" "$msg202" \
        "4" "$msg070" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        break
    fi

    case $CHOICE in
    0) about_c ;;
    1) enabler_c ;;
    2) disabler_c ;;
    3) instructions_c ;;
    4 | q) break ;;
    *) echo "Invalid Option" ;;
    esac

done
