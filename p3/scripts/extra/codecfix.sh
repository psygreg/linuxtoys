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
    pkg_exists \
        fdk-aac-free \
        libavcodec-free \
        libavdevice-free \
        libavfilter-free \
        libavformat-free \
        libavutil-free \
        libpostproc-free \
        libswresample-free \
        libswscale-free \
        ffmpeg-free
    sudo rpm-ostree override remove \
        "${pkg_found[@]}" \
        --install ffmpeg
    info "$finishmsg"
else
    zeninf "$msg077"
fi
