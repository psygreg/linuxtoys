#!/bin/bash
# name: codecfix
# version: 1.0
# description: codecfix_desc
# icon: codec.svg
# compat: suse, fedora, ostree, rhel
# revert: no

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
sudo_rq
if is_suse; then
    pkg_install opi
    sudo opi codecs
    zeninf "$msg018"
elif is_fedora || is_rhel; then
    rpmfusion_chk
    sudo dnf swap ffmpeg-free ffmpeg --allowerasing
    sudo dnf install @multimedia --setopt="install_weak_deps=False" --exclude=PackageKit-gstreamer-plugin
    zeninf "$msg018"
elif is_ostree; then
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
        --install ffmpeg openh264 gstreamer1-plugin-openh264 libavcodec-freeworld mesa-va-drivers-freeworld mesa-vdpau-drivers-freeworld mesa-vulkan-drivers-freeworld libavcodec-freeworld gstreamer1-plugins-bad-freeworld
else
    zeninf "$msg077"
fi
