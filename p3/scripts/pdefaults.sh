#!/bin/bash
# name: pdefaults
# version: 1.0
# description: pdefaults_desc
# icon: optimizer.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy
# reboot: yes
# noconfirm: yes
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
# system-agnostic scripts
sysag_run () {
    if ! is_cachy && ! is_zorin; then
        # systemd patches
        cachyos_sysd_lib
    fi
    # shader booster
    sboost_lib
    # disable split-lock mitigation, which is not a security feature therefore is safe to disable
    dsplitm_lib
    # add earlyoom configuration, Fedora already has systemd-oomd
    if ! is_fedora && ! is_ostree; then
        earlyoom_lib
    fi
    # change intel driver to Xe on discrete GPUs
    if ! is_fedora && ! is_ubuntu; then
        intel_xe_lib
    fi
    # fix GTK app rendering for Intel BMG and Nvidia GPUs
    fix_intel_gtk
    # add alive timeout fix for Gnome
    if echo "$XDG_CURRENT_DESKTOP" | grep -qi 'gnome'; then
        sudo gsettings set org.gnome.mutter check-alive-timeout 20000
    fi
    # vm.min_free_kbytes dynamic setup - disabled for further testing
    # free_mem_fix
    # full kernel preemption for better latency in Fedora -- will skip automatically in other OS
    preempt_lib
}
# consolidated installation
optimizer () {
    if [ ! -f $HOME/.local/.autopatch.state ]; then
        prep_tmp
        sysag_run
        touch "$HOME/.local/.autopatch.state"
        zeninf "$msg036"
    else
        zenwrn "$msg234"
        exit 100
    fi
}
# menu
while true; do
    CHOICE=$(zenity --list --title "Power Optimizer" --text "$msg229" \
        --column "Options" \
        "Install without Power Profile" \
        "Desktop" \
        "Laptop" \
        "Cancel" \
        --width 360 --height 360 )

    if [ $? -ne 0 ]; then
        exit 100
    fi

    case $CHOICE in
    "Install without Power Profile" ) sudo_rq && optimizer && exit 0;;
    "Desktop") sudo_rq && pp_ondemand && optimizer && exit 0;;
    "Laptop") sudo_rq && optimizer && psave_lib && exit 0;;
    "Cancel") exit 100 ;;
    *) echo "Invalid Option" ;;
    esac
done
