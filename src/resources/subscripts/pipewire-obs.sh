#!/bin/bash
# functions

# depcheck
depcheck_pipe () {

    local _packages=(wireplumber)
    _install_

}

# install plugin for flatpak
flatpak_pipe () {

    if flatpak list --app | grep -q com.obsproject.Studio; then
        local ver="1.2.0"
        cd $HOME
        mkdir obspipe
        cd obspipe
        wget https://github.com/dimtpap/obs-pipewire-audio-capture/releases/download/${ver}/linux-pipewire-audio-${ver}-flatpak-30.tar.gz || { echo "Download failed"; cd ..; rm -rf obspipe; return 1; }
        tar xvzf linux-pipewire-audio-${ver}-flatpak-30.tar.gz
        cp -rf linux-pipewire-audio $HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/
        sudo flatpak override --filesystem=xdg-run/pipewire-0 com.obsproject.Studio
        cd ..
        rm -rf obspipe
    else 
        title="Installer"
        msg="OBS Studio flatpak not installed."
        _msgbox_
    fi

}

# install plugin for native packages
native_pipe () {

    local ver="1.2.0"
    cd $HOME
    mkdir obspipe
    cd obspipe
    wget https://github.com/dimtpap/obs-pipewire-audio-capture/releases/download/${ver}/linux-pipewire-audio-${ver}.tar.gz || { echo "Download failed"; cd ..; rm -rf obspipe; return 1; }
    tar xvzf linux-pipewire-audio-${ver}.tar.gz
    cp -rf linux-pipewire-audio $HOME/.config/obs-studio/plugins/
    cd ..
    rm -rf obspipe

}

# native package checker
obscheck () {

    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
        if rpm -qi "obs-studio" 2>/dev/null 1>&2; then
            native_pipe
        else
            whiptail --title "Installer" --msgbox "OBS Studio not found." 8 78
        fi
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]]; then
        if pacman -Qi "obs-studio" 2>/dev/null 1>&2; then
            native_pipe
        else
            whiptail --title "Installer" --msgbox "OBS Studio not found." 8 78
        fi
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        if dpkg -s "obs-studio" 2>/dev/null 1>&2; then
            native_pipe
        else
            whiptail --title "Installer" --msgbox "OBS Studio not found." 8 78
        fi
    else
        whiptail --title "Installer" --msgbox "Invalid Operating System." 8 78
    fi

}

source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
depcheck_pipe
# menu
while :; do

    CHOICE=$(whiptail --title "OBS Pipewire Audio Capture" --menu "Choose your OBS version:" 25 78 16 \
        "0" "Native" \
        "1" "Flatpak" \
        "2" "Cancel" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        break
    fi

    case $CHOICE in
    0) obscheck ;;
    1) flatpak_pipe ;;
    2 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done