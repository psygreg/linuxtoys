#!/bin/bash
# name: OBS Studio
# version: 1.0
# description: obs_desc
# icon: obs.svg
# repo: https://github.com/dimtpap/obs-pipewire-audio-capture
# reboot: ostree
# new

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# function - plugin to fix OBS mic
obs_pipe () {
    local ver=$(curl -s "https://api.github.com/repos/dimtpap/obs-pipewire-audio-capture/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    prep_tmp
    mkdir obspipe
    cd obspipe
    wget https://github.com/dimtpap/obs-pipewire-audio-capture/releases/download/${ver}/linux-pipewire-audio-${ver}-flatpak-30.tar.gz || { echo "Download failed"; cd ..; rm -rf obspipe; return 1; }
    tar xvzf linux-pipewire-audio-${ver}-flatpak-30.tar.gz
    prep_dir "$HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/linux-pipewire-audio"
    copy_ -rf linux-pipewire-audio/* $HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/linux-pipewire-audio/
    sudo flatpak override --filesystem=xdg-run/pipewire-0 com.obsproject.Studio
}
pkg_flat com.obsproject.Studio com.obsproject.Studio.Plugin.WaylandHotkeys
sudo_rq
# check dependency for Pipewire Audio Capture plugin and xwayland
pkg_install wireplumber
if is_arch || is_cachy || is_solus; then
    pkg_install xorg-xwayland
elif is_debian || is_ubuntu; then
    pkg_install xwayland
elif is_fedora || is_suse || is_ostree; then
    pkg_install xorg-x11-server-Xwayland
fi
obs_pipe
# Set QT_QPA_PLATFORM environment variable for CEF
flatpak override --user \
  --socket=x11 \
  --nosocket=wayland \
  --filesystem=/tmp/.X11-unix \
  --env=QT_QPA_PLATFORM=xcb \
  --env=DISPLAY=$VALID_DISPLAY \
  com.obsproject.Studio