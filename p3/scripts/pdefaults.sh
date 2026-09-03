#!/bin/bash
# name: pdefaults
# version: 1.0
# description: pdefaults_desc
# icon: optimizer.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy, rhel, !zorin, !deepin, ostree
# reboot: yes
# noconfirm: yes
# nocontainer
# systemd: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
# system-agnostic scripts
sysag_run () {
    call_script cachyconfs
    # shader booster
    call_script sboost
    # disable split-lock mitigation, which is not a security feature therefore is safe to disable
    call_script dsplitm
    # add earlyoom configuration, Fedora already has systemd-oomd
    call_script earlyoom
    # change intel driver to Xe on discrete GPUs
    call_script intelxe
    # fix GTK app rendering for Intel BMG and Nvidia GPUs
    call_script gtk-bmg-fix
    # add alive timeout fix for Gnome
    if echo "$XDG_CURRENT_DESKTOP" | grep -qi 'gnome'; then
        sudo gsettings set org.gnome.mutter check-alive-timeout 20000
    fi
    # full kernel preemption for better latency in Fedora -- will skip automatically in other OS
    call_script preemptfedora
}
# consolidated installation
optimizer () {
    if [ ! -f $HOME/.local/.autopatch.state ]; then
        prep_tmp
        sysag_run
        prep_create "$HOME/.local/.autopatch.state"
        zeninf "$msg036"
    else
        zenwrn "$msg234"
        exit 100
    fi
}
# menu
while true; do
    OPTIONS=(
        TRUE  "standard"    "Install without Power Profile"
    )
    if ! is_zorin && ! is_cachy && ! is_suse; then
        OPTIONS+=(
            FALSE "laptop" "Laptop"
        )
    fi
    CPU_VENDOR=$(awk -F ': *' '/^vendor_id/ { print $2; exit }' /proc/cpuinfo)
    if [[ "$CPU_VENDOR" == "AuthenticAMD" ]]; then
        OPTIONS+=(
            FALSE "performance" "High Performance"
        )
    fi
    OPTIONS+=(
        FALSE "cancel" "$msg070"
    )

    CHOICE=$(
        zenity --list \
            --radiolist \
            --title="Power Optimizer" \
            --text="$msg229" \
            --column="Select" \
            --column="ID" \
            --column="Options" \
            --hide-column=2 \
            --print-column=2 \
            "${OPTIONS[@]}" \
            --width=360 \
            --height=360
    )
    status=$?

    if (( status != 0 )) || [[ -z "$CHOICE" ]]; then
        exit 100
    fi
    case "$CHOICE" in
        standard)
            askpass && optimizer
            exit $?
            ;;
        performance)
            askpass && call_script ondemand && optimizer
            exit $?
            ;;
        laptop)
            laptop_mode=1
            askpass && optimizer && call_script psaver
            exit $?
            ;;
        cancel)
            exit 100
            ;;
        *)
            printf 'Unexpected option returned by Zenity: %q\n' "$CHOICE" >&2
            exit 1
            ;;
    esac
done