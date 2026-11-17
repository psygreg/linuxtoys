#!/bin/bash
# name: sysup
# description: sysup_desc
# icon: topgrade.svg
# revert: no
# registry: no

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
[ ! -n "$UPD_SERVICE" ] && sudo_rq

needs_reboot() {
    if is_ostree || is_ublue || is_gregos; then
        # rpm-ostree stages a new deployment that only takes effect on reboot.
        # The 'staged' flag marks the deployment queued to boot next.
        local status_json
        if [ "$UPD_SERVICE" = "1" ]; then
            status_json=$(rpm-ostree status --json 2>/dev/null)
        else
            status_json=$(sudo_ rpm-ostree status --json 2>/dev/null)
        fi
        printf '%s' "$status_json" | grep -q '"staged"[[:space:]]*:[[:space:]]*true'
        return $?
    elif is_fedora || is_rhel; then
        # 'dnf needs-restarting -r' exits 0 when NO reboot is required and 1 when
        # a reboot IS required. Treat "reboot required" as a recommendation to
        # return 0 (reboot recommended), matching the other branches below.
        if [ "$UPD_SERVICE" = "1" ]; then
            dnf needs-restarting -r >/dev/null 2>&1
        else
            sudo_ dnf needs-restarting -r >/dev/null 2>&1
        fi
        # $? holds the dnf exit code: 0 = no reboot needed, 1 = reboot required.
        if [ $? -eq 1 ]; then
            return 0  # reboot required
        else
            return 1  # no reboot required
        fi
    elif is_debian || is_ubuntu; then
        [ -f /var/run/reboot-required ]
    elif is_arch || is_cachy || is_manjaro; then
        return 0 # no way of reliably checking for this on Arch-based distros, leave that to the user but always recommend it anyway
    elif is_suse; then
        sudo_ zypper needs-rebooting
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
    question "Release Upgrade" "$sysup_available" || return 1
}

