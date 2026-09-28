#!/usr/bin/env bash

obs_pipe () {
    local ver=$(curl -s "https://api.github.com/repos/dimtpap/obs-pipewire-audio-capture/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    prep_tmp_noram
    mkdir obspipe
    cd obspipe
    wget https://github.com/dimtpap/obs-pipewire-audio-capture/releases/download/${ver}/linux-pipewire-audio-${ver}-flatpak-30.tar.gz || { echo "Download failed"; cd ..; rm -rf obspipe; return 1; }
    tar xvzf linux-pipewire-audio-${ver}-flatpak-30.tar.gz
    prep_dir "$HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/linux-pipewire-audio"
    copy_ -rf linux-pipewire-audio/* $HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/linux-pipewire-audio/
}

# intel QSV support
is_intel && { pkg_flat org.freedesktop.Platform.VAAPI.Intel/x86_64/25.08 || fatal "Failed to install Intel VAAPI platform"; } || true

askpass
# check dependency for Pipewire Audio Capture plugin, xwayland and virtual camera
pkg_install wireplumber
if is_arch || is_cachy || is_solus; then
    pkg_install xorg-xwayland v4l2loopback-dkms
elif is_debian || is_ubuntu; then
    pkg_install --bypass xwayland v4l2loopback-dkms
    secureboot_check
elif is_fedora || is_rhel || is_ostree; then
    summon_helpers
    rpmfusion_chk
    secureboot_check
    pkg_install xorg-x11-server-Xwayland v4l2loopback
elif is_suse; then
    pkg_install xwayland v4l2loopback-autoload v4l2loopback-kmp-default v4l2loopback-utils
fi

obs_pipe

flatpak override --user --nosocket=wayland
