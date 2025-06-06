#!/bin/bash
# functions

# menu
runners_menu () {

    local spritz_status=$([ "$_spritz" = "1" ] && echo "ON" || echo "OFF")
    local osu_status=$([ "$_osu" = "1" ] && echo "ON" || echo "OFF")

    while :; do

        local selection
        selection=$(whiptail --title "$msg131" --checklist \
            "$msg131" 20 78 15 \
            "Spritz" "$msg153" $spritz_status \
            "Osu!-Wine" "$msg154" $osu_status \
            3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
            break
        fi

        [[ "$selection" == *"Spritz"* ]] && _spritz="1" || _spritz=""
        [[ "$selection" == *"Osu!-Wine"* ]] && _osu="1" || _osu=""

        if [[ -n "$_spritz" ]]; then
            cd $HOME
            local krnver=$(uname -r | cut -d- -f1)
            local krnmaj=$(echo "$krnver" | cut -d. -f1)
            local krnmin=$(echo "$krnver" | cut -d. -f2)
            if (( KERNEL_MAJOR > 6 )) || { (( KERNEL_MAJOR == 6 )) && (( KERNEL_MINOR > 13 )); }; then
                wget https://github.com/NelloKudo/WineBuilder/releases/download/spritz-v10.9-1/spritz-wine-tkg-ntsync-fonts-wow64-10.9-2-x86_64.tar.xz
                tar -xf spritz-wine-tkg-ntsync-fonts-wow64-10.9-2-x86_64.tar.xz
                cp -rf spritz-wine-tkg-ntsync-10.9 $HOME/.var/app/net.lutris.Lutris/data/lutris/runners/wine/
                rm spritz-wine-tkg-ntsync-fonts-wow64-10.9-2-x86_64.tar.xz
                rm -rf spritz-wine-tkg-ntsync-10.9
            else
                wget https://github.com/NelloKudo/WineBuilder/releases/download/spritz-v10.9-1/spritz-wine-tkg-fonts-wow64-10.9-2-x86_64.tar.xz
                tar -xf spritz-wine-tkg-fonts-wow64-10.9-2-x86_64.tar.xz
                cp -rf spritz-wine-tkg-10.9 $HOME/.var/app/net.lutris.Lutris/data/lutris/runners/wine/
                rm spritz-wine-tkg-fonts-wow64-10.9-2-x86_64.tar.xz
                rm -rf spritz-wine-tkg-10.9
            fi
        fi
        if [[ -n "$_osu" ]]; then
            wget https://github.com/NelloKudo/WineBuilder/releases/download/wine-osu-staging-10.8-2/wine-osu-winello-fonts-wow64-10.8-2-x86_64.tar.xz
            tar -xf wine-osu-winello-fonts-wow64-10.8-2-x86_64.tar.xz
            cp -rf wine-osu $HOME/.var/app/net.lutris.Lutris/data/lutris/runners/wine/
            rm wine-osu-winello-fonts-wow64-10.8-2-x86_64.tar.xz
            rm -rf wine-osu
        fi
    
    done

}

# runtime
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
if command -v flatpak &> /dev/null && flatpak list | grep -q 'net.lutris.Lutris'; then
    runners_menu
else
    title="$msg030"
    msg="$msg155"
    _msgbox_
fi
