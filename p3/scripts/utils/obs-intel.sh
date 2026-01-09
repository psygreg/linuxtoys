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
    _packages+=(obs-studio libva-intel-media-driver v4l2loopback intel-vpl-gpu-rt xorg-x11-server-Xwayland)
elif is_suse || is_debian || is_ubuntu; then
    if [ "$ID" == "ubuntu" ]; then # install OBS Studio PPA for pure Ubuntu to avoid broken snap
        sudo add-apt-repository -y ppa:obsproject/obs-studio
        sudo apt-get update
    fi
    _packages+=(obs-studio intel-media-driver v4l2loopback xwayland)
elif is_arch || is_cachy; then # get obs-studio-browser from AUR for browser source, remove vlc-plugin-lua if installed to avoid conflicts with vlc-plugin-luajit
    if pacman -Qi vlc-plugin-lua &> /dev/null; then
        sudo pacman -R --noconfirm vlc-plugin-lua
    fi
    _packages+=(obs-studio-browser libva-intel-driver intel-media-driver v4l2loopback-dkms vpl-gpu-rt xorg-xwayland)
fi
_install_
sleep 1
obs_pipe
# Set QT_QPA_PLATFORM environment variable for CEF
if [ -f "$HOME/.local/share/applications/com.obsproject.Studio.desktop" ]; then
    if ! grep -q "QT_QPA_PLATFORM" "$HOME/.local/share/applications/com.obsproject.Studio.desktop"; then
        sed -i '/^Exec=/s/Exec=/Exec=env QT_QPA_PLATFORM=xcb /' "$HOME/.local/share/applications/com.obsproject.Studio.desktop"
    fi
elif [ -f "/usr/share/applications/obs.desktop" ]; then
    mkdir -p "$HOME/.local/share/applications"
    sudo sed -i '/^Exec=/s/Exec=/Exec=env QT_QPA_PLATFORM=xcb /' "$HOME/.local/share/applications/com.obsproject.Studio.desktop"
    cp "/usr/share/applications/obs.desktop" "$HOME/.local/share/applications/obs.desktop"
    sed -i '/^Exec=/s/Exec=/Exec=QT_QPA_PLATFORM=xcb /' "$HOME/.local/share/applications/com.obsproject.Studio.desktop"
fi
zeninf "$msg018"
