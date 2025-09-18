#!/bin/bash
# name: codecfix-hw
# version: 1.0
# description: codecfix-hw_desc
# icon: codec.svg
# compat: fedora, ostree
# reboot: yes

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
sudo_rq
rpmfusion_chk
if command -v rpm-ostree &> /dev/null; then
    sudo rpm-ostree override remove \
    ffmpeg-free \
    libavcodec-free \
    libavfilter-free \
    libavformat-free \
    libavutil-free \
    libpostproc-free \
    libswresample-free \
    libswscale-free \
    libavdevice-free \
    noopenh264 \
    --install ffmpeg openh264 gstreamer1-plugin-openh264 libavcodec-freeworld mesa-va-drivers-freeworld mesa-vdpau-drivers-freeworld mesa-vulkan-drivers-freeworld vlc-plugins-freeworld libavcodec-freeworld gstreamer1-plugins-bad-freeworld
else
    _rmpkgs=(ffmpeg-free libavcodec-free libavfilter-free libavformat-free libavutil-free libpostproc-free libswresample-free libswscale-free libavdevice-free noopenh264)
    for pkg in "${_rmpkgs[@]}"; do
        if rpm -qi "$pkg" &> /dev/null; then
            sudo dnf remove -y "$pkg"
        fi
    done
    _packages=(ffmpeg openh264 gstreamer1-plugin-openh264 libavcodec-freeworld mesa-va-drivers-freeworld mesa-vdpau-drivers-freeworld mesa-vulkan-drivers-freeworld vlc-plugins-freeworld libavcodec-freeworld gstreamer1-plugins-bad-freeworld)
    _install_
fi
zeninf "$msg036"