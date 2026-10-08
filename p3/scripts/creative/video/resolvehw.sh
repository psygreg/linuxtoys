#!/bin/bash
# name: resolvehw
# version: 1.0
# description: resolvehw_desc
# icon: resolve.svg
# repo: https://github.com/EdvinNilsson/ffmpeg_encoder_plugin
# compat: ubuntu, debian, fedora, arch, cachy, rhel, suse

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
install_nobox () {
    ls /opt/resolve &>/dev/null || fatal "DaVinci Resolve is not currently installed in this computer."
    prep_tmp_noram
    wget https://github.com/EdvinNilsson/ffmpeg_encoder_plugin/releases/latest/download/ffmpeg_encoder_plugin.dvcp.bundle.zip || fatal "Failed to download plugin bundle."

    rm -rf ffmpeg_encoder_plugin.dvcp.bundle
    unzip ffmpeg_encoder_plugin.dvcp.bundle.zip || fatal "Failed to extract plugin bundle."
    [ -d ffmpeg_encoder_plugin.dvcp.bundle ] || fatal "Plugin bundle was not found after extraction."

    prep_dir /opt/resolve/IOPlugins/
    prep_dir_edit /opt/resolve/IOPlugins/ffmpeg_encoder_plugin.dvcp.bundle
    sudo_ rm -rf -- /opt/resolve/IOPlugins/ffmpeg_encoder_plugin.dvcp.bundle || fatal "Failed to replace plugin bundle."

    copy_ -r ffmpeg_encoder_plugin.dvcp.bundle /opt/resolve/IOPlugins/ || fatal "Failed to install plugin bundle."
    if is_fedora || is_rhel; then
        call_script codecfix
    elif is_suse; then
        pkg_brew ffmpeg-full
    elif is_ubuntu || is_debian; then
        pkg_install ffmpeg
    elif is_arch || is_cachy || is_manjaro; then
        pkg_install ffmpeg davinci-ffmpeg-encoder-plugin
    fi
    if is_icr_capable && ! is_hybridgpu; then
        call_script intelxe
    fi
}
install_dvbox() {
    distrobox enter davincibox -- ls /opt/resolve &>/dev/null || fatal "DaVinci Resolve is not currently installed in this computer."
    prep_tmp_noram
    wget https://github.com/EdvinNilsson/ffmpeg_encoder_plugin/releases/latest/download/ffmpeg_encoder_plugin.dvcp.bundle.zip || fatal "Failed to download plugin bundle."
    rm -rf ffmpeg_encoder_plugin.dvcp.bundle
    unzip ffmpeg_encoder_plugin.dvcp.bundle.zip || fatal "Failed to extract plugin bundle."
    [ -d ffmpeg_encoder_plugin.dvcp.bundle ] || fatal "Plugin bundle was not found after extraction."
    distrobox_prep_dir davincibox /opt/resolve/IOPlugins/
    distrobox_prep_dir_edit davincibox /opt/resolve/IOPlugins/ffmpeg_encoder_plugin.dvcp.bundle
    distrobox enter davincibox -- rm -rf -- /opt/resolve/IOPlugins/ffmpeg_encoder_plugin.dvcp.bundle 2>/dev/null \
        || distrobox enter davincibox -- sudo rm -rf -- /opt/resolve/IOPlugins/ffmpeg_encoder_plugin.dvcp.bundle \
        || fatal "Failed to replace plugin bundle in DaVinciBox."
    distrobox_copy_ davincibox -r ffmpeg_encoder_plugin.dvcp.bundle /opt/resolve/IOPlugins/ \
        || fatal "Failed to install plugin bundle into DaVinciBox."
    distrobox enter davincibox -- sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(distrobox enter davincibox -- rpm -E %fedora).noarch.rpm \
        https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(distrobox enter davincibox -- rpm -E %fedora).noarch.rpm || fatal "Failed to add RPMFusion repositories in DaVinciBox."
    distrobox enter davincibox -- sudo dnf swap ffmpeg-free ffmpeg --allowerasing -y || fatal "Failed to swap ffmpeg packages in DaVinciBox."
    if is_intel; then
        distrobox enter davincibox -- sudo dnf install intel-media-driver intel-vpl-gpu-rt -y || fatal "Failed to install Intel media drivers in DaVinciBox."
    fi
}

if [ "$AUTO_DVBOX" = "1" ]; then
    install_dvbox
elif [ "$AUTO_DVNAT" = "1" ]; then
    install_nobox
else
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
fi

info "DaVinci Resolve FFmpeg Plugin installed successfully!"
