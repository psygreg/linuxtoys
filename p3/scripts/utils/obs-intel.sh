#!/bin/bash
# name: OBS Studio
# version: 1.0
# description: obs_desc
# icon: obs.svg
# gpu: Intel
# repo: https://github.com/dimtpap/obs-pipewire-audio-capture

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
# function - plugin to fix OBS mic
obs_pipe () {
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
}
sleep 1
sudo_rq
_packages=(obs-studio wireplumber)
_install_
sleep 1
obs_pipe
zeninf "$msg018"