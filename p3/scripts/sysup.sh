#!/bin/bash
# name: sysup
# description: sysup_desc
# icon: topgrade.svg
# revert: no
# compat: !ostree, !ublue

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
[ ! -n "$UPD_SERVICE" ] && sudo_rq

needs_reboot() {
    if is_fedora; then
        { [ "$UPD_SERVICE" = "1" ] && dnf needs-restarting -r; } || sudo dnf needs-restarting -r
    elif is_debian || is_ubuntu; then
        [ -f /var/run/reboot-required ]
    elif is_arch || is_cachy; then
        return 0 # no way of reliably checking for this on Arch-based distros, leave that to the user but always recommend it anyway
    elif is_suse; then
        sudo zypper needs-rebooting
    elif is_solus; then
        return 0 # no way of reliably checking for this on Solus, leave that to the user but always recommend it anyway
    fi
}
release_upgrade() {
    [ "$UPD_SERVICE" = "1" ] && return 1 # don't check for release upgrades if we're running as a background service
    if is_ubuntu; then
        { do-release-upgrade -c && return 0; } || return 1      
    elif is_fedora; then
        pkg_install jq
        fedora_version=$(curl -s https://fedoraproject.org/releases.json | jq -r '.[] | select(.version | test("Beta") | not) | .version' | sort -rn | head -1)
        if [[ -z "$fedora_version" ]]; then
            return 1  # Failed to fetch version info
        fi
        { [ "$VERSION_ID" != "$fedora_version" ] && return 0; } || return 1
    fi
}
offer_release_upgrade() {
    zenity --question --text="$sysup_available" --title="Release Upgrade" || return 1
}
notify_logged_users() {
    local message="$1"
    local notified=1
    command -v notify-send >/dev/null || return 1
    if command -v loginctl >/dev/null; then
        while read -r session_id _; do
            [[ -n "$session_id" ]] || continue

            local active state user uid runtime_dir bus_addr user_env display wayland
            active=$(loginctl show-session "$session_id" -p Active --value 2>/dev/null)
            state=$(loginctl show-session "$session_id" -p State --value 2>/dev/null)
            user=$(loginctl show-session "$session_id" -p Name --value 2>/dev/null)
            uid=$(loginctl show-session "$session_id" -p User --value 2>/dev/null)

            [[ "$active" = "yes" ]] || continue
            [[ "$state" = "active" ]] || continue
            [[ -n "$user" && -n "$uid" ]] || continue

            runtime_dir="/run/user/$uid"
            bus_addr="unix:path=$runtime_dir/bus"
            [[ -S "$runtime_dir/bus" ]] || continue

            user_env=$(sudo -u "$user" systemctl --user show-environment 2>/dev/null || true)
            display=$(printf '%s\n' "$user_env" | awk -F= '/^DISPLAY=/{print substr($0,9); exit}')
            wayland=$(printf '%s\n' "$user_env" | awk -F= '/^WAYLAND_DISPLAY=/{print substr($0,17); exit}')

            if sudo -u "$user" env \
                XDG_RUNTIME_DIR="$runtime_dir" \
                DBUS_SESSION_BUS_ADDRESS="$bus_addr" \
                DISPLAY="$display" \
                WAYLAND_DISPLAY="$wayland" \
                notify-send "$message" --icon=system-reboot --urgency=critical --app-name="LinuxToys Update"; then
                notified=0
            fi
        done < <(loginctl list-sessions --no-legend 2>/dev/null)
    fi

    if [ "$notified" -ne 0 ]; then
        while IFS=: read -r user _ uid _ _ _ _; do
            [[ "$uid" -ge 1000 ]] || continue
            [[ "$uid" -eq 65534 ]] && continue
            [[ -S "/run/user/$uid/bus" ]] || continue

            if sudo -u "$user" env \
                XDG_RUNTIME_DIR="/run/user/$uid" \
                DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" \
                notify-send "$message" --icon=system-reboot --urgency=critical --app-name="LinuxToys Update"; then
                notified=0
            fi
        done < /etc/passwd
    fi
    return "$notified"
}

echo "$sysup_starting"
if is_fedora; then
    { [ "$UPD_SERVICE" = "1" ] && dnf autoremove -y; } || sudo dnf autoremove -y || fatal "Failed to remove orphaned packages"
    { [ "$UPD_SERVICE" = "1" ] && dnf upgrade -y --setopt=throttle=2M; } || sudo dnf upgrade -y || fatal "Failed to upgrade packages"
    if release_upgrade; then
        if offer_release_upgrade; then
            sudo dnf system-upgrade download --releasever=$fedora_version -y || fatal "Failed to download Fedora $fedora_version upgrade"
            sudo dnf system-upgrade reboot || fatal "Failed to reboot for Fedora $fedora_version upgrade"
        fi
    fi
elif is_debian || is_ubuntu; then
    { [ "$UPD_SERVICE" = "1" ] && apt autoremove -y; } || fatal "Failed to remove orphaned packages"
    { [ "$UPD_SERVICE" = "1" ] && apt upgrade -y -o Acquire::http::Dl-Limit=2048 Acquire::https::Dl-Limit=2048; } || sudo apt upgrade -y || fatal "Failed to upgrade packages"
    if is_ubuntu && [[ "$ID" == "ubuntu" ]] && release_upgrade; then
        if offer_release_upgrade; then
            sudo do-release-upgrade || fatal "Failed to start Ubuntu release upgrade"
        fi
    fi
elif is_arch || is_cachy; then
    orphaned_packages=$(pacman -Qdtq 2>/dev/null || true)
    if [[ -n "$orphaned_packages" ]]; then
        sudo pacman -Rns --noconfirm $orphaned_packages || fatal "Failed to remove orphaned packages"
    fi
    sudo pacman -Syu --noconfirm || fatal "Failed to upgrade packages"
elif is_suse; then
    orphaned_packages=$(zypper packages --unneeded | awk '/^i/{print $5}')
    if [[ -n "$orphaned_packages" ]]; then
        sudo zypper rm --clean-deps $orphaned_packages -y || fatal "Failed to remove orphaned packages"
    fi
    sudo zypper dup -y || fatal "Failed to upgrade packages"
elif is_solus; then
    sudo eopkg rmo -y || fatal "Failed to remove orphaned packages"
    sudo eopkg up -y || fatal "Failed to upgrade packages"
fi
if which flatpak &> /dev/null; then
    { [ "$UPD_SERVICE" = "1" ] && flatpak uninstall --system --unused --delete-data -y; } || flatpak uninstall --unused --delete-data -y || fatal "Failed to remove orphaned flatpak packages"
    { [ "$UPD_SERVICE" = "1" ] && flatpak update --system -y; } || flatpak update -y || fatal "Failed to update flatpak packages"
fi
if needs_reboot; then
    if [ "$UPD_SERVICE" = "1" ]; then
        notify_logged_users "$sysup_rebootreq" || echo "$sysup_rebootreq"
    else
        zeninf "$sysup_rebootreq"
    fi
else
    { [ "$UPD_SERVICE" = "1" ] && echo "$sysup_completed"; } || zeninf "$sysup_completed"
fi
