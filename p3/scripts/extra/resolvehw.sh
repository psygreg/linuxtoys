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
if lspci | grep -E "VGA|3D" | grep -i "Intel" > /dev/null; then
    GPU="Intel"
fi
# Get the latest release URL from GitHub API
GITHUB_API="https://api.github.com/repos/EdvinNilsson/ffmpeg_encoder_plugin/releases/latest"
LATEST_RELEASE=$(curl -s "$GITHUB_API" | grep '"download_url"' | grep 'ffmpeg_encoder_plugin.dvcp.bundle.zip' | head -1 | cut -d'"' -f4)
if [ -z "$LATEST_RELEASE" ]; then
    # Fallback: try to construct URL from release tag
    RELEASE_TAG=$(curl -s "$GITHUB_API" | grep '"tag_name"' | head -1 | cut -d'"' -f4)
    if [ -n "$RELEASE_TAG" ]; then
        LATEST_RELEASE="https://github.com/EdvinNilsson/ffmpeg_encoder_plugin/releases/download/${RELEASE_TAG}/ffmpeg_encoder_plugin.dvcp.bundle.zip"
    fi
fi
if [ -n "$LATEST_RELEASE" ]; then
    cd $HOME
    # Download and execute the install.sh script
    wget "$LATEST_RELEASE"
    unzip ffmpeg_encoder_plugin.dvcp.bundle.zip -d /opt/resolve/IOPlugins/
else
    fatal "Cannot find ffmpeg_encoder_plugin.dvcp.bundle.zip in the latest release"
fi
if [ "$GPU" = "Intel" ]; then
    if is_fedora || is_ostree; then
        rpmfusion_chk
        _packages=(intel-media-driver intel-vpl-gpu-rt)
        _install_
        sudo dnf swap --allowerasing ffmpeg-free ffmpeg -y
    elif is_ubuntu || is_debian; then
        _packages=(intel-media-driver ffmpeg)
        _install_
    elif is_arch || is_cachy; then
        _packages=(intel-media-driver vpl-gpu-rt ffmpeg-full)
        _install_
    fi
fi

