#!/usr/bin/env bash
# name: DaVinci Resolve AAC Bridge
# version: 1.0
# description: resolveaac_desc
# icon: resolve.svg
# repo: https://github.com/GloriousEggroll/dvcp-aac
# compat: ubuntu, debian, fedora, arch, cachy, rhel, suse

# --- Start of the script code ---

RELEASE_URL="https://github.com/GloriousEggroll/dvcp-aac/releases/latest/download/aac-plugin-release.tar.gz"
ARCHIVE="aac-plugin-release.tar.gz"
CONTAINER="davincibox"
RESOLVE_ROOT="/opt/resolve"

check_arch() {
    case "$(uname -m)" in
        x86_64|amd64) ;;
        *) fatal "This package targets Linux x86-64." ;;
    esac
}

check_resolve_stopped_local() {
    python3 - "$RESOLVE_ROOT" <<'PY'
import os
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
resolve = root / "bin/resolve"

for item in Path("/proc").iterdir():
    if not item.name.isdigit():
        continue

    try:
        exe = os.readlink(item / "exe")
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue

    if exe.endswith(" (deleted)"):
        exe = exe[:-10]

    try:
        running = Path(exe).resolve()
    except OSError:
        continue

    if running == resolve:
        raise SystemExit(
            "DaVinci Resolve is currently running. "
            "Save your work and fully quit Resolve first."
        )
PY

    [ $? -eq 0 ] || fatal \
        "DaVinci Resolve is currently running. Save your work and fully quit Resolve first."
}

check_resolve_stopped_distrobox() {
    local container="$1"

    distrobox enter "$container" -- python3 - "$RESOLVE_ROOT" <<'PY'
import os
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
resolve = root / "bin/resolve"

for item in Path("/proc").iterdir():
    if not item.name.isdigit():
        continue

    try:
        exe = os.readlink(item / "exe")
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue

    if exe.endswith(" (deleted)"):
        exe = exe[:-10]

    try:
        running = Path(exe).resolve()
    except OSError:
        continue

    if running == resolve:
        raise SystemExit(
            "DaVinci Resolve is currently running. "
            "Save your work and fully quit Resolve first."
        )
PY

    [ $? -eq 0 ] || fatal \
        "DaVinci Resolve is currently running in $container. Save your work and fully quit Resolve first."
}

find_release_root() {
    local base="$1"
    local installer

    installer=$(find "$base" -type f -name install.py -print -quit)

    [ -n "$installer" ] \
        || fatal "The AAC plugin release does not contain install.py."

    dirname "$installer"
}

install_bundle_local() {
    local source="$1"
    local bundle="$2"
    local target="$RESOLVE_ROOT/IOPlugins/$bundle"

    [ -d "$source" ] || return 0

    # Match upstream's refusal to replace a symlink.
    [ ! -L "$target" ] \
        || fatal "Refusing to replace a symlink: $target"

    prep_dir_edit "$target"

    sudo_ rm -rf -- "$target" \
        || fatal "Failed to replace $bundle."

    move_ "$source" "$target" \
        || fatal "Failed to install $bundle."
}

install_bundle_distrobox() {
    local container="$1"
    local source="$2"
    local bundle="$3"
    local target="$RESOLVE_ROOT/IOPlugins/$bundle"

    distrobox enter "$container" -- test -d "$source" \
        || return 0

    if distrobox enter "$container" -- test -L "$target"; then
        fatal "Refusing to replace a symlink: $target"
    fi

    distrobox_prep_dir_edit "$container" "$target"

    distrobox enter "$container" -- rm -rf -- "$target" 2>/dev/null \
        || distrobox enter "$container" -- sudo rm -rf -- "$target" \
        || fatal "Failed to replace $bundle in $container."

    distrobox_move_ "$container" "$source" "$target" \
        || fatal "Failed to install $bundle in $container."
}

