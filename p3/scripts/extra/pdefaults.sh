#!/bin/bash
# name: pdefaults
# version: 1.0
# description: pdefaults_desc
# icon: optimizer.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy, rhel, !zorin, !deepin, ostree, !gregos
# reboot: yes
# noconfirm: yes
# nocontainer
# systemd: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
# system-agnostic scripts
sysag_run () {
    # call_script cachyconfs
    # shader booster
    call_script sboost
    # disable split-lock mitigation, which is not a security feature therefore is safe to disable
    call_script dsplitm
    # GPU-aware low latency wrapper for game launches
    call_script latencydevil
    # add earlyoom configuration, Fedora already has systemd-oomd
    call_script earlyoom
    # change intel driver to Xe on discrete GPUs
    call_script intelxe
    # fix GTK app rendering for Intel BMG and Nvidia GPUs
    call_script gtk-bmg-fix
    # add alive timeout fix for Gnome
    if echo "$XDG_CURRENT_DESKTOP" | grep -qi 'gnome'; then
        # Runs as the user on purpose: mutter reads the user's gsettings, and
        # a root-run gsettings would write root's dconf database (and try to
        # autolaunch a session bus, since sudo strips DBUS_SESSION_BUS_ADDRESS).
        gsettings set org.gnome.mutter check-alive-timeout 20000
    fi
    # full kernel preemption for better latency in Fedora -- will skip automatically in other OS
    call_script preemptfedora
    # enable x86_64v3 repositories on ubuntu
    call_script ubuntuv3
    # enable tcp_bbr if applicable
    call_script bbr
    # enable MTU probing
    call_script mtuprobe
}
# consolidated installation
optimizer () {
    export OPTIMIZER_RUN=1
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
    IDS=(standard)
    LABELS=("$defaultpwr")
    if ! is_zorin && ! is_cachy && ! is_suse; then
        IDS+=(laptop)
        LABELS+=("Laptop")
    fi
    CPU_VENDOR=$(awk -F ': *' '/^vendor_id/ { print $2; exit }' /proc/cpuinfo)
    if [[ "$CPU_VENDOR" == "AuthenticAMD" ]] && ! is_cachy; then
        IDS+=(performance)
        LABELS+=("$highperfpwr")
    fi
    IDS+=(cancel)
    LABELS+=("$msg070")

    CHOICE=$(radioselect --title "Power Optimizer" --text "$msg229" "${LABELS[@]}") || exit 100
    CHOICE_ID=""
    for i in "${!LABELS[@]}"; do
        if [[ "${LABELS[i]}" == "$CHOICE" ]]; then
            CHOICE_ID="${IDS[i]}"
            break
        fi
    done

    case "$CHOICE_ID" in
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
            printf 'Unexpected option returned by the menu: %q\n' "$CHOICE" >&2
            exit 1
            ;;
    esac
done
