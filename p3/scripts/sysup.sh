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
    zenity --question --text="$sysup_available" --title="Release Upgrade" || return 1
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
    "$brew_bin" upgrade || warn "Failed to upgrade Homebrew formulae"
}

if [ "$UPD_SERVICE" = "1" ] && [ "$(id -u)" -ne 0 ]; then
    flatpak uninstall --user --unused --delete-data -y || warn "Failed to remove orphaned user Flatpaks"
    flatpak_update_installation --user ""
    brew_update
    echo "$sysup_completed"
    exit 0
fi

echo "$sysup_starting"
if is_steamos; then
    # SteamOS-style immutables manage their packages through the OS image, so
    # there is nothing to do here. Flatpaks, Homebrew and git apps still update.
    :
elif is_ostree || is_ublue || is_gregos; then
    # rpm-ostree based immutables: pull and stage a new deployment. The staged
    # deployment is applied on the next reboot (see needs_reboot below).
    { [ "$UPD_SERVICE" = "1" ] && rpm-ostree update; } || sudo_ rpm-ostree update || fatal "Failed to update system image"
elif is_fedora || is_rhel; then
    { { [ "$UPD_SERVICE" = "1" ] && dnf autoremove -y && dnf clean all && dnf -y makecache --refresh; } || \
        { sudo_ dnf autoremove -y && sudo_ dnf clean all && sudo_ dnf -y makecache --refresh; }; } || die "Failed to remove orphaned packages"
    { [ "$UPD_SERVICE" = "1" ] && dnf --refresh upgrade -y --setopt=throttle=2M; } || sudo_ dnf --refresh upgrade -y || fatal "Failed to upgrade packages"
    is_fedora && { release_upgrade &&
            if offer_release_upgrade; then
                sudo_ dnf system-upgrade download --releasever=$fedora_version -y || fatal "Failed to download Fedora $fedora_version upgrade"
                sudo_ dnf system-upgrade reboot || fatal "Failed to reboot for Fedora $fedora_version upgrade"
            fi
    }
elif is_debian || is_ubuntu; then
    interrupted_apt_guard
    if { [ "$UPD_SERVICE" = "1" ] && apt-get -s autoremove 2>/dev/null | grep -q '^Remv '; } || sudo_ apt-get -s autoremove 2>/dev/null | grep -q '^Remv '; then
        { [ "$UPD_SERVICE" = "1" ] && apt-get autoremove -y; } || sudo_ apt-get autoremove -y || fatal "Failed to remove orphaned packages"
    fi
    { [ "$UPD_SERVICE" = "1" ] && apt-get upgrade -y --allow-downgrades -o Acquire::http::Dl-Limit=2048 -o Acquire::https::Dl-Limit=2048; } || sudo_ apt-get upgrade -y --allow-downgrades || fatal "Failed to upgrade packages"
    if is_ubuntu && [[ "$ID" == "ubuntu" ]] && release_upgrade; then
        if offer_release_upgrade; then
            sudo_ do-release-upgrade || fatal "Failed to start Ubuntu release upgrade"
        fi
    fi
elif { is_arch || is_cachy; } && ! is_manjaro; then
    pacman_lock_guard
    orphaned_packages=$(pacman -Qdtq 2>/dev/null || true)
    if [[ -n "$orphaned_packages" ]]; then
        sudo_ pacman -Rns $orphaned_packages || fatal "Failed to remove orphaned packages"
    fi
    if [ "$ID" = "omarchy" ]; then
        omarchy-update -y
    else
        sudo_ pacman -Syu --noconfirm || fatal "Failed to upgrade packages"
    fi
elif is_manjaro; then
    pamac remove --orphans --no-confirm || fatal "Failed to remove orphaned packages"
    pamac update --no-confirm || fatal "Failed to upgrade packages"
elif is_suse; then
    mapfile -t orphaned_packages < <(
        zypper --xmlout packages --unneeded 2>/dev/null |
        sed -n 's/.*<solvable[^>]*name="\([^"]*\)".*/\1/p'
    )
    if (( ${#orphaned_packages[@]} )); then
        sudo_ zypper -n rm --clean-deps "${orphaned_packages[@]}" || die "Failed to remove orphaned packages"
    fi
    sudo_ zypper dup --no-recommends -y || fatal "Failed to upgrade packages"
elif is_solus; then
    { [ "$UPD_SERVICE" = "1" ] && eopkg rmo -y; } || sudo_ eopkg rmo -y || fatal "Failed to remove orphaned packages"
    { [ "$UPD_SERVICE" = "1" ] && eopkg up -y; } || sudo_ eopkg up -y || fatal "Failed to upgrade packages"
fi

if command -v flatpak >/dev/null 2>&1; then
    if [ "$UPD_SERVICE" = "1" ]; then
        flatpak uninstall --system --unused --delete-data -y || warn "Failed to remove orphaned system Flatpaks"
        flatpak_update_installation --system ""
    else
        flatpak uninstall --user --unused --delete-data -y || warn "Failed to remove orphaned user Flatpaks"
        flatpak_update_installation --user ""

        sudo_ flatpak uninstall --system --unused --delete-data -y || warn "Failed to remove orphaned system Flatpaks"
        flatpak_update_installation --system sudo
    fi
fi
if command -v snap >/dev/null 2>&1 && command -v snapd >/dev/null 2>&1; then
    { [ "$UPD_SERVICE" = "1" ] && snap refresh; } || sudo_ snap refresh || warn "Failed to upgrade snap packages"
fi

# Update Homebrew formulae on any system where Homebrew is installed.
brew_update

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
            call_script "$app" || warn "Failed to update $app"
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
