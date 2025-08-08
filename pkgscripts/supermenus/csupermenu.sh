#!/bin/bash
# give user a rundown of its capabilities
about_c () {

    {
        echo "$msg190"
        echo "$msg191"
        echo "$msg192"
    } > txtbox

    zenity --text-info \
       --title="Console Mode" \
       --filename=txtbox \
       --checkbox="$msg276" \
       --width=400 --height=300

    case $? in
        0) enabler_c ;;
        1) echo "Cancelled." ;;
        -1) echo "An unexpected error has occurred." ;;
    esac

}

# enable console mode
enabler_c () {

    if command -v flatpak &> /dev/null && flatpak list | grep -q 'com.valvesoftware.Steam'; then
        cd $HOME
        mkdir -p $HOME/.config/autostart
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/consolemode/com.valvesoftware.Steam.desktop
        sudo cp com.valvesoftware.Steam.desktop $HOME/.config/autostart/
        flatpak override com.valvesoftware.Steam --talk-name=org.freedesktop.Flatpak
        flatpak override com.valvesoftware.Steam --filesystem=${HOME}/.local/share/flatpak
        if flatpak list | grep -q 'com.heroicgameslauncher.hgl'; then
            wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/consolemode/com.heroicgameslauncher.hgl.desktop
            sudo cp com.heroicgameslauncher.hgl.desktop $HOME/.config/autostart/
        fi
        zeninf "$msg197"
        xdg-open https://github.com/psygreg/linuxtoys/blob/main/src/resources/other/consolemode/console-${langfile}.md
        rm com.heroicgameslauncher.hgl.desktop
        rm com.valvesoftware.Steam.desktop
    else
        nonfatal "$msg196"
    fi

}

# disable console mode
disabler_c () {

    if [ -f "$HOME/.config/autostart/com.valvesoftware.Steam.desktop" ]; then
        sudo rm $HOME/.config/autostart/com.valvesoftware.Steam.desktop
    fi
    zeninf "$msg198"

}

# open instructions in browser
instructions_c () {

    zeninf "$msg203"
    xdg-open https://github.com/psygreg/linuxtoys/blob/main/src/resources/other/consolemode/console-${langfile}.md

}

# runtime
. /etc/os-release
source /usr/bin/linuxtoys/linuxtoys.lib
_lang_
source /usr/bin/linuxtoys/${langfile}
# menu
while true; do

    CHOICE=$(zenity --list --title "$msg199" \
        --column="$msg195" \
        "$msg193" \
        "$msg194" \
        "$msg202" \
        "$msg070" \
        --height=360 --width=300)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        break
    fi

    case $CHOICE in
    "$msg193") about_c ;;
    "$msg194") disabler_c ;;
    "$msg202") instructions_c ;;
    "$msg070") break ;;
    *) echo "Invalid Option" ;;
    esac

done
