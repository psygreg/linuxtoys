#!/bin/bash
# name: resolvehw
# version: 1.0
# description: resolvehw_desc
# icon: resolve.svg
# repo: https://github.com/EdvinNilsson/ffmpeg_encoder_plugin
# compat: ubuntu, debian, fedora, arch, cachy, rhel

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
install_nobox () {
    ls /opt/resolve &>/dev/null || fatal "DaVinci Resolve is not currently installed in this computer."
    prep_tmp_noram
    wget https://github.com/EdvinNilsson/ffmpeg_encoder_plugin/releases/latest/download/ffmpeg_encoder_plugin.dvcp.bundle.zip || fatal "Failed to download plugin bundle."
    prep_dir /opt/resolve/IOPlugins/
    sudo unzip ffmpeg_encoder_plugin.dvcp.bundle.zip -d /opt/resolve/IOPlugins/ || fatal "Failed to unzip plugin bundle."
    if is_fedora || is_rhel; then
        rpmfusion_chk
        sudo dnf swap ffmpeg-free ffmpeg --allowerasing -y || fatal "Failed to swap ffmpeg packages."
        if is_intel; then
            pkg_install intel-media-driver intel-vpl-gpu-rt -y || fatal "Failed to install Intel media drivers."
        fi
    elif is_ubuntu || is_debian; then
        pkg_install ffmpeg
        if is_intel; then
            { is_debian && enable_debian_nonfree; } || true
            pkg_install intel-media-va-driver-non-free libmfx-gen1.2
        fi
    elif is_arch || is_cachy || is_manjaro; then
        pkg_install ffmpeg davinci-ffmpeg-encoder-plugin
        if is_intel; then
            pkg_install intel-media-driver vpl-gpu-rt
        fi
    fi
}
install_dvbox() {
    distrobox enter davincibox -- ls /opt/resolve &>/dev/null || fatal "DaVinci Resolve is not currently installed in this computer."
    prep_tmp_noram
    wget https://github.com/EdvinNilsson/ffmpeg_encoder_plugin/releases/latest/download/ffmpeg_encoder_plugin.dvcp.bundle.zip || fatal "Failed to download plugin bundle."
    distrobox enter davincibox -- mkdir -p /opt/resolve/IOPlugins/ || fatal "Failed to create IOPlugins directory in DaVinciBox."
    distrobox enter davincibox -- sudo unzip ffmpeg_encoder_plugin.dvcp.bundle.zip -d /opt/resolve/IOPlugins/ || fatal "Failed to unzip plugin bundle into DaVinciBox."
    distrobox enter davincibox -- sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(distrobox enter davincibox -- rpm -E %fedora).noarch.rpm \
        https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(distrobox enter davincibox -- rpm -E %fedora).noarch.rpm || fatal "Failed to add RPMFusion repositories in DaVinciBox."
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