# Update Flatpak packages for one installation ($1: --user or --system, $2: "sudo" to elevate).
# Package refs are updated explicitly instead of a bare 'flatpak update': without REFs,
# flatpak also refreshes appstream metadata for every configured remote in one pass and
# fails wholesale — reporting a misleading "No such ref 'appstream2/...'" — when a single
# stale or unreachable remote breaks, masking the package updates that did succeed.
# Metadata is instead refreshed per remote afterwards, best-effort.
flatpak_update_installation() {
    local scope="$1" elevated="$2"
    local update_cmd=(flatpak update "$scope")
    local appstream_cmd=(flatpak update "$scope" --appstream)
    if [ "$elevated" = "sudo" ]; then
        update_cmd=(sudo_ "${update_cmd[@]}")
        appstream_cmd=(sudo_ "${appstream_cmd[@]}")
    fi

    local refs=()
    mapfile -t refs < <(flatpak list "$scope" --app --runtime --columns=application 2>/dev/null)
    if ((${#refs[@]})); then
        "${update_cmd[@]}" -y "${refs[@]}" || warn "Failed to upgrade Flatpaks"
    fi

    local remote
    while IFS= read -r remote; do
        [ -n "$remote" ] || continue
        "${appstream_cmd[@]}" "$remote" 2>/dev/null ||
            warn "Failed to update appstream metadata for Flatpak remote $remote"
    done < <(flatpak remotes "$scope" --columns=name 2>/dev/null)
}

# Update Homebrew formulae when Homebrew is installed. 'brew update' refreshes
# the formula metadata, then 'brew upgrade' upgrades every installed formula.
# Homebrew lives in the user's prefix and needs no elevation. Best-effort: a
# failure here should not abort the rest of the system update.
brew_update() {
    local brew_bin
    brew_bin=$(_brew_executable) || return 0
    "$brew_bin" update || { warn "Failed to refresh Homebrew metadata"; return 0; }
    "$brew_bin" upgrade -y || warn "Failed to upgrade Homebrew formulae"
}

# Update global Bun packages (bun install -g) for the invoking user. They live in
# the user's own Bun prefix, so this never runs as root: a root service run would
# update /root instead. Services start with a minimal PATH, so bun is also looked
# up where pkg_bun and Homebrew install it. Best-effort, like brew_update.
bun_update() {
    [ "$(id -u)" -ne 0 ] || return 0
    local bun_bin="" candidate
    for candidate in "$(type -P bun)" "${BUN_INSTALL:+$BUN_INSTALL/bin/bun}" "$HOME/.bun/bin/bun" \
        /home/linuxbrew/.linuxbrew/bin/bun "$HOME/.linuxbrew/bin/bun"; do
        if [[ -n "$candidate" && -x "$candidate" ]]; then
            bun_bin=$candidate
            break
        fi
    done
    [[ -n "$bun_bin" ]] || return 0
    # bun exits 1 when no global packages were ever installed; that is not a failure.
    [[ -f "${BUN_INSTALL:-$HOME/.bun}/install/global/package.json" ]] || return 0
    "$bun_bin" update -g || warn "Failed to upgrade global Bun packages"
}

if [ "$UPD_SERVICE" = "1" ] && [ "$(id -u)" -ne 0 ]; then
    flatpak uninstall --user --unused --delete-data -y || warn "Failed to remove orphaned user Flatpaks"
    flatpak_update_installation --user ""
    brew_update
    bun_update
    cleanup_orphan_desktops
    echo "$sysup_completed"
    exit 0
fi

echo "$sysup_starting"

# The native package-manager transactions below (rpm-ostree, dnf, apt, pacman,
# pamac, zypper, eopkg) are the one part of a system update that must not be
# interrupted: a Ctrl+C or a navigation away mid-transaction can leave the
# manager's databases or the system itself in a broken state. Hold the runner
# navigation lock for the whole distro branch so the terminal runner disables
# input (including Ctrl+C) and the Back button until the transactions finish.
# A run that dies inside the section is covered by the runner's on_child_exit,
# which always clears the lock. Only user-driven runs may take it: background
# service runs (UPD_SERVICE=1) have no terminal runner to honor the lock, and
# runner_lock's lazy CachyOS mirror preflight can exit a run outright on a
# failed ranking — an unattended update must never die mid-script from that.
# Outside the runner (LINUXTOYS_RUNNER_STATE unset) the lock is a no-op, so
# plain CLI launches are unaffected.
[ "$UPD_SERVICE" != "1" ] && runner_lock "package-transaction" ""
if is_steamos; then
    # SteamOS-style immutables manage their packages through the OS image, so
    # there is nothing to do here. Flatpaks, Homebrew and git apps still update.
    :
elif is_ostree || is_ublue || is_gregos; then
    # rpm-ostree based immutables: pull and stage a new deployment. The staged
    # deployment is applied on the next reboot (see needs_reboot below).
    if [ "$UPD_SERVICE" = "1" ]; then
        rpm_ostree_transaction rpm-ostree update || fatal "Failed to update system image"
    else
        rpm_ostree_transaction sudo_ rpm-ostree update || fatal "Failed to update system image"
    fi
elif is_fedora || is_rhel; then
    if [ "$UPD_SERVICE" = "1" ]; then
        dnf_transaction dnf autoremove -y || die "Failed to remove orphaned packages"
        dnf_transaction dnf clean all || die "Failed to remove orphaned packages"
        dnf_transaction dnf -y makecache --refresh || die "Failed to remove orphaned packages"
    else
        dnf_transaction sudo_ dnf autoremove -y || die "Failed to remove orphaned packages"
        dnf_transaction sudo_ dnf clean all || die "Failed to remove orphaned packages"
        dnf_transaction sudo_ dnf -y makecache --refresh || die "Failed to remove orphaned packages"
    fi
    if [ "$UPD_SERVICE" = "1" ]; then
        dnf_transaction dnf --refresh upgrade --best --allowerasing -y --setopt=throttle=2M || fatal "Failed to upgrade packages"
    else
        dnf_transaction sudo_ dnf --refresh upgrade --best --allowerasing -y || fatal "Failed to upgrade packages"
    fi
    is_fedora && { release_upgrade &&
            if offer_release_upgrade; then
                dnf_transaction sudo_ dnf system-upgrade download --releasever=$fedora_version --best --allowerasing -y || fatal "Failed to download Fedora $fedora_version upgrade"
                dnf_transaction sudo_ dnf system-upgrade reboot || fatal "Failed to reboot for Fedora $fedora_version upgrade"
            fi
    }
elif is_debian || is_ubuntu; then
    interrupted_apt_guard
    if { [ "$UPD_SERVICE" = "1" ] && apt-get -s autoremove 2>/dev/null | grep -q '^Remv '; } || sudo_ apt-get -s autoremove 2>/dev/null | grep -q '^Remv '; then
        if [ "$UPD_SERVICE" = "1" ]; then
            apt_transaction apt-get autoremove -y || fatal "Failed to remove orphaned packages"
        else
            apt_transaction sudo_ apt-get autoremove -y || fatal "Failed to remove orphaned packages"
        fi
    fi
    if [ "$UPD_SERVICE" = "1" ]; then
        apt_transaction apt-get upgrade -y --allow-downgrades -o Acquire::http::Dl-Limit=2048 -o Acquire::https::Dl-Limit=2048 || fatal "Failed to upgrade packages"
    else
        apt_transaction sudo_ apt-get upgrade -y --allow-downgrades || fatal "Failed to upgrade packages"
    fi
    if is_ubuntu && [[ "$ID" == "ubuntu" ]] && release_upgrade; then
        if offer_release_upgrade; then
            # do-release-upgrade runs through sudo_, whose env_reset strips
            # DISPLAY, so it falls back to its interactive text frontend and
            # needs terminal input. Release the navigation lock for it: the
            # upgrade was explicitly chosen through the dialog above, and a
            # locked terminal could never answer its prompts. The unlock after
            # the distro branch tolerates the already-released depth.
            [ "$UPD_SERVICE" != "1" ] && runner_unlock
            sudo_ do-release-upgrade || fatal "Failed to start Ubuntu release upgrade"
        fi
    fi
elif { is_arch || is_cachy; } && ! is_manjaro; then
    pacman_lock_guard
    orphaned_packages=$(pacman -Qdtq 2>/dev/null || true)
    if [[ -n "$orphaned_packages" ]]; then
        # Orphan removal runs under the runner lock, where terminal input is
        # disabled: auto-confirm like every other branch's removal (dnf/apt
        # autoremove, zypper rm, pamac --no-confirm), otherwise the run sits
        # forever on pacman's ":: Do you want to remove these packages?".
        pacman_transaction sudo_ pacman -Rns --noconfirm $orphaned_packages || fatal "Failed to remove orphaned packages"
    fi
    if [ "$ID" = "omarchy" ]; then
        omarchy-update -y
    else
        pacman_transaction sudo_ pacman -Syu --noconfirm --overwrite '*' || fatal "Failed to upgrade packages"
    fi
elif is_manjaro; then
    pacman_lock_guard
    pacman_transaction pamac remove --orphans --no-confirm || fatal "Failed to remove orphaned packages"
    pacman_transaction pamac update --no-confirm || fatal "Failed to upgrade packages"
elif is_suse; then
    mapfile -t orphaned_packages < <(
        zypper --xmlout packages --unneeded 2>/dev/null |
        sed -n 's/.*<solvable[^>]*name="\([^"]*\)".*/\1/p'
    )
    if (( ${#orphaned_packages[@]} )); then
        zypper_transaction sudo_ zypper -n rm --clean-deps "${orphaned_packages[@]}" || die "Failed to remove orphaned packages"
    fi
    zypper_transaction sudo_ zypper dup --no-recommends --auto-agree-with-licenses -y || fatal "Failed to upgrade packages"
elif is_solus; then
    if [ "$UPD_SERVICE" = "1" ]; then
        eopkg_transaction eopkg rmo -y || fatal "Failed to remove orphaned packages"
        eopkg_transaction eopkg up -y || fatal "Failed to upgrade packages"
    else
        eopkg_transaction sudo_ eopkg rmo -y || fatal "Failed to remove orphaned packages"
        eopkg_transaction sudo_ eopkg up -y || fatal "Failed to upgrade packages"
    fi
fi
# Release the navigation lock before the interruptible remainder: Flatpak,
# Snap, Homebrew and app updates are atomic or re-runnable. runner_unlock at
# depth zero is a no-op, so this also covers the Ubuntu release-upgrade path
# that already released the lock inside the branch above.
[ "$UPD_SERVICE" != "1" ] && runner_unlock

if command -v flatpak >/dev/null 2>&1; then
    if [ "$UPD_SERVICE" = "1" ]; then
        # Root context (background service). No --delete-data here or in the
        # sudo_ call below: --unused only removes runtimes, which own no
        # ~/.var/app data and no permission-store entries, so there is nothing
        # for it to delete; worse, --delete-data makes flatpak connect to the
        # session bus to reset portal permissions (org.freedesktop.impl.portal
        # .PermissionStore) and no session bus exists in this branch — the
        # uninstall would exit 1 right after the transaction completed.
        flatpak uninstall --system --unused -y || warn "Failed to remove orphaned system Flatpaks"
        flatpak_update_installation --system ""
    else
        flatpak uninstall --user --unused --delete-data -y || warn "Failed to remove orphaned user Flatpaks"
        flatpak_update_installation --user ""

        # Elevated flatpak must not use --delete-data either: sudo_ forwards
        # the desktop session's DBUS_SESSION_BUS_ADDRESS, and --delete-data
        # makes flatpak connect to the user's portal permission store over
        # that bus as root. The user's message bus only accepts connections
        # from that user, so it resets the root client's connection and
        # flatpak exits 1 with "error: Error receiving data: Connection reset
        # by peer" AFTER the uninstall transaction already completed — a
        # successful cleanup misreported as a failure. --delete-data would
        # also target root's $HOME here, not the invoking user's. The --user
        # pass above keeps it: it runs inside the user's session, where both
        # the data and the permission store are reachable.
        sudo_ flatpak uninstall --system --unused -y || warn "Failed to remove orphaned system Flatpaks"
        flatpak_update_installation --system sudo
    fi
fi
if command -v snap >/dev/null 2>&1 && command -v snapd >/dev/null 2>&1; then
    { [ "$UPD_SERVICE" = "1" ] && snap refresh; } || sudo_ snap refresh || warn "Failed to upgrade snap packages"
fi

# Drop leftover user menu launchers whose Flatpak/Snap/native targets were
# removed earlier in this update (or by previous uninstalls). Best-effort.
cleanup_orphan_desktops

# Update Homebrew formulae on any system where Homebrew is installed.
brew_update

# Update global Bun packages on any system where Bun is installed.
bun_update

# Update applications installed directly from GitHub/Codeberg releases through
# repository-list pkg_fromrelease transactions. A changed stable tag is enough;
# release tags are not assumed to follow semantic-version ordering.
if [[ "$UPD_SERVICE" != "1" ]] && git_app_versions; then
    for app in "${GIT_APPS[@]}"; do
        version_var="GIT_${app}_VERSION"
        repo_var="GIT_${app}_REPO"
        installed_version="${!version_var}"
        release_repo="${!repo_var}"

        latest_version=$(latest_release_version "$release_repo") || {
            warn "Failed to check release updates for $app"
            continue
        }

        if [[ "$latest_version" != "$installed_version" ]]; then
            echo "Updating $app: $installed_version -> $latest_version"
            # call_script dies (exiting the whole run) when nothing offers the app
            # any more. The subshell confines that to this app's warning.
            ( call_script "$app" ) || warn "Failed to update $app"
        fi
    done
fi

# Update AppImages installed from the AppImage catalog. Tracked apps record the
# resolved release (id, tag, repository) at install time; a changed stable tag
# from the same repository is enough to trigger a refresh. Tags are compared
# literally and are not assumed to follow semantic-version ordering.
if [[ "$UPD_SERVICE" != "1" ]] && appimage_app_versions; then
    for app in "${APPIMAGE_APPS[@]}"; do
        safe_app=$(printf '%s' "$app" | tr -c 'A-Za-z0-9_' '_')
        version_var="APPIMAGE_${safe_app}_VERSION"
        repo_var="APPIMAGE_${safe_app}_REPO"
        installed_version="${!version_var}"
        release_repo="${!repo_var}"
        [[ -n "$release_repo" ]] || continue

        latest_version=$(latest_release_version "$release_repo") || {
            warn "Failed to check release updates for $app"
            continue
        }

        if [[ "$latest_version" != "$installed_version" ]]; then
            echo "Updating $app: $installed_version -> $latest_version"
            pkg_appimage_update "$app" "$release_repo" "$installed_version" || warn "Failed to update $app"
        fi
    done
fi

if needs_reboot; then
    if [ "$UPD_SERVICE" = "1" ]; then
        echo "$sysup_rebootreq"
    else
        zeninf "$sysup_rebootreq"
    fi
else
    { [ "$UPD_SERVICE" = "1" ] && echo "$sysup_completed"; } || zeninf "$sysup_completed"
fi
