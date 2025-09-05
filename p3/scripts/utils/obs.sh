#!/bin/bash
# name: OBS Studio
# version: 1.0
# description: obs_desc
# icon: obs.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
# function - plugin to fix OBS mic
obs_pipe () {
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
}
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub com.obsproject.Studio
sleep 1
sudo_rq
# check dependency for Pipewire Audio Capture plugin
_packages=(wireplumber)
_install_
sleep 1
obs_pipe