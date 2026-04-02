#!/bin/bash
# name: pdefaults
# version: 1.0
# description: pdefaults_desc
# icon: optimizer.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy, !zorin
# reboot: yes
# noconfirm: yes
# nocontainer

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/optimizers.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
# system-agnostic scripts
sysag_run () {
    if ! is_cachyos || ! is_solus || [ ! -f /usr/lib/sysctl.d/99-cachyos-settings.conf ]; then
        # systemd patches
        cachyos_sysd_lib
    fi
    # shader booster
    sboost_lib
    # disable split-lock mitigation, which is not a security feature therefore is safe to disable
    dsplitm_lib
    # add earlyoom configuration
    earlyoom_lib
    # change intel driver to Xe on discrete GPUs
    if ! is_solus || ! is_fedora; then
        intel_xe_lib
    fi
    # fix GTK app rendering for Intel BMG and Nvidia GPUs
    fix_intel_gtk
    # set proton to run on wine-wayland mode by default
    wayland_proton_lib
    # add alive timeout fix for Gnome
    if echo "$XDG_CURRENT_DESKTOP" | grep -qi 'gnome'; then
        sudo gsettings set org.gnome.mutter check-alive-timeout 20000
    fi
    # vm.min_free_kbytes dynamic setup
    free_mem_fix
    # full kernel preemption for better latency in Fedora -- will skip automatically in other OS
    preempt_lib
    # fix video thumbnails
    _packages=(ffmpegthumbnailer)
    # codec fix for Fedora/OpenSUSE
    if [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ "fedora" ]]; then
        rpmfusion_chk
        _packages+=(libavcodec-freeworld gstreamer1-plugins-ugly)
    elif [[ "$ID_LIKE" == *suse* ]]; then
        sudo zypper in -y opi
        sudo opi codecs
    fi
    _install_
}
# consolidated installation
optimizer () {
    if [ ! -f $HOME/.local/.autopatch.state ]; then
        cd $HOME
        #if [ "$ID" == "debian" ]; then
            #debfixer_lib
        #fi
        # system-agnostic optimizations
        sysag_run
        touch $HOME/.local/.autopatch.state
        zeninf "$msg036"
    else
        fatal "$msg234"
    fi
}
# menu
while true; do
    CHOICE=$(zenity --list --title "Power Optimizer" --text "$msg229" \
        --column "Options" \
        "Desktop" \
        "Laptop" \
        "Cancel" \
        "Install without Power Profile" \
        --width 360 --height 360 )

    if [ $? -ne 0 ]; then
        exit 100
    fi

    case $CHOICE in
    "Desktop") sudo_rq && pp_ondemand && optimizer && exit 0;;
    "Laptop") sudo_rq && optimizer && psave_lib && exit 0;;
    "Install without Power Profile" ) sudo_rq && optimizer && exit 0;;
    "Cancel") exit 100 ;;
    *) echo "Invalid Option" ;;
    esac
done
