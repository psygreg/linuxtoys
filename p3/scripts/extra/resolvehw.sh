#!/bin/bash
# name: resolvehw
# version: 1.0
# description: resolvehw_desc
# icon: resolve.svg
# repo: https://github.com/EdvinNilsson/ffmpeg_encoder_plugin
# compat: ubuntu, debian, fedora, arch, cachy

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
install_nobox () {
    # Install build dependencies
    if is_fedora || is_ostree; then
        if rpmfusion_chk; then
            pkg_install cmake gcc-c++ ffmpeg-devel git make
            if is_intel; then
                pkg_install intel-media-driver intel-vpl-gpu-rt
            fi
        fi
    elif is_ubuntu || is_debian; then
        pkg_install build-essential cmake libavcodec-dev libavformat-dev libavutil-dev libswscale-dev git make
        if is_intel; then
            pkg_install intel-media-driver
        fi
    elif is_arch || is_cachy; then
        pkg_install cmake ffmpeg git make base-devel
        if is_intel; then
            pkg_install intel-media-driver vpl-gpu-rt
        fi
    fi

    # Clone and build
    prep_tmp
    if [ -d "ffmpeg_encoder_plugin" ]; then
        rm -rf ffmpeg_encoder_plugin
    fi
    git clone https://github.com/EdvinNilsson/ffmpeg_encoder_plugin
    cd ffmpeg_encoder_plugin
    mkdir build
    cd build
    cmake -DCMAKE_INSTALL_PREFIX=/usr ..
    make

    # Install
    # Directory structure for Linux-x86-64
    prep_dir "/opt/resolve/IOPlugins/ffmpeg_encoder_plugin.dvcp.bundle/Contents/Linux-x86-64"
    PLUGIN_DIR="/opt/resolve/IOPlugins/ffmpeg_encoder_plugin.dvcp.bundle/Contents/Linux-x86-64"
    sudo_rq
    copy_ ffmpeg_encoder_plugin.dvcp "$PLUGIN_DIR/"
}
install_dvbox() {
    prep_tmp
    wget https://github.com/EdvinNilsson/ffmpeg_encoder_plugin/releases/latest/download/ffmpeg_encoder_plugin.dvcp.bundle.zip || fatal "Failed to download plugin bundle."
    distrobox enter davincibox -- unzip ffmpeg_encoder_plugin.dvcp.bundle.zip -d /opt/resolve/IOPlugins/ || fatal "Failed to unzip plugin bundle into DaVinciBox."
    distrobox enter davincibox -- sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm \
        https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm || fatal "Failed to add RPMFusion repositories in DaVinciBox."
    distrobox enter davincibox -- sudo dnf swap ffmpeg-free ffmpeg --allowerasing -y || fatal "Failed to swap ffmpeg packages in DaVinciBox."
    if is_intel; then
        distrobox enter davincibox -- sudo dnf install intel-media-driver intel-vpl-gpu-rt -y || fatal "Failed to install Intel media drivers in DaVinciBox."
    fi
}
while true; do
    CHOICE=$(zenity --list --title "DaVinci Resolve FFMPEG Plugin" --text "$msg229" \
        --column "Options" \
        "DaVinciBox" \
        "Local Installation" \
        "Cancel" \
        --width 360 --height 360 )

    if [ $? -ne 0 ]; then
        exit 100
    fi

    case $CHOICE in
    "DaVinciBox" ) install_dvbox && break;;
    "Local Installation") install_nobox && break;;
    "Cancel") exit 100 ;;
    *) echo "Invalid Option" ;;
    esac
done

zeninf "DaVinci Resolve FFmpeg Plugin installed successfully!"
