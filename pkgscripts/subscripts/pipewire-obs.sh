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
        local ver=$(curl -s "https://api.github.com/repos/dimtpap/obs-pipewire-audio-capture/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
        cd $HOME
        mkdir obspipe
        cd obspipe
        wget https://github.com/dimtpap/obs-pipewire-audio-capture/releases/download/${ver}/linux-pipewire-audio-${ver}-flatpak-30.tar.gz || { echo "Download failed"; cd ..; rm -rf obspipe; return 1; }
        tar xvzf linux-pipewire-audio-${ver}-flatpak-30.tar.gz
        mkdir -p $HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/linux-pipewire-audio
        cp -rf linux-pipewire-audio/* $HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/linux-pipewire-audio/
        sudo flatpak override --filesystem=xdg-run/pipewire-0 com.obsproject.Studio
        cd ..
        rm -rf obspipe
        return 0
    else 
        nonfatal "OBS Studio flatpak not installed."
    fi

}

# install plugin for native packages
native_pipe () {

    local ver=$(curl -s "https://api.github.com/repos/dimtpap/obs-pipewire-audio-capture/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    cd $HOME
    mkdir obspipe
    cd obspipe
    wget https://github.com/dimtpap/obs-pipewire-audio-capture/releases/download/${ver}/linux-pipewire-audio-${ver}.tar.gz || { echo "Download failed"; cd ..; rm -rf obspipe; return 1; }
    tar xvzf linux-pipewire-audio-${ver}.tar.gz
    mkdir -p $HOME/.config/obs-studio/plugins/linux-pipewire-audio
    cp -rf linux-pipewire-audio/* $HOME/.config/obs-studio/plugins/linux-pipewire-audio/
    cd ..
    rm -rf obspipe
    return 0

}

# native package checker
obscheck () {

    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
        if rpm -qi "obs-studio" 2>/dev/null 1>&2; then
            native_pipe
        else
            nonfatal "OBS Studio not found."
        fi
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
        if pacman -Qi "obs-studio" 2>/dev/null 1>&2; then
            native_pipe
        else
            nonfatal "OBS Studio not found."
        fi
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        if dpkg -s "obs-studio" 2>/dev/null 1>&2; then
            native_pipe
        else
            nonfatal "OBS Studio not found."
        fi
    else
        nonfatal "Invalid Operating System."
        exit 1
    fi

}

source /usr/bin/linuxtoys/linuxtoys.lib
depcheck_pipe
# menu
while true; do

    CHOICE=$(zenity --list --title "OBS Pipewire Audio Capture" --text "Choose your OBS version:" \
        --column "Options" \
        "Native" \
        "Flatpak" \
        "Cancel" \
        --width 300 --height 330)

    if [ $? -ne 0 ]; then
        exit 0
    fi

    case $CHOICE in
    "Native") obscheck && break ;;
    "Flatpak") flatpak_pipe && break ;;
    "Cancel") break ;;
    *) echo "Invalid Option" ;;
    esac
done
