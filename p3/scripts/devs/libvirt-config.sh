#!/bin/bash
# name: Virt Manager
# version: 1.1
# description: Install and configure libvirt and qemu.
# icon: virt-manager.png
# compat: ubuntu, debian, fedora, suse, arch, cachy, ostree, ublue
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

configure_libvirt() {
    if is_ubuntu || is_debian; then
        _packages=(qemu-kvm libvirt-daemon-system libvirt-clients virt-manager virt-viewer dnsmasq-base bridge-utils swtpm netcat-openbsd)
    elif is_fedora || is_ostree; then
        _packages=(qemu-kvm libvirt virt-install virt-manager virt-viewer dnsmasq bridge-utils swtpm nmap-ncat)
    elif is_suse; then
        _packages=(qemu-kvm libvirt libvirt-daemon virt-install virt-manager virt-viewer dnsmasq bridge-utils swtpm netcat-openbsd)
    elif is_arch || is_cachy; then
        _packages=(qemu-full virt-manager virt-viewer dnsmasq vde2 bridge-utils swtpm openbsd-netcat)
    else
        fatal "Unsupported distribution for this script."
    fi

    sudo_rq
    _install_

    # Add all regular users to libvirt group
    while IFS=: read -r user _ uid _; do
        if [ "$uid" -ge 1000 ] && [ "$user" != "nobody" ]; then
            sudo usermod -aG libvirt "$user" >/dev/null 2>&1 || true
        fi
    done < /etc/passwd

    # Enable/start legacy and modern libvirt daemons (first available wins)
    sudo systemctl enable --now libvirtd.service >/dev/null 2>&1 \
        || sudo systemctl enable --now virtqemud.service >/dev/null 2>&1 \
        || true
}

if [[ "$DISABLE_ZENITY" == "1" ]] || zenity --question --title "Libvirt Config" --text "This will install and configure libvirt + qemu for your distro. Proceed?" --width 420 --height 300; then
    configure_libvirt
    zeninf "Libvirt and QEMU setup completed. You may need to log out and log in again for group changes to apply."
    exit 0
fi