install_nobox() {
    check_arch

    [ -f "$RESOLVE_ROOT/bin/resolve" ] \
        || fatal "DaVinci Resolve is not currently installed in this computer."

    check_resolve_stopped_local

    prep_tmp_noram

    rm -rf aac-plugin-release "$ARCHIVE"

    wget -O "$ARCHIVE" "$RELEASE_URL" \
        || fatal "Failed to download AAC plugin release."

    mkdir -p aac-plugin-release \
        || fatal "Failed to create AAC plugin extraction directory."

    tar -xzf "$ARCHIVE" -C aac-plugin-release \
        || fatal "Failed to extract AAC plugin release."

    local release_root
    release_root=$(find_release_root "$PWD/aac-plugin-release")

    # Preserve upstream package-integrity and Resolve compatibility checks.
    (
        cd "$release_root" \
            && python3 ./install.py check --root "$RESOLVE_ROOT"
    ) || fatal "AAC plugin package or DaVinci Resolve compatibility check failed."

    # Check again immediately before modifying Resolve, matching upstream's
    # second stopped() check before committing the installation.
    check_resolve_stopped_local

    prep_dir "$RESOLVE_ROOT/IOPlugins"

    install_bundle_local \
        "$release_root/aac_decoder_probe.dvcp.bundle" \
        "aac_decoder_probe.dvcp.bundle"

    install_bundle_local \
        "$release_root/aac_fdk_plugin.dvcp.bundle" \
        "aac_fdk_plugin.dvcp.bundle"
}

install_dvbox() {
    check_arch

    distrobox enter "$CONTAINER" -- test -f "$RESOLVE_ROOT/bin/resolve" \
        || fatal "DaVinci Resolve is not currently installed in DaVinciBox."

    check_resolve_stopped_distrobox "$CONTAINER"

    # Keep the release entirely inside the container. /opt/resolve is not
    # bind-mounted, so installation and validation must operate on the
    # container's own filesystem.
    local workdir="/tmp/linuxtoys-dvcp-aac-$$"

    distrobox enter "$CONTAINER" -- rm -rf -- "$workdir" 2>/dev/null || true

    distrobox enter "$CONTAINER" -- mkdir -p "$workdir/release" \
        || fatal "Failed to create temporary AAC plugin directory in DaVinciBox."

    distrobox enter "$CONTAINER" -- \
        wget -O "$workdir/$ARCHIVE" "$RELEASE_URL" \
        || fatal "Failed to download AAC plugin release in DaVinciBox."

    distrobox enter "$CONTAINER" -- \
        tar -xzf "$workdir/$ARCHIVE" -C "$workdir/release" \
        || fatal "Failed to extract AAC plugin release in DaVinciBox."

    local release_root
    release_root=$(
        distrobox enter "$CONTAINER" -- \
            find "$workdir/release" -type f -name install.py -print -quit
    )

    [ -n "$release_root" ] \
        || fatal "The AAC plugin release does not contain install.py."

    release_root="${release_root%/install.py}"

    # Run upstream's package and Resolve compatibility checks against the
    # Resolve installation that actually exists inside DaVinciBox.
    distrobox enter "$CONTAINER" -- sh -c \
        'cd "$1" && python3 ./install.py check --root "$2"' \
        sh "$release_root" "$RESOLVE_ROOT" \
        || fatal "AAC plugin package or DaVinci Resolve compatibility check failed in DaVinciBox."

    check_resolve_stopped_distrobox "$CONTAINER"

    distrobox_prep_dir "$CONTAINER" "$RESOLVE_ROOT/IOPlugins"

    install_bundle_distrobox \
        "$CONTAINER" \
        "$release_root/aac_decoder_probe.dvcp.bundle" \
        "aac_decoder_probe.dvcp.bundle"

    install_bundle_distrobox \
        "$CONTAINER" \
        "$release_root/aac_fdk_plugin.dvcp.bundle" \
        "aac_fdk_plugin.dvcp.bundle"

    distrobox enter "$CONTAINER" -- rm -rf -- "$workdir" 2>/dev/null \
        || distrobox enter "$CONTAINER" -- sudo rm -rf -- "$workdir" \
        || true
}

if [ "$AUTO_DVBOX" = "1" ]; then
    install_dvbox
elif [ "$AUTO_DVNAT" = "1" ]; then
    install_nobox
else
    while true; do
        CHOICE=$(radioselect \
            "DaVinciBox" \
            "Local Installation" \
            "$cancelmsg")

        [ $? -eq 0 ] || exit 100

        case "$CHOICE" in
            "DaVinciBox")
                install_dvbox
                break
                ;;
            "Local Installation")
                install_nobox
                break
                ;;
            "$cancelmsg")
                exit 100
                ;;
            *)
                exit 100
                ;;
        esac
    done
fi

info "DaVinci Resolve AAC plugins installed successfully!"
