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

# The marker records that a bootstrap configured Flathub during this session,
# so call_script bootstraps stay idempotent. It is not proof the configuration
# still works: a failed run, a broken remote or a cleaned /tmp must not make a
# manual run exit silently. Manual runs therefore re-verify and repair below,
# and always report what they did.
flathub_already_ready=0
if [ -f /tmp/linuxtoys_flatpak_done ]; then
    if [ -n "${CALLED_SCRIPT:-}" ]; then
        if flatpak remotes --columns=name 2>/dev/null | grep -qx flathub &&
           flatpak remote-ls flathub &>/dev/null; then
            exit 0
        fi
    else
        echo "Flathub support was configured earlier in this session; re-checking..."
        flathub_already_ready=1
    fi
fi

askpass
# fix for MODICIA OS, issue #1407
if [ -f /etc/apt/preferences.d/noflatpak-nosnap.pref ]; then
    prep_rm /etc/apt/preferences.d/noflatpak-nosnap.pref
fi
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

# Mark the session only after the configuration actually succeeded.
touch /tmp/linuxtoys_flatpak_done

# First-time Flathub setup exposes Flatpak's app-export paths and the desktop
# menu cache that the current session has not loaded yet. Flag it so the
# checklist reboot/session-refresh prompt can tell the user to log out and back
# in (or reboot) for newly installed Flatpak apps to appear. A re-verify of an
# already-working Flathub does not need it.
if [ "$flathub_already_ready" -eq 0 ]; then
    touch /tmp/flatpak_path_pending
fi

zeninf "$finishmsg"
