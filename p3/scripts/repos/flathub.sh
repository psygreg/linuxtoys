#!/bin/bash
# name: Flathub
# version: 1.0
# description: flat_desc
# icon: flathub.svg
# reboot: yes
# repo: https://flathub.org
# compat: !solus, !ostree
# systemd: yes

# --- Start of the script code ---
sysdetect

repair_flathub_remote() {
    local scope="$1"
    local sudo_cmd=()
    [ "$scope" = "--system" ] && sudo_cmd=(sudo)

    if "${sudo_cmd[@]}" flatpak "$scope" remotes --columns=name 2>/dev/null \
        | grep -qx flathub; then

        if ! "${sudo_cmd[@]}" flatpak "$scope" remote-ls flathub &>/dev/null; then
            "${sudo_cmd[@]}" flatpak "$scope" remote-delete --force flathub || return 1
            "${sudo_cmd[@]}" flatpak "$scope" remote-add \
                flathub \
                "https://dl.flathub.org/repo/flathub.flatpakrepo" || return 1
        fi
    else
        "${sudo_cmd[@]}" flatpak "$scope" remote-add \
            flathub \
            "https://dl.flathub.org/repo/flathub.flatpakrepo" || return 1
    fi
}

[ -f /tmp/linuxtoys_flatpak_done ] && exit 0

askpass
if ! command -v flatpak &>/dev/null; then
    pkg_install flatpak
    sysd_start flatpak-system-helper.service
fi

# Prefer a user-level Flathub remote, but fall back to system-level.
if ! repair_flathub_remote --user; then
    warn "Failed to configure Flathub userlevel remote"
    if ! repair_flathub_remote --system; then
        die "Failed to configure Flathub remotes"
    fi
else
    repair_flathub_remote --system || die "Failed to configure Flathub systemlevel remote"
fi

touch /tmp/linuxtoys_flatpak_done
[ -n "$flatpak_path_pending" ] && touch /tmp/flatpak_path_pending
zeninf "$finishmsg"