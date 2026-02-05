#!/bin/bash
# name: resolvehw
# version: 1.0
# description: resolvehw_desc
# icon: resolve.svg
# repo: https://github.com/EdvinNilsson/ffmpeg_encoder_plugin
# compat: ubuntu, debian, fedora, arch, cachy

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
# detect GPU if Intel
# detect GPU if Intel
if lspci | grep -E "VGA|3D" | grep -i "Intel" > /dev/null; then
    GPU="Intel"
fi

# Install build dependencies
if is_fedora || is_ostree; then
    rpmfusion_chk
    _packages=(cmake gcc-c++ ffmpeg-devel git make)
    if [ "$GPU" = "Intel" ]; then
        _packages+=(intel-media-driver intel-vpl-gpu-rt)
    fi
    _install_
elif is_ubuntu || is_debian; then
    _packages=(build-essential cmake libavcodec-dev libavformat-dev libavutil-dev libswscale-dev git make)
    if [ "$GPU" = "Intel" ]; then
        _packages+=(intel-media-driver)
    fi
    _install_
elif is_arch || is_cachy; then
    _packages=(cmake ffmpeg git make base-devel)
    if [ "$GPU" = "Intel" ]; then
        _packages+=(intel-media-driver vpl-gpu-rt)
    fi
    _install_
fi

# Clone and build
cd $HOME
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
PLUGIN_DIR="/opt/resolve/IOPlugins/ffmpeg_encoder_plugin.dvcp.bundle/Contents/Linux-x86-64"
sudo mkdir -p "$PLUGIN_DIR"
sudo cp ffmpeg_encoder_plugin.dvcp "$PLUGIN_DIR/"

# Cleanup
cd $HOME
rm -rf ffmpeg_encoder_plugin
zeninf "DaVinci Resolve FFmpeg Plugin installed successfully!"

