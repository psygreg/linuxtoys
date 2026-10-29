#!/bin/bash
# name: FlatPark
# version: 1.0
# description: flatpark_desc
# icon: flatpark.svg
# repo: https://flatpark.org
# compat: !solus
# systemd: yes

# --- Start of the script code ---
sysdetect

repair_flatpark_remote() {
    local scope="$1"
    local sudo_cmd=()
    [ "$scope" = "--system" ] && sudo_cmd=(sudo)

    if "${sudo_cmd[@]}" flatpak "$scope" remotes --columns=name 2>/dev/null \
        | grep -qx flatpark; then

        if ! "${sudo_cmd[@]}" flatpak "$scope" remote-ls flatpark &>/dev/null; then
            "${sudo_cmd[@]}" flatpak "$scope" remote-delete --force flatpark || return 1
            "${sudo_cmd[@]}" flatpak "$scope" remote-add \
                flatpark \
                "https://dl.flatpark.org/flatpark.flatpakrepo" || return 1
        fi
    else
        "${sudo_cmd[@]}" flatpak "$scope" remote-add \
            flatpark \
            "https://dl.flatpark.org/flatpark.flatpakrepo" || return 1
    fi
}

# The marker records that a bootstrap configured FlatPark during this session,
# so call_script flatpark stays idempotent. As with Flathub, it is not proof
# the configuration still works: manual runs re-verify and repair below.
flatpark_already_ready=0
if [ -f /tmp/linuxtoys_flatpark_done ]; then
    if [ -n "${CALLED_SCRIPT:-}" ]; then
        if flatpak remotes --columns=name 2>/dev/null | grep -qx flatpark &&
           flatpak remote-ls flatpark &>/dev/null; then
            exit 0
        fi
    else
        echo "FlatPark support was configured earlier in this session; re-checking..."
        flatpark_already_ready=1
    fi
fi

# FlatPark's runtimes live on Flathub, so its bootstrap runs first: it installs
# Flatpak when missing, repairs both Flathub scopes and sets the session
# markers. A failed Flathub preparation is not fatal here -- the FlatPark
# remotes are configured below and Flatpak itself resolves runtimes from any
# reachable configured remote -- but a real network failure surfaces on it.
call_script flathub
if ! command -v flatpak &>/dev/null; then
    pkg_install flatpak
    sysd_start flatpak-system-helper.service
fi

# Prefer a user-level FlatPark remote, but fall back to system-level. An app
# installed system-wide needs the remotes added system-wide too, so both
# scopes are configured whenever possible.
if ! repair_flatpark_remote --user; then
    warn "Failed to configure FlatPark userlevel remote"
    if ! repair_flatpark_remote --system; then
        die "Failed to configure FlatPark remotes"
    fi
else
    repair_flatpark_remote --system || die "Failed to configure FlatPark systemlevel remote"
fi

# Mark the session only after the configuration actually succeeded.
touch /tmp/linuxtoys_flatpark_done
# The AppStream source universe changed: the next catalog check rebuilds
# against the newly available FlatPark source.
rm -f "$HOME/.cache/linuxtoys/appstream/state.json"

zeninf "$finishmsg"
