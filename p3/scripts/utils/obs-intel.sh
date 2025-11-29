#!/bin/bash
# name: OBS Studio
# version: 1.0
# description: obs_desc
# icon: obs.svg
# gpu: Intel
# repo: https://github.com/dimtpap/obs-pipewire-audio-capture
# negates: obs

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
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
_packages=(wireplumber)
if is_fedora || is_ostree; then
    rpmfusion_chk
    _packages+=(obs-studio libva-intel-media-driver v4l2loopback)
elif is_suse || is_debian || is_ubuntu; then
    _packages+=(obs-studio intel-media-driver v4l2loopback)
elif is_arch || is_cachy; then # get obs-studio-browser from AUR for browser source
    _packages+=(obs-studio-browser libva-intel-driver intel-media-driver v4l2loopback-dkms)
fi
_install_
sleep 1
obs_pipe
zeninf "$msg018"