#!/bin/bash
# name: psaver
# version: 1.0
# description: psaver_desc
# icon: psaver.svg
# reboot: yes
# nocontainer
# repo: https://thealexdev23.github.io/power-options/
# optimized-only: yes
# compat: fedora, rhel, ubuntu, debian, arch
# systemd: yes

# --- Start of the script code ---
if [ ! -f "$HOME/.local/.autopatch.state" ]; then
    prep_tmp
    askpass
    { ( pkg_exists tlp power-profiles-daemon && [ -n "$pkg_found" ] ) && zenwrn "OS already has TLP/power-profiles-daemon. Skipping power-options..." && return 100; } || true
    if is_fedora || is_rhel; then
        sudo dnf config-manager addrepo --from-repofile=https://files.distropack.dev/rpm_repo/TheAlexDev23/power-options
        pkg_install power-options-gtk power-options-tray
    elif is_arch; then
        pkg_install power-options-gtk power-options-tray
    elif is_ubuntu || is_debian; then
        echo 'deb https://files.distropack.dev/download/TheAlexDev23/power-options/deb /' | sudo tee /etc/apt/sources.list.d/distropack_TheAlexDev23_power-options.list
        curl -fsSL 'https://files.distropack.dev/pubkey?user=TheAlexDev23&project=power-options' | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/distropack_TheAlexDev23_power-options.gpg > /dev/null
        sudo apt update
        pkg_install power-options-gtk power-options-tray
    fi
else
    warn "$msg234"
    exit 100
fi