#!/usr/bin/env bash
# Nix subsystem helpers for LinuxToys.
#
# Packages are never installed with nix-env. LinuxToys owns one declarative
# module per backend (home-manager and the NixOS system configuration) and
# rebuilds only when the user applies queued operations.

NIX_TOYS_BEGIN="# BEGIN LinuxToys managed packages"
NIX_TOYS_END="# END LinuxToys managed packages"
_NIX_GPU_SETUP_ATTEMPTED=0
_NIX_HM_NIX_CONF_BACKUP=""

_nix_bin() {
    command -v nix 2>/dev/null || {
        for candidate in /nix/var/nix/profiles/default/bin/nix \
            "$HOME/.nix-profile/bin/nix" \
            "$HOME/.local/state/nix/profile/bin/nix"; do
            [ -x "$candidate" ] && { printf '%s\n' "$candidate"; return 0; }
        done
    }
}

_nix_state_dir() {
    printf '%s\n' "${XDG_CACHE_HOME:-$HOME/.cache}/linuxtoys/nix"
}

# Resolve the active Home Manager/NixOS paths once per shell process. The
# Python resolver is the single authority: it checks explicit overrides, the
# durable path record, conventional locations and (when needed) a bounded
# discovery pass. Keeping it in Python prevents the app and the generated
# terminal scripts from disagreeing about which configuration is active.
_nix_paths_script() {
    local base="${SCRIPT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
    printf '%s\n' "${base}/app/nix_paths.py"
}

_nix_load_active_paths() {
    [ "${_NIX_ACTIVE_PATHS_READY:-0}" = "1" ] && return 0
    _NIX_ACTIVE_PATHS_READY=1
    local script output
    script=$(_nix_paths_script) || return 0
    [ -r "$script" ] || return 0
    command -v python3 >/dev/null 2>&1 || return 0
    if output=$(python3 "$script" shell 2>/dev/null); then
        [ -n "$output" ] && eval "$output"
    fi
    return 0
}

_nix_hm_paths_resolved() {
    _nix_load_active_paths
    [ -n "${_NIX_ACTIVE_HOME_SOURCE:-}" ] || return 0
    [ "${_NIX_ACTIVE_HOME_RESOLVED:-0}" = "1" ]
}

_nix_system_paths_resolved() {
    _nix_load_active_paths
    [ -n "${_NIX_ACTIVE_SYSTEM_SOURCE:-}" ] || return 0
    [ "${_NIX_ACTIVE_SYSTEM_RESOLVED:-0}" = "1" ]
}

_nix_paths_error() {
    local scope="$1" script message
    script=$(_nix_paths_script) || return 0
    [ -r "$script" ] || return 0
    command -v python3 >/dev/null 2>&1 || return 0
    message=$(python3 "$script" message "$scope" 2>/dev/null) || return 0
    [ -n "$message" ] && printf '%s\n' "$message" >&2
}

_nix_hm_flake_active() {
    _nix_load_active_paths
    if [ -n "${_NIX_ACTIVE_HOME_SOURCE:-}" ]; then
        [ "${_NIX_ACTIVE_HOME_FLAKE:-0}" = "1" ]
    else
        [ -f "$(_nix_hm_dir)/flake.nix" ]
    fi
}

_nix_system_flake_active() {
    _nix_load_active_paths
    if [ -n "${_NIX_ACTIVE_SYSTEM_SOURCE:-}" ]; then
        [ "${_NIX_ACTIVE_SYSTEM_FLAKE:-0}" = "1" ]
    else
        [ -f "$(_nix_system_dir)/flake.nix" ]
    fi
}

_nix_reload_active_paths() {
    _NIX_ACTIVE_PATHS_READY=0
    unset _NIX_ACTIVE_HOME_DIR _NIX_ACTIVE_HOME_CONFIG _NIX_ACTIVE_HOME_MODULE
    unset _NIX_ACTIVE_HOME_FLAKE _NIX_ACTIVE_HOME_RESOLVED _NIX_ACTIVE_HOME_SOURCE
    unset _NIX_ACTIVE_SYSTEM_DIR _NIX_ACTIVE_SYSTEM_CONFIG _NIX_ACTIVE_SYSTEM_MODULE
    unset _NIX_ACTIVE_SYSTEM_FLAKE _NIX_ACTIVE_SYSTEM_RESOLVED _NIX_ACTIVE_SYSTEM_SOURCE
    _nix_load_active_paths
}

_nix_record_generated_flake() {
    local scope="$1" directory="$2" config="$3" module="$4" script
    script=$(_nix_paths_script) || return 0
    [ -r "$script" ] || return 0
    command -v python3 >/dev/null 2>&1 || return 0
    python3 "$script" record-flake "$scope" "$directory" "$config" "$module" \
        >/dev/null 2>&1 || true
    _nix_reload_active_paths
}

_nix_queue_file() {
    printf '%s\n' "${LINUXTOYS_NIX_QUEUE:-$(_nix_state_dir)/queue.json}"
}

# System features LinuxToys may add to the NixOS module on demand. The marker
# lives in the user cache (like the unfree choice), while the resulting option
# is rendered into the root-owned module on the next rewrite/rebuild.
_nix_feature_marker() {
    printf '%s\n' "$(_nix_state_dir)/feature-$1"
}

_nix_feature_enabled() {
    [ "$(cat "$(_nix_feature_marker "$1")" 2>/dev/null)" = "1" ]
}

_nix_mark_feature() {
    mkdir -p -- "$(_nix_state_dir)" 2>/dev/null || true
    printf '1\n' >"$(_nix_feature_marker "$1")" 2>/dev/null
}

_nix_hm_dir() {
    _nix_load_active_paths
    if [ -n "${LINUXTOYS_NIX_HM_MODULE:-}" ]; then
        dirname -- "$LINUXTOYS_NIX_HM_MODULE"
    elif [ -n "${HOME_MANAGER_CONFIG:-}" ]; then
        if [ -f "$HOME_MANAGER_CONFIG" ]; then
            dirname -- "$(readlink -f -- "$HOME_MANAGER_CONFIG" 2>/dev/null || printf '%s\n' "$HOME_MANAGER_CONFIG")"
        else
            dirname -- "$HOME_MANAGER_CONFIG"
        fi
    elif [ -n "${LINUXTOYS_NIX_HM_DIR:-}" ]; then
        printf '%s\n' "$LINUXTOYS_NIX_HM_DIR"
    elif [ -n "${_NIX_ACTIVE_HOME_DIR:-}" ]; then
        printf '%s\n' "$_NIX_ACTIVE_HOME_DIR"
    else
        printf '%s\n' "${XDG_CONFIG_HOME:-$HOME/.config}/home-manager"
    fi
}

_nix_hm_config_file() {
    _nix_load_active_paths
    if [ -n "${_NIX_ACTIVE_HOME_CONFIG:-}" ] && [ -f "$_NIX_ACTIVE_HOME_CONFIG" ]; then
        printf '%s\n' "$_NIX_ACTIVE_HOME_CONFIG"
    elif [ -n "${HOME_MANAGER_CONFIG:-}" ] && [ -f "$HOME_MANAGER_CONFIG" ]; then
        printf '%s\n' "$HOME_MANAGER_CONFIG"
    elif [ -n "${LINUXTOYS_NIX_HM_DIR:-}" ]; then
        local candidate
        for candidate in "$LINUXTOYS_NIX_HM_DIR/home.nix" \
            "$LINUXTOYS_NIX_HM_DIR/default.nix"; do
            if [ -f "$candidate" ]; then
                printf '%s\n' "$candidate"
                return 0
            fi
        done
    fi
    return 0
}

_nix_hm_module() {
    _nix_load_active_paths
    if [ -n "${LINUXTOYS_NIX_HM_MODULE:-}" ]; then
        printf '%s\n' "$LINUXTOYS_NIX_HM_MODULE"
    elif [ -n "${_NIX_ACTIVE_HOME_MODULE:-}" ]; then
        printf '%s\n' "$_NIX_ACTIVE_HOME_MODULE"
    else
        printf '%s\n' "$(_nix_hm_dir)/linuxtoys.nix"
    fi
}

_nix_system_dir() {
    _nix_load_active_paths
    if [ -n "${LINUXTOYS_NIX_SYSTEM_MODULE:-}" ]; then
        dirname -- "$LINUXTOYS_NIX_SYSTEM_MODULE"
    elif [ -n "${NIXOS_CONFIG:-}" ]; then
        if [ -f "$NIXOS_CONFIG" ]; then
            dirname -- "$(readlink -f -- "$NIXOS_CONFIG" 2>/dev/null || printf '%s\n' "$NIXOS_CONFIG")"
        else
            dirname -- "$NIXOS_CONFIG"
        fi
    elif [ -n "${LINUXTOYS_NIX_SYSTEM_DIR:-}" ]; then
        printf '%s\n' "$LINUXTOYS_NIX_SYSTEM_DIR"
    elif [ -n "${_NIX_ACTIVE_SYSTEM_DIR:-}" ]; then
        printf '%s\n' "$_NIX_ACTIVE_SYSTEM_DIR"
    else
        printf '%s\n' "/etc/nixos"
    fi
}

_nix_system_config_file() {
    _nix_load_active_paths
    if [ -n "${NIXOS_CONFIG:-}" ] && [ -f "$NIXOS_CONFIG" ]; then
        printf '%s\n' "$NIXOS_CONFIG"
    elif [ -n "${_NIX_ACTIVE_SYSTEM_CONFIG:-}" ] && [ -f "$_NIX_ACTIVE_SYSTEM_CONFIG" ]; then
        printf '%s\n' "$_NIX_ACTIVE_SYSTEM_CONFIG"
    elif [ -n "${LINUXTOYS_NIX_SYSTEM_DIR:-}" ] \
        && [ -f "$LINUXTOYS_NIX_SYSTEM_DIR/configuration.nix" ]; then
        printf '%s\n' "$LINUXTOYS_NIX_SYSTEM_DIR/configuration.nix"
    fi
    return 0
}

_nix_system_module() {
    _nix_load_active_paths
    if [ -n "${LINUXTOYS_NIX_SYSTEM_MODULE:-}" ]; then
        printf '%s\n' "$LINUXTOYS_NIX_SYSTEM_MODULE"
    elif [ -n "${_NIX_ACTIVE_SYSTEM_MODULE:-}" ]; then
        printf '%s\n' "$_NIX_ACTIVE_SYSTEM_MODULE"
    else
        printf '%s\n' "$(_nix_system_dir)/linuxtoys.nix"
    fi
}

_nix_module_for_scope() {
    case "$1" in
        system) _nix_system_module ;;
        *) _nix_hm_module ;;
    esac
}

_nix_valid_attr() {
    [[ "$1" =~ ^[A-Za-z_][A-Za-z0-9_\'-]*$ ]]
}

_nix_hm_bin() {
    command -v home-manager 2>/dev/null || {
        for candidate in "$HOME/.nix-profile/bin/home-manager" \
            "$HOME/.local/state/nix/profile/bin/home-manager"; do
            [ -x "$candidate" ] && { printf '%s\n' "$candidate"; return 0; }
        done
    }
}

# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

nix_available() {
    [ -n "$(_nix_bin)" ]
}

nix_flakes_enabled() {
    local bin output
    bin=$(_nix_bin)
    [ -n "$bin" ] || return 1
    output=$("$bin" config show experimental-features 2>/dev/null) \
        || output=$("$bin" show-config 2>/dev/null | sed -n 's/^experimental-features[[:space:]]*=[[:space:]]*//p')
    output=${output//,/ }
    [[ " $output " == *" flakes "* ]]
}

nix_home_manager_available() {
    [ -n "$(_nix_hm_bin)" ]
}

nix_is_nixos() {
    if [ -e /etc/NIXOS ] || [ -f "$(_nix_system_dir)/configuration.nix" ]; then
        return 0
    fi
    local id="" id_like=""
    if [ -r /etc/os-release ]; then
        id=$(sed -n 's/^ID=//p' /etc/os-release | head -n1 | tr -d '"' | tr '[:upper:]' '[:lower:]')
        id_like=$(sed -n 's/^ID_LIKE=//p' /etc/os-release | head -n1 | tr -d '"' | tr '[:upper:]' '[:lower:]')
    fi
    case "$id" in
        nixos|nixos-*) return 0 ;;
    esac
    case " $id_like " in
        *" nixos "*) return 0 ;;
    esac
    return 1
}

nix_system_available() {
    nix_is_nixos
}

# Nix packages on a non-NixOS host load the host GPU stack through Home
# Manager's genericLinux GPU target. NixOS already provides /run/opengl-driver,
# and gregOS links its custom driver stack there itself.
nix_gpu_supported() {
    nix_is_nixos && return 1
    if declare -F is_gregos >/dev/null 2>&1 && is_gregos; then
        return 1
    fi
    return 0
}

nix_gpu_configured() {
    local path
    for path in \
        "$(_nix_hm_module)" \
        "$(_nix_hm_config_file)" \
        "$(_nix_hm_dir)/home.nix" \
        "$(_nix_hm_dir)/default.nix" \
        "$(_nix_hm_dir)/flake.nix"; do
        [ -f "$path" ] || continue
        grep -qsE '(^|[[:space:]{;])(targets\.genericLinux\.)?gpu\.enable[[:space:]]*=[[:space:]]*true' "$path" \
            && return 0
    done
    return 1
}

nix_gpu64_setup_ready() {
    nix_gpu_configured || return 1
    [ -e /run/opengl-driver ] || return 1
    [ -e /etc/tmpfiles.d/non-nixos-gpu.conf ] \
        || [ -e /etc/systemd/system/non-nixos-gpu.service ]
}

_nix_gpu32_script() {
    local base="${SCRIPT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
    printf '%s\n' "${base}/libs/nix-gpu32.bash"
}

# 32-bit Nix GPU support is an x86_64-only complement to the Home Manager
# 64-bit target. NixOS and gregOS already provide the complete layout.
nix_gpu32_supported() {
    nix_gpu_supported || return 1
    [ "$(uname -m)" = "x86_64" ] || return 1
    local script
    script=$(_nix_gpu32_script)
    [ -r "$script" ] || return 1
    bash "$script" supported >/dev/null 2>&1
}

nix_gpu32_ready() {
    nix_gpu32_supported || return 0
    local script
    script=$(_nix_gpu32_script)
    [ -r "$script" ] || return 1
    bash "$script" status >/dev/null 2>&1
}

nix_gpu_setup_ready() {
    nix_gpu64_setup_ready || return 1
    nix_gpu32_ready
}

# Nix packages' bubblewrap wrappers bind /etc/zoneinfo. Distributions that keep
# tzdata only under /usr/share/zoneinfo leave that source path missing, so
# non-NixOS hosts get the compatibility link. NixOS provides it itself, and
# gregOS ships it in the image.
nix_zoneinfo_required() {
    nix_is_nixos && return 1
    if declare -F is_gregos >/dev/null 2>&1 && is_gregos; then
        return 1
    fi
    [ -d /usr/share/zoneinfo ]
}

nix_zoneinfo_ready() {
    nix_zoneinfo_required || return 0
    [ -e /etc/zoneinfo ] || [ -L /etc/zoneinfo ]
}

_nix_ensure_zoneinfo() {
    nix_zoneinfo_ready && return 0
    if [ "${LINUXTOYS_NIX_DRY_RUN:-0}" = "1" ]; then
        printf 'Skipping /etc/zoneinfo compatibility link (dry run).\n'
        return 0
    fi
    if ! sudo_ ln -s -- /usr/share/zoneinfo /etc/zoneinfo; then
        # A concurrent setup may have created the link after the readiness
        # check; accept that instead of failing the caller.
        nix_zoneinfo_ready && return 0
        return 1
    fi
    declare -F _append_transmap >/dev/null 2>&1 \
        && _append_transmap "created /etc/zoneinfo"
    return 0
}

_nix_gpu_setup_bin() {
    local candidate resolved
    for candidate in \
        "$HOME/.nix-profile/bin/non-nixos-gpu-setup" \
        "$HOME/.local/state/nix/profiles/home-manager/bin/non-nixos-gpu-setup" \
        "$HOME/.local/state/nix/profiles/profile/bin/non-nixos-gpu-setup"; do
        [ -x "$candidate" ] || continue
        resolved=$(readlink -f -- "$candidate" 2>/dev/null) || resolved="$candidate"
        printf '%s\n' "$resolved"
        return 0
    done
    candidate=$(command -v non-nixos-gpu-setup 2>/dev/null) || candidate=""
    [ -n "$candidate" ] && [ -x "$candidate" ] || return 1
    resolved=$(readlink -f -- "$candidate" 2>/dev/null) || resolved="$candidate"
    printf '%s\n' "$resolved"
}

_nix_gpu_setup_from_output() {
    local log="$1"
    [ -f "$log" ] || return 1
    grep -oE '/nix/store/[[:alnum:]]+-non-nixos-gpu/bin/non-nixos-gpu-setup' "$log" \
        | head -n1
}

# Home Manager compares the active /run/opengl-driver link with the driver
# environment it just built and prints the exact setup command when they
# differ. Keep the switch output visible while capturing that command.
_nix_run_home_manager_switch() {
    local log rc setup
    if ! nix_gpu_supported; then
        "$@"
        return $?
    fi
    log=$(mktemp "${TMPDIR:-/tmp}/linuxtoys-nix-hm.XXXXXX") || {
        "$@"
        return $?
    }
    "$@" 2>&1 | tee "$log"
    rc=${PIPESTATUS[0]}
    if [ "$rc" -eq 0 ]; then
        setup=$(_nix_gpu_setup_from_output "$log") || setup=""
        if [ -n "$setup" ]; then
            _NIX_GPU_SETUP_ATTEMPTED=1
            printf 'GPU drivers changed; refreshing non-NixOS GPU setup...\n'
            sudo_ "$setup" \
                || printf 'GPU driver setup did not complete; run %s manually.\n' "$setup" >&2
        fi
    fi
    rm -f -- "$log"
    return "$rc"
}

_nix_rewrite_module() {
    local scope="$1"
    local -a current
    mapfile -t current < <(_nix_module_read_packages "$scope")
    _nix_write_module "$scope" "${current[@]}"
}

_nix_write_gpu_module() {
    _nix_rewrite_module home-manager
}

_nix_ensure_gpu64_setup() {
    nix_home_manager_available || return 0
    _nix_hm_paths_resolved || return 0
    if [ "${LINUXTOYS_NIX_DRY_RUN:-0}" = "1" ]; then
        printf 'Skipping 64-bit GPU setup (dry run).\n'
        return 0
    fi

    local changed=0 bin
    _NIX_GPU_SETUP_ATTEMPTED=0
    if ! nix_gpu_configured; then
        _nix_write_gpu_module || return 1
        changed=1
    fi

    bin=$(_nix_gpu_setup_bin) || bin=""
    if [ "$changed" -eq 1 ] || [ -z "$bin" ]; then
        _nix_rebuild home-manager || return 1
        bin=$(_nix_gpu_setup_bin) || bin=""
        if [ "$_NIX_GPU_SETUP_ATTEMPTED" -eq 1 ]; then
            nix_gpu64_setup_ready && return 0
            printf 'GPU driver setup did not complete; run the reported non-nixos-gpu-setup command again.\n' >&2
            return 1
        fi
    fi

    nix_gpu64_setup_ready && return 0
    [ -n "$bin" ] || {
        printf 'Could not locate non-nixos-gpu-setup after the Home Manager rebuild.\n' >&2
        return 1
    }
    sudo_ "$bin"
}

_nix_ensure_gpu32_tools() {
    local -a packages=() tools=()
    if ! command -v patchelf >/dev/null 2>&1; then
        packages+=(patchelf)
        tools+=(patchelf)
    fi
    if ! command -v readelf >/dev/null 2>&1; then
        packages+=(binutils)
        tools+=(readelf)
    fi
    if ! command -v jq >/dev/null 2>&1; then
        packages+=(jq)
        tools+=(jq)
    fi
    ((${#packages[@]})) || return 0
    if declare -F pkg_install >/dev/null 2>&1; then
        pkg_install "${packages[@]}"
        return $?
    fi
    printf 'Missing 32-bit GPU bundle tools: %s\n' "${tools[*]}" >&2
    printf 'Install patchelf, binutils and jq, then retry.\n' >&2
    return 1
}

_nix_ensure_gpu32_setup() {
    local mode="${1:-setup}" script
    nix_gpu32_supported || return 0
    if [ "${LINUXTOYS_NIX_DRY_RUN:-0}" = "1" ]; then
        printf 'Skipping 32-bit GPU setup (dry run).\n'
        return 0
    fi
    script=$(_nix_gpu32_script)
    [ -r "$script" ] || return 1
    _nix_ensure_gpu32_tools || return 1
    sudo_ bash "$script" "$mode" || return 1
    if [ "$mode" = "setup" ]; then
        declare -F _append_transmap >/dev/null 2>&1 \
            && _append_transmap "installed 32-bit Nix GPU bundle"
    fi
    return 0
}

_nix_ensure_gpu_setup() {
    nix_gpu_supported || return 0
    if [ "${LINUXTOYS_NIX_DRY_RUN:-0}" = "1" ]; then
        printf 'Skipping GPU setup (dry run).\n'
        return 0
    fi

    local rc=0
    _nix_ensure_gpu64_setup || rc=1
    _nix_ensure_gpu32_setup setup || rc=1
    return "$rc"
}

nix_unfree_enabled() {
    case "${NIXPKGS_ALLOW_UNFREE:-0}" in
        1|true|yes) return 0 ;;
    esac
    local marker
    marker="$(_nix_state_dir)/allow-unfree"
    [ "$(cat "$marker" 2>/dev/null)" = "1" ] && return 0
    grep -qsE 'allowUnfree[[:space:]]*=[[:space:]]*true' \
        "$(_nix_hm_module)" \
        "$(_nix_system_module)" \
        "$HOME/.config/nixpkgs/config.nix" \
        "$(_nix_hm_dir)/home.nix" \
        "$(_nix_hm_dir)/default.nix" \
        "$(_nix_hm_dir)/flake.nix" \
        "$(_nix_system_dir)/configuration.nix" \
        2>/dev/null
}

# ---------------------------------------------------------------------------
# Module generation
# ---------------------------------------------------------------------------

_nix_should_allow_unfree() {
    local marker
    marker="$(_nix_state_dir)/allow-unfree"
    [ "$(cat "$marker" 2>/dev/null)" = "1" ] && return 0
    grep -qsE 'allowUnfree[[:space:]]*=[[:space:]]*true' \
        "$(_nix_hm_module)" "$(_nix_system_module)" 2>/dev/null && return 0
    nix_unfree_enabled
}

_nix_render_packages() {
    local attr
    for attr in "$@"; do
        _nix_valid_attr "$attr" || continue
        printf '    pkgs.%s\n' "$attr"
    done
}

_nix_flakes_import_name() {
    if [ "$1" = "system" ]; then
        printf '%s\n' "linuxtoys-system-flakes.nix"
    else
        printf '%s\n' "linuxtoys-flakes.nix"
    fi
}

_nix_flakes_module_path() {
    printf '%s/%s\n' "$(dirname -- "$(_nix_module_for_scope "$1")")" \
        "$(_nix_flakes_import_name "$1")"
}

_nix_render_module() {
    local scope="$1"
    shift
    local allow_unfree="" flakes_import="" gpu_enable="" maintenance=""
    local flatpak_enable="" appimage_enable=""
    _nix_should_allow_unfree && allow_unfree="  nixpkgs.config.allowUnfree = true;"
    flakes_import="  imports = [ ./$(_nix_flakes_import_name "$scope") ];"
    if [ "$scope" = "system" ]; then
        _nix_feature_enabled flatpak && flatpak_enable="  services.flatpak.enable = true;"
        if _nix_feature_enabled appimage; then
            appimage_enable=$(cat <<'EOF'
  programs.appimage.enable = true;
  programs.appimage.binfmt = lib.mkDefault true;
EOF
)
        fi
    fi
    if [ "$scope" != "system" ] && nix_gpu_supported; then
        gpu_enable="  targets.genericLinux.gpu.enable = true;"
    fi
    if [ "$scope" != "system" ] && ! nix_is_nixos; then
        maintenance=$(cat <<'EOF'
  # Home Manager only generates nix.conf when it knows which Nix package to
  # use. NixOS supplies one through the system module; standalone installs
  # must name it, or nix.settings below aborts the rebuild.
  nix.package = lib.mkDefault pkgs.nix;
  nix.settings.extra-experimental-features = [ "nix-command" "flakes" ];
  nix.gc = {
    automatic = true;
    dates = "weekly";
    options = "--delete-older-than 14d";
  };
  nix.settings.auto-optimise-store = true;
  # LinuxToys replaces the stock nix-gc command so the newest three
  # generations survive even when they are older than two weeks.
  systemd.user.services.nix-gc.Service.ExecStart = lib.mkForce
    "${config.home.homeDirectory}/.local/share/linuxtoys/nix-gc.sh";
EOF
)
    fi

    if [ "$scope" = "system" ]; then
        cat <<EOF
{ lib, pkgs, ... }:

# Generated by LinuxToys. Packages are managed through the Nix subsystem.
{
$allow_unfree
$flakes_import
$flatpak_enable
$appimage_enable
  environment.systemPackages = [
$NIX_TOYS_BEGIN
$(_nix_render_packages "$@")
$NIX_TOYS_END
  ];
}
EOF
    else
        cat <<EOF
{ config, lib, pkgs, ... }:

# Generated by LinuxToys. Packages are managed through the Nix subsystem.
{
$allow_unfree
$gpu_enable
$maintenance
$flakes_import
  home.packages = [
$NIX_TOYS_BEGIN
$(_nix_render_packages "$@")
$NIX_TOYS_END
  ];
}
EOF
    fi
}

_nix_module_read_packages() {
    local scope="$1" module
    module=$(_nix_module_for_scope "$scope")
    [ -f "$module" ] || return 0
    sed -n "/$NIX_TOYS_BEGIN/,/$NIX_TOYS_END/p" "$module" \
        | grep -oE "pkgs\.[A-Za-z_][A-Za-z0-9_'-]*" \
        | sed 's/^pkgs\.//' || true
}

# Publish a validated Nix file. User files are moved in place; root-owned system
# files go through the shared sudo helper. A one-shot backup is kept unless the
# user already has one.
_nix_publish_file() {
    local source="$1" target="$2" directory backup
    directory=$(dirname -- "$target")
    backup="${target}.linuxtoys.bak"
    mkdir -p -- "$directory" 2>/dev/null || true

    if command -v nix-instantiate >/dev/null 2>&1; then
        nix-instantiate --parse "$source" >/dev/null 2>&1 || return 1
    fi

    chmod 0644 "$source" 2>/dev/null || true
    if [ ! -e "$backup" ]; then
        if [ -e "$target" ]; then
            if [ -w "$directory" ]; then
                cp -p -- "$target" "$backup" 2>/dev/null || true
            else
                declare -F sudo_ >/dev/null 2>&1 && sudo_ cp -p -- "$target" "$backup" 2>/dev/null || true
            fi
        fi
    fi

    if [ -w "$directory" ]; then
        mv -f -- "$source" "$target"
    else
        declare -F sudo_ >/dev/null 2>&1 || { rm -f -- "$source"; return 1; }
        sudo_ install -m 0644 -- "$source" "$target" || { rm -f -- "$source"; return 1; }
        rm -f -- "$source"
    fi
}

_nix_write_file() {
    local target="$1" content="$2" temporary
    temporary=$(mktemp "${TMPDIR:-/tmp}/linuxtoys-nix.XXXXXX") || return 1
    printf '%s\n' "$content" >"$temporary" || {
        rm -f -- "$temporary"
        return 1
    }
    if _nix_publish_file "$temporary" "$target"; then
        return 0
    fi
    rm -f -- "$temporary"
    return 1
}

_nix_write_script() {
    local target="$1" content="$2" directory temporary
    directory=$(dirname -- "$target")
    mkdir -p -- "$directory" 2>/dev/null || return 1
    temporary=$(mktemp "${TMPDIR:-/tmp}/linuxtoys-nix-script.XXXXXX") || return 1
    printf '%s\n' "$content" >"$temporary" || {
        rm -f -- "$temporary"
        return 1
    }
    chmod 0755 "$temporary" 2>/dev/null || true
    if mv -f -- "$temporary" "$target"; then
        return 0
    fi
    rm -f -- "$temporary"
    return 1
}

_nix_write_nix_gc_script() {
    local target content
    [ -n "${HOME:-}" ] || return 1
    target="$HOME/.local/share/linuxtoys/nix-gc.sh"
    content=$(cat <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Mirrors --delete-older-than 14d, but keeps the newest three generations.
keep_days=14
keep_generations=3

_nix_gc_tool() {
    local name="$1" candidate
    for candidate in "$HOME/.nix-profile/bin/$name" \
        "$HOME/.local/state/nix/profile/bin/$name" \
        "/nix/var/nix/profiles/default/bin/$name"; do
        [ -x "$candidate" ] && { printf '%s\n' "$candidate"; return 0; }
    done
    command -v "$name" 2>/dev/null
}

nix_env=$(_nix_gc_tool nix-env) || exit 0
nix_gc=$(_nix_gc_tool nix-collect-garbage) || exit 0
nix_store=$(_nix_gc_tool nix-store) || true
now=$(date +%s)
cutoff=$((now - keep_days * 86400))

trim_profile() {
    local profile="$1" line generation rest day marker timestamp index total
    local -a generations=() delete=()
    [ -e "$profile" ] || return 0
    mapfile -t generations < <(
        "$nix_env" --profile "$profile" --list-generations 2>/dev/null \
            | awk '/^[[:space:]]*[0-9]+[[:space:]]/ { print $1, $2, ($0 ~ /current/ ? "current" : "old") }'
    )
    total=${#generations[@]}
    (( total > keep_generations )) || return 0
    for (( index = 0; index < total - keep_generations; index++ )); do
        line=${generations[index]}
        generation=${line%% *}
        rest=${line#* }
        day=${rest%% *}
        marker=${rest#* }
        [ "$marker" = "current" ] && continue
        timestamp=$(date -d "$day" +%s 2>/dev/null) || continue
        (( timestamp < cutoff )) && delete+=("$generation")
    done
    (( ${#delete[@]} )) || return 0
    "$nix_env" --profile "$profile" --delete-generations "${delete[@]}"
}

declare -A seen=()
for profile in \
    "$HOME/.nix-profile" \
    "$HOME/.local/state/nix/profiles/profile" \
    "$HOME/.local/state/nix/profiles/home-manager" \
    "$HOME/.local/state/nix/profiles/channels"; do
    resolved=$(readlink -f -- "$profile" 2>/dev/null) || resolved="$profile"
    [ -n "${seen[$resolved]:-}" ] && continue
    seen[$resolved]=1
    trim_profile "$profile" || exit 1
done

"$nix_gc" || exit 1
[ -n "$nix_store" ] && "$nix_store" --optimise || true
EOF
)
    _nix_write_script "$target" "$content"
}

# Older generated modules carry the cleanup service without nix.package, which
# makes Home Manager abort on non-NixOS; treat them as outdated so setup
# rewrites them before the next rebuild.
nix_maintenance_configured() {
    [ -f "$HOME/.local/share/linuxtoys/nix-gc.sh" ] \
        && grep -qF 'systemd.user.services.nix-gc.Service.ExecStart' \
            "$(_nix_hm_module)" 2>/dev/null \
        && grep -qE '^[[:space:]]*nix\.package[[:space:]]*=' \
            "$(_nix_hm_module)" 2>/dev/null
}

_nix_ensure_maintenance() {
    nix_is_nixos && return 0
    _nix_write_nix_gc_script || return 1
    nix_maintenance_configured && return 0
    local -a current
    mapfile -t current < <(_nix_module_read_packages home-manager)
    _nix_write_module home-manager "${current[@]}"
}

_nix_write_module() {
    local scope="$1" target content flakes
    shift
    if [ "$scope" = "system" ]; then
        if ! _nix_system_paths_resolved; then
            _nix_paths_error system
            return 1
        fi
    elif ! _nix_hm_paths_resolved; then
        _nix_paths_error home-manager
        return 1
    fi
    target=$(_nix_module_for_scope "$scope")
    flakes=$(_nix_flakes_module_path "$scope")
    if [ "$scope" != "system" ] && ! nix_is_nixos; then
        _nix_write_nix_gc_script || return 1
    fi
    if [ ! -e "$flakes" ]; then
        _nix_write_file "$flakes" "{ pkgs, ... }:

# LinuxToys replaces this file when Nix flakes are imported.
{
}" || return 1
    fi
    content=$(_nix_render_module "$scope" "$@")
    _nix_write_file "$target" "$content"
}

# Insert `./<module>` into an existing imports/modules list. If the file has
# neither, the module body opening is used for regular home-manager/NixOS
# configuration files. Flakes without a modules list are never guessed at.
_nix_patch_imports() {
    local path="$1" module="${2:-linuxtoys.nix}" temporary inserted=0
    [ -f "$path" ] || return 1
    grep -qF -- "$module" "$path" && return 0

    temporary=$(mktemp "${TMPDIR:-/tmp}/linuxtoys-nix.XXXXXX") || return 1
    inserted=0
    if awk -v module="$module" '
        BEGIN { done = 0 }
        {
            if (!done && $0 ~ /(imports|modules)[[:space:]]*=[[:space:]]*\[/) {
                sub(/\[/, "[ ./" module, $0)
                done = 1
            }
            print
        }
        END { exit(done ? 0 : 3) }
    ' "$path" >"$temporary"; then
        inserted=1
    fi
    if [ "$inserted" -eq 0 ]; then
        if [ "$(basename -- "$path")" = "flake.nix" ]; then
            rm -f -- "$temporary"
            return 1
        fi
        if awk -v module="$module" '
            BEGIN { done = 0 }
            {
                print
                if (!done && $0 ~ /^[[:space:]]*\{[[:space:]]*$/) {
                    print "  imports = [ ./" module " ];"
                    done = 1
                }
            }
            END { exit(done ? 0 : 3) }
        ' "$path" >"$temporary"; then
            inserted=1
        fi
        if [ "$inserted" -eq 0 ]; then
            rm -f -- "$temporary"
            return 1
        fi
    fi

    if _nix_publish_file "$temporary" "$path"; then
        return 0
    fi
    rm -f -- "$temporary"
    return 1
}

_nix_create_hm_home() {
    local path="$1" state_version content
    state_version=$("$(_nix_hm_bin)" --version 2>/dev/null \
        | sed -n 's/^\([0-9][0-9]*\.[0-9][0-9]*\).*/\1/p' | head -n1)
    [ -n "$state_version" ] || state_version="24.05"
    content=$(cat <<EOF
{ config, pkgs, ... }:

{
  home.username = "$USER";
  home.homeDirectory = "$HOME";
  home.stateVersion = "$state_version";
  imports = [ ./linuxtoys.nix ];
}
EOF
)
    _nix_write_file "$path" "$content"
}

_nix_ensure_hm_config() {
    local directory module override
    if ! _nix_hm_paths_resolved; then
        _nix_paths_error home-manager
        return 1
    fi
    directory=$(_nix_hm_dir)
    module=$(_nix_hm_module)
    override=$(_nix_hm_config_file)
    mkdir -p -- "$directory" 2>/dev/null || true
    [ -f "$module" ] || _nix_write_module home-manager || return 1
    _nix_ensure_maintenance || return 1

    if _nix_hm_flake_active; then
        if [ -f "$directory/home.nix" ] \
            && grep -qE '(\./)?home\.nix([^[:alnum:]_.-]|$)' "$directory/flake.nix"; then
            _nix_patch_imports "$directory/home.nix" && return 0
        fi
        if [ -f "$directory/default.nix" ] \
            && grep -qE '(\./)?default\.nix([^[:alnum:]_.-]|$)' "$directory/flake.nix"; then
            _nix_patch_imports "$directory/default.nix" && return 0
        fi
        if [ -n "$override" ] \
            && grep -qF -- "$(basename -- "$override")" "$directory/flake.nix"; then
            _nix_patch_imports "$override" && return 0
        fi
        _nix_patch_imports "$directory/flake.nix" && return 0
        if [ -n "$override" ]; then
            _nix_patch_imports "$override" && return 0
        fi
        if [ -f "$directory/home.nix" ]; then
            _nix_patch_imports "$directory/home.nix" && return 0
        fi
        if [ -f "$directory/default.nix" ]; then
            _nix_patch_imports "$directory/default.nix" && return 0
        fi
        return 1
    fi
    if [ -n "$override" ]; then
        _nix_patch_imports "$override"
        return $?
    fi
    if [ -f "$directory/home.nix" ]; then
        _nix_patch_imports "$directory/home.nix"
        return $?
    fi
    if [ -f "$directory/default.nix" ]; then
        _nix_patch_imports "$directory/default.nix"
        return $?
    fi
    _nix_create_hm_home "$directory/home.nix"
}

_nix_ensure_system_config() {
    local directory module config
    if ! _nix_system_paths_resolved; then
        _nix_paths_error system
        return 1
    fi
    directory=$(_nix_system_dir)
    module=$(_nix_system_module)
    config=$(_nix_system_config_file)
    [ -f "$module" ] || _nix_write_module system || return 1

    if _nix_system_flake_active; then
        if [ -n "$config" ] && [ -f "$config" ] \
            && grep -qE '(\./)?configuration\.nix([^[:alnum:]_.-]|$)' "$directory/flake.nix"; then
            _nix_patch_imports "$config" && return 0
        fi
        _nix_patch_imports "$directory/flake.nix" && return 0
        if [ -n "$config" ] && [ -f "$config" ]; then
            _nix_patch_imports "$config" && return 0
        fi
        return 1
    fi
    if [ -n "$config" ] && [ -f "$config" ]; then
        _nix_patch_imports "$config"
        return $?
    fi
    return 1
}

_nix_ensure_import() {
    case "$1" in
        system) _nix_ensure_system_config ;;
        *) _nix_ensure_hm_config ;;
    esac
}

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

_nix_user_nix_conf() {
    printf '%s\n' "${XDG_CONFIG_HOME:-$HOME/.config}/nix/nix.conf"
}

_nix_enable_flakes() {
    local directory config
    directory="${XDG_CONFIG_HOME:-$HOME/.config}/nix"
    config="$directory/nix.conf"
    mkdir -p -- "$directory" || return 1
    if ! grep -qsE '^[[:space:]]*(extra-)?experimental-features[[:space:]]*=.*flakes' "$config" 2>/dev/null; then
        {
            [ -f "$config" ] && [ -n "$(tail -c1 "$config" 2>/dev/null)" ] && printf '\n'
            printf 'extra-experimental-features = nix-command flakes\n'
        } >>"$config" || return 1
    fi
    nix_flakes_enabled
}

# _nix_enable_flakes creates a regular user nix.conf when flakes are disabled.
# The generated module now manages that path through nix.settings, so a file
# carrying only LinuxToys' flake line is moved aside before the Home Manager
# switch; the generated nix.conf contains the same extra features.
_nix_stash_linux_toys_nix_conf() {
    local config line backup index=1 active=0
    config=$(_nix_user_nix_conf)
    [ -f "$config" ] && [ ! -L "$config" ] || return 0
    while IFS= read -r line || [ -n "$line" ]; do
        line=${line#"${line%%[![:space:]]*}"}
        line=${line%"${line##*[![:space:]]}"}
        [ -z "$line" ] && continue
        case "$line" in
            \#*) continue ;;
            "extra-experimental-features = nix-command flakes") active=1 ;;
            *) return 0 ;;
        esac
    done <"$config"
    ((active)) || return 0
    backup="${config}.linuxtoys.bak"
    while [ -e "$backup" ]; do
        backup="${config}.linuxtoys.bak.$index"
        index=$((index + 1))
    done
    mv -f -- "$config" "$backup" || return 1
    _NIX_HM_NIX_CONF_BACKUP="$backup"
}

_nix_restore_user_nix_conf() {
    local config
    [ -n "${_NIX_HM_NIX_CONF_BACKUP:-}" ] || return 0
    config=$(_nix_user_nix_conf)
    if [ ! -e "$config" ]; then
        mv -f -- "$_NIX_HM_NIX_CONF_BACKUP" "$config" 2>/dev/null || true
    fi
    _NIX_HM_NIX_CONF_BACKUP=""
}

_nix_install_home_manager() {
    local bin
    bin=$(_nix_bin) || return 1
    [ -n "$bin" ] || return 1
    "$bin" --extra-experimental-features "nix-command flakes" \
        profile install nixpkgs#home-manager || return 1
    export PATH="$HOME/.nix-profile/bin:$HOME/.local/state/nix/profile/bin:$PATH"
    nix_home_manager_available
}

nix_setup() {
    local rc=0 answer hm_backend=0 system_backend=0
    if ! nix_available; then
        printf 'Nix is not installed.\n' >&2
        return 1
    fi

    _nix_ensure_zoneinfo || {
        printf 'Could not create the /etc/zoneinfo compatibility link.\n' >&2
        rc=1
    }

    if ! nix_flakes_enabled; then
        if command -v question >/dev/null 2>&1; then
            question "Enable Nix flakes" \
                "LinuxToys installs Nix packages from nixpkgs and needs flakes. Enable flakes in your user Nix configuration?" \
                420 200 || rc=1
        fi
        if [ "$rc" -eq 0 ]; then
            _nix_enable_flakes || {
                printf 'Could not enable Nix flakes.\n' >&2
                rc=1
            }
        fi
    fi
    [ "$rc" -eq 0 ] || return "$rc"

    if ! nix_unfree_enabled; then
        if command -v question >/dev/null 2>&1; then
            if question "Allow unfree Nix packages" \
                "Some applications in nixpkgs are unfree (for example proprietary browsers or media codecs). Allow them in the LinuxToys Nix module?" \
                420 220; then
                answer=1
            else
                answer=0
            fi
        else
            answer=1
        fi
        mkdir -p -- "$(_nix_state_dir)" 2>/dev/null || true
        printf '%s\n' "$answer" >"$(_nix_state_dir)/allow-unfree" 2>/dev/null || true
    else
        mkdir -p -- "$(_nix_state_dir)" 2>/dev/null || true
        printf '1\n' >"$(_nix_state_dir)/allow-unfree" 2>/dev/null || true
    fi

    if ! nix_home_manager_available \
        && { ! nix_is_nixos || _nix_hm_paths_resolved; }; then
        if command -v question >/dev/null 2>&1; then
            question "Install Home Manager" \
                "Home Manager gives user-level Nix installs their own profile and makes package changes reversible. It is recommended. Install it now?" \
                420 220 || answer=0
        fi
        if [ "${answer:-1}" = "1" ]; then
            _nix_install_home_manager || {
                printf 'Home Manager could not be installed; system-level Nix remains available on NixOS.\n' >&2
            }
            _nix_reload_active_paths
        fi
    fi

    if nix_home_manager_available; then
        if _nix_hm_paths_resolved; then
            if _nix_ensure_hm_config; then
                hm_backend=1
                _nix_ensure_gpu_setup || {
                    printf 'Could not set up GPU acceleration for Nix packages.\n' >&2
                    rc=1
                }
            else
                printf 'Could not integrate the LinuxToys module into the Home Manager configuration.\n' >&2
                rc=1
            fi
        fi
    fi
    if nix_system_available; then
        if _nix_system_paths_resolved; then
            if _nix_ensure_system_config; then
                system_backend=1
            else
                printf 'Could not integrate the LinuxToys module into the NixOS configuration.\n' >&2
                rc=1
            fi
        fi
    fi

    if [ "$hm_backend" -eq 0 ] && [ "$system_backend" -eq 0 ]; then
        if nix_home_manager_available && ! _nix_hm_paths_resolved; then
            _nix_paths_error home-manager
        fi
        if nix_system_available && ! _nix_system_paths_resolved; then
            _nix_paths_error system
        fi
        printf 'Neither an active Home Manager environment nor a NixOS system configuration could be prepared.\n' >&2
        rc=1
    fi
    return "$rc"
}

# ---------------------------------------------------------------------------
# Host features that are NixOS options rather than packages
# ---------------------------------------------------------------------------

nix_flatpak_ready() {
    command -v flatpak >/dev/null 2>&1 || return 1
    if nix_is_nixos; then
        # The NixOS option also provides the system helper used by system-scope
        # remotes; a user-profile Flatpak alone is not the full host feature.
        systemctl cat flatpak-system-helper.service >/dev/null 2>&1 || return 1
    fi
}

# NixOS does not install Flatpak through a distro package manager. Enable the
# system option in the LinuxToys module and rebuild once, so both the CLI and
# the system helper/portals work as they do on other distributions.
nix_ensure_flatpak() {
    nix_flatpak_ready && return 0
    nix_is_nixos || return 1
    nix_available || return 1
    if [ "${LINUXTOYS_NIX_DRY_RUN:-0}" = "1" ]; then
        printf 'Skipping NixOS Flatpak enablement (dry run).\n'
        return 0
    fi
    _nix_mark_feature flatpak || return 1
    _nix_ensure_system_config || return 1
    _nix_rewrite_module system || return 1
    _nix_rebuild system || return 1
    hash -r 2>/dev/null || true
    nix_flatpak_ready
}

nix_appimage_ready() {
    command -v appimage-run >/dev/null 2>&1 || return 1
    # NixOS registers the binfmt handler under the option name 'appimage'.
    [ -e /proc/sys/fs/binfmt_misc/appimage ]
}

# AppImages run through appimage-run via binfmt on NixOS. The registration is a
# system option, so enable it in the LinuxToys module once and rebuild.
nix_ensure_appimage() {
    nix_appimage_ready && return 0
    nix_is_nixos || return 1
    nix_available || return 1
    if [ "${LINUXTOYS_NIX_DRY_RUN:-0}" = "1" ]; then
        printf 'Skipping NixOS AppImage enablement (dry run).\n'
        return 0
    fi
    _nix_mark_feature appimage || return 1
    _nix_ensure_system_config || return 1
    _nix_rewrite_module system || return 1
    _nix_rebuild system || return 1
    hash -r 2>/dev/null || true
    nix_appimage_ready
}

# Install a repository listing that ships a flake as its NixOS source. The
# default package is selected (a single unambiguous package output), imported
# through the declarative flake state and applied in one rebuild.
nix_install_repo_flake() {
    local reference="$1" name="${2:-}" scope="" apply_script rc
    [ -n "$reference" ] || {
        printf 'No flake reference was provided.\n' >&2
        return 1
    }
    nix_available || {
        printf 'Nix is not installed.\n' >&2
        return 1
    }
    if ! nix_flakes_enabled; then
        _nix_enable_flakes || {
            printf 'Could not enable Nix flakes.\n' >&2
            return 1
        }
    fi
    if nix_is_nixos; then
        scope="system"
    fi
    printf 'Inspecting the flake and preparing its default package...\n'
    apply_script=$(python3 "$SCRIPT_DIR/app/nix_flake_cli.py" \
        install-default "$reference" "$scope" "$name") || return 1
    [ -n "$apply_script" ] || {
        printf 'Could not prepare the flake installation.\n' >&2
        return 1
    }
    printf 'Applying the Nix configuration...\n'
    SCRIPT_DIR="$SCRIPT_DIR" bash "$apply_script"
    rc=$?
    rm -f -- "$apply_script"
    return "$rc"
}

# ---------------------------------------------------------------------------
# Apply queued operations
# ---------------------------------------------------------------------------

_nix_rebuild() {
    local scope="$1" directory rc system_config hm_config
    local -a hm_command current
    _NIX_GPU_SETUP_ATTEMPTED=0
    if [ "${LINUXTOYS_NIX_DRY_RUN:-0}" = "1" ]; then
        printf 'Skipping %s rebuild (dry run).\n' "$scope"
        return 0
    fi
    if [ "$scope" = "system" ]; then
        if ! _nix_system_paths_resolved; then
            _nix_paths_error system
            return 1
        fi
        directory=$(_nix_system_dir)
        system_config=$(_nix_system_config_file)
        # The generated LinuxToys module may import a flake module, so the
        # elevated rebuild needs flakes even when the user runs nixos-rebuild
        # without --flake.
        local nix_config="${NIX_CONFIG:+$NIX_CONFIG$'\n'}extra-experimental-features = nix-command flakes"
        if _nix_system_flake_active; then
            sudo_ env NIX_CONFIG="$nix_config" \
                nixos-rebuild switch --flake "$directory"
        elif [ -n "$system_config" ]; then
            sudo_ env NIX_CONFIG="$nix_config" \
                nixos-rebuild switch -I "nixos-config=$system_config"
        else
            printf 'No NixOS configuration found in %s.\n' "$directory" >&2
            return 1
        fi
        return $?
    fi

    if ! _nix_hm_paths_resolved; then
        _nix_paths_error home-manager
        return 1
    fi
    directory=$(_nix_hm_dir)
    hm_config=$(_nix_hm_config_file)
    export NIX_CONFIG="${NIX_CONFIG:+$NIX_CONFIG$'\n'}extra-experimental-features = nix-command flakes"
    if _nix_hm_flake_active; then
        hm_command=("$(_nix_hm_bin)" switch --flake "$directory")
    elif [ -n "$hm_config" ]; then
        hm_command=("$(_nix_hm_bin)" switch -f "$hm_config")
    elif [ -f "$directory/home.nix" ]; then
        hm_command=("$(_nix_hm_bin)" switch -f "$directory/home.nix")
    elif [ -f "$directory/default.nix" ]; then
        hm_command=("$(_nix_hm_bin)" switch -f "$directory/default.nix")
    else
        printf 'No Home Manager configuration found in %s.\n' "$directory" >&2
        return 1
    fi
    _NIX_HM_NIX_CONF_BACKUP=""
    if ! nix_is_nixos; then
        if [ -f "$(_nix_hm_module)" ]; then
            # A module generated before nix.package was added would abort the
            # switch; refresh it here so update-only/rebuild-only paths recover.
            if ! nix_maintenance_configured; then
                mapfile -t current < <(_nix_module_read_packages home-manager)
                _nix_write_module home-manager "${current[@]}" || return 1
            fi
            _nix_stash_linux_toys_nix_conf || true
        fi
    fi
    _nix_run_home_manager_switch "${hm_command[@]}"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        _nix_restore_user_nix_conf
    fi
    return "$rc"
}

_nix_channel_bin() {
    command -v nix-channel 2>/dev/null || {
        local nix candidate
        nix=$(_nix_bin) || return 1
        candidate="$(dirname -- "$nix")/nix-channel"
        [ -x "$candidate" ] && printf '%s\n' "$candidate"
    }
}

_nix_update_flake() {
    local directory="$1" elevated="$2" bin nix_config
    bin=$(_nix_bin) || return 1
    nix_config="${NIX_CONFIG:+$NIX_CONFIG$'\n'}extra-experimental-features = nix-command flakes"
    if [ "$elevated" = "sudo" ]; then
        ( cd "$directory" \
            && sudo_ env NIX_CONFIG="$nix_config" \
                "$bin" --extra-experimental-features "nix-command flakes" flake update )
    else
        ( cd "$directory" \
            && env NIX_CONFIG="$nix_config" \
                "$bin" --extra-experimental-features "nix-command flakes" flake update )
    fi
}

_nix_update_channels() {
    local elevated="$1" channel
    channel=$(_nix_channel_bin) || return 1
    if [ "$elevated" = "sudo" ]; then
        sudo_ "$channel" --update
    else
        "$channel" --update
    fi
}

# Update the Nix package sources used by the generated LinuxToys modules.
# Flake configurations refresh their locked inputs; classic configurations use
# channels. The subsequent rebuild goes through _nix_rebuild so Home Manager's
# GPU-driver warning is captured and the non-NixOS setup is refreshed.
nix_update() {
    nix_available || return 0
    local rc=0 directory elevated hm_config
    if nix_system_available \
        && _nix_system_paths_resolved \
        && { [ "$(id -u)" -eq 0 ] || [ "${UPD_SERVICE:-0}" != "1" ]; }; then
        directory=$(_nix_system_dir)
        elevated=""
        [ "$(id -u)" -ne 0 ] && elevated="sudo"
        if _nix_system_flake_active; then
            _nix_update_flake "$directory" "$elevated" || rc=1
        else
            _nix_update_channels "$elevated" || rc=1
        fi
        _nix_rebuild system || rc=1
    fi

    hm_config=$(_nix_hm_config_file)
    directory=$(_nix_hm_dir)
    if nix_home_manager_available \
        && _nix_hm_paths_resolved \
        && [ "$(id -u)" -ne 0 ] \
        && { _nix_hm_flake_active || [ -n "$hm_config" ] \
            || [ -f "$directory/home.nix" ] || [ -f "$directory/default.nix" ]; }; then
        if _nix_hm_flake_active; then
            _nix_update_flake "$directory" "" || rc=1
        else
            _nix_update_channels "" || rc=1
        fi
        _nix_rebuild home-manager || rc=1
        if nix_gpu_supported \
            && nix_gpu_configured \
            && [ "${_NIX_GPU_SETUP_ATTEMPTED:-0}" -eq 0 ] \
            && ! nix_gpu_setup_ready; then
            _nix_ensure_gpu_setup || rc=1
        fi
        if nix_gpu32_supported; then
            _nix_ensure_gpu32_setup refresh || rc=1
        fi
    fi
    return "$rc"
}

_nix_sync_registry() {
    local temporary scope attr
    temporary=$(mktemp "${TMPDIR:-/tmp}/linuxtoys-nix-registry.XXXXXX") || return 1
    for scope in home-manager system; do
        while IFS= read -r attr; do
            [ -n "$attr" ] && printf '%s\t%s\n' "$attr" "$scope" >>"$temporary"
        done < <(_nix_module_read_packages "$scope")
    done
    if python3 "$SCRIPT_DIR/app/nix_registry.py" sync "$temporary"; then
        rm -f -- "$temporary"
        return 0
    fi
    rm -f -- "$temporary"
    return 1
}

_nix_link_flakes_module() {
    local scope="$1"
    local -a current
    mapfile -t current < <(_nix_module_read_packages "$scope")
    _nix_write_module "$scope" "${current[@]}"
}

_nix_flake_cli() {
    python3 "$SCRIPT_DIR/app/nix_flake_cli.py" "$@"
}

_nix_sync_flake_registry() {
    command -v python3 >/dev/null 2>&1 || return 1
    _nix_flake_cli sync-registry "$@" >/dev/null
}

_nix_cleanup_flake_wrappers() {
    command -v python3 >/dev/null 2>&1 || return 1
    _nix_flake_cli cleanup-wrappers >/dev/null
}

# Publish one generated flakes module, link it from the LinuxToys module and
# rebuild that scope. The caller has already ensured the flake/config exists.
_nix_apply_flake_module() {
    local scope="$1" module_source="$2" target
    case "$scope" in
        system|home-manager) ;;
        *)
            printf 'Invalid flake install scope: %s\n' "$scope" >&2
            return 1
            ;;
    esac
    [ -s "$module_source" ] || {
        printf 'The flake module is empty or missing.\n' >&2
        return 1
    }
    if ! _nix_ensure_import "$scope"; then
        printf 'Could not integrate the LinuxToys Nix module for %s.\n' "$scope" >&2
        return 1
    fi
    target=$(_nix_flakes_module_path "$scope")
    if ! _nix_publish_file "$module_source" "$target"; then
        printf 'Could not write the imported flake module.\n' >&2
        return 1
    fi
    if ! _nix_link_flakes_module "$scope"; then
        printf 'Could not link the flake module into the LinuxToys Nix module.\n' >&2
        return 1
    fi
    _nix_rebuild "$scope"
}

nix_import_flake_module() {
    local scope="$1" module_source="$2" flake_source="$3"
    local directory flake
    case "$scope" in
        system|home-manager) ;;
        *)
            printf 'Invalid flake install scope: %s\n' "$scope" >&2
            return 1
            ;;
    esac
    [ -s "$module_source" ] || {
        printf 'The flake module is empty or missing.\n' >&2
        return 1
    }
    nix_available || {
        printf 'Nix is not installed.\n' >&2
        return 1
    }
    if ! nix_flakes_enabled; then
        _nix_enable_flakes || {
            printf 'Could not enable Nix flakes.\n' >&2
            return 1
        }
    fi

    if [ "$scope" = "system" ]; then
        nix_system_available || {
            printf 'The NixOS system configuration is not available.\n' >&2
            return 1
        }
        if ! _nix_ensure_system_config; then
            printf 'Could not integrate the LinuxToys Nix module into the system configuration.\n' >&2
            return 1
        fi
        directory=$(_nix_system_dir)
        flake="$directory/flake.nix"
        if [ ! -f "$flake" ]; then
            if [ ! -s "$flake_source" ] || ! _nix_publish_file "$flake_source" "$flake"; then
                printf 'Could not create the NixOS flake configuration.\n' >&2
                return 1
            fi
            _nix_record_generated_flake system "$directory" \
                "$(_nix_system_config_file)" "$(_nix_system_module)"
        else
            rm -f -- "$flake_source" 2>/dev/null || true
        fi
        _nix_apply_flake_module system "$module_source" || return $?
        _nix_sync_flake_registry || printf 'Warning: could not update the Nix flake Action Registry entries.\n' >&2
        _nix_cleanup_flake_wrappers || printf 'Warning: could not clean up unused Nix flake wrappers.\n' >&2
        return 0
    fi

    nix_home_manager_available || {
        printf 'Home Manager is not installed; choose the system scope instead.\n' >&2
        return 1
    }
    if ! _nix_ensure_hm_config; then
        printf 'Could not integrate the LinuxToys Nix module into the Home Manager configuration.\n' >&2
        return 1
    fi
    directory=$(_nix_hm_dir)
    flake="$directory/flake.nix"
    if [ ! -f "$flake" ]; then
        if [ ! -s "$flake_source" ] || ! _nix_publish_file "$flake_source" "$flake"; then
            printf 'Could not create the Home Manager flake configuration.\n' >&2
            return 1
        fi
        _nix_record_generated_flake home-manager "$directory" \
            "$(_nix_hm_config_file)" "$(_nix_hm_module)"
    else
        rm -f -- "$flake_source" 2>/dev/null || true
    fi
    _nix_apply_flake_module home-manager "$module_source" || return $?
    _nix_sync_flake_registry || printf 'Warning: could not update the Nix flake Action Registry entries.\n' >&2
    _nix_cleanup_flake_wrappers || printf 'Warning: could not clean up unused Nix flake wrappers.\n' >&2
    return 0
}

# Remove imported flakes by encoded state id. The Python bridge removes only
# those state records, renders the remaining module per affected scope and
# cleans wrapper trees that are no longer referenced. Registry operations for
# the removed ids are retired only after every affected scope rebuilds.
nix_remove_flakes() {
    local line scope module_source failed=0 output
    local -a ids=("$@") outputs
    (($#)) || {
        printf 'No imported Nix flake was selected.\n' >&2
        return 1
    }
    nix_available || {
        printf 'Nix is not installed.\n' >&2
        return 1
    }
    if ! nix_flakes_enabled; then
        _nix_enable_flakes || {
            printf 'Could not enable Nix flakes.\n' >&2
            return 1
        }
    fi
    output=$(_nix_flake_cli remove "${ids[@]}") || {
        printf 'Could not remove the imported Nix flake.\n' >&2
        return 1
    }
    if [ -z "$output" ]; then
        printf 'Could not determine which Nix module to rebuild for the removed flake.\n' >&2
        return 1
    fi
    mapfile -t outputs <<<"$output"
    for line in "${outputs[@]}"; do
        [ -n "$line" ] || continue
        IFS=$'\t' read -r scope module_source <<<"$line"
        case "$scope" in
            system|home-manager) ;;
            *)
                printf 'Invalid flake install scope: %s\n' "$scope" >&2
                [ -n "$module_source" ] && rm -f -- "$module_source"
                failed=1
                continue
                ;;
        esac
        if ! _nix_apply_flake_module "$scope" "$module_source"; then
            printf 'The %s Nix rebuild failed. The imported flake was not fully removed.\n' "$scope" >&2
            rm -f -- "$module_source" 2>/dev/null || true
            failed=1
            continue
        fi
        rm -f -- "$module_source" 2>/dev/null || true
    done
    if [ "$failed" -eq 0 ]; then
        _nix_sync_flake_registry --removed "${ids[@]}" \
            || printf 'Warning: could not update the Nix flake Action Registry entries.\n' >&2
        _nix_cleanup_flake_wrappers \
            || printf 'Warning: could not clean up unused Nix flake wrappers.\n' >&2
    fi
    return "$failed"
}

nix_subsystem_ensure() {
    local hm_backend=0 system_backend=0
    nix_available || return 1
    export PATH="$HOME/.nix-profile/bin:$HOME/.local/state/nix/profile/bin:$PATH"
    if ! nix_flakes_enabled; then
        _nix_enable_flakes || return 1
    fi
    _nix_ensure_zoneinfo \
        || printf 'Warning: could not create the /etc/zoneinfo compatibility link.\n' >&2
    mkdir -p -- "$(_nix_state_dir)" 2>/dev/null || true
    printf '1\n' >"$(_nix_state_dir)/allow-unfree" 2>/dev/null || true
    if ! nix_home_manager_available \
        && { ! nix_is_nixos || _nix_hm_paths_resolved; }; then
        _nix_install_home_manager || return 1
        _nix_reload_active_paths
    fi
    if nix_home_manager_available && _nix_hm_paths_resolved; then
        _nix_ensure_hm_config || return 1
        hm_backend=1
    fi
    if nix_system_available && _nix_system_paths_resolved; then
        _nix_ensure_system_config || return 1
        system_backend=1
    fi
    if [ "$hm_backend" -eq 0 ] && [ "$system_backend" -eq 0 ]; then
        if nix_home_manager_available && ! _nix_hm_paths_resolved; then
            _nix_paths_error home-manager
        fi
        if nix_system_available && ! _nix_system_paths_resolved; then
            _nix_paths_error system
        fi
        printf 'Neither an active Home Manager environment nor a NixOS system configuration is available.\n' >&2
        return 1
    fi
    if [ "$hm_backend" -eq 1 ]; then
        _nix_ensure_gpu_setup \
            || printf 'Warning: could not set up GPU acceleration for Nix packages.\n' >&2
    fi
    return 0
}

nix_remove_packages() {
    local scope attr target current_count changed=0
    local -a current kept
    (($#)) || return 1
    for scope in home-manager system; do
        if [ "$scope" = "system" ]; then
            _nix_system_paths_resolved || continue
        else
            _nix_hm_paths_resolved || continue
        fi
        mapfile -t current < <(_nix_module_read_packages "$scope")
        current_count=${#current[@]}
        (($current_count)) || continue
        kept=()
        for attr in "${current[@]}"; do
            local remove=0
            for target in "$@"; do
                [ "$attr" = "$target" ] && { remove=1; break; }
            done
            [ "$remove" -eq 1 ] || kept+=("$attr")
        done
        ((${#kept[@]} != current_count)) || continue
        if ! _nix_write_module "$scope" "${kept[@]}"; then
            printf 'Could not write the LinuxToys Nix module for %s.\n' "$scope" >&2
            return 1
        fi
        _nix_ensure_import "$scope" || return 1
        if ! _nix_rebuild "$scope"; then
            printf 'The %s Nix rebuild failed. The package was kept installed.\n' "$scope" >&2
            return 1
        fi
        changed=1
    done
    (($changed)) || {
        printf 'No LinuxToys-managed Nix package matched (already absent): %s\n' "$*" >&2
        return 0
    }
    _nix_sync_registry || printf 'Warning: could not update the Nix Action Registry entries.\n' >&2
    return 0
}

nix_import_manifest() {
    local json="$1" scope attr json_key failed=0
    local -a current incoming merged
    [ -s "$json" ] || {
        printf 'The Nix manifest package file is empty or missing.\n' >&2
        return 1
    }
    command -v jq >/dev/null 2>&1 || {
        printf 'jq is required to import Nix manifest packages.\n' >&2
        return 1
    }
    nix_subsystem_ensure || {
        printf 'The Nix subsystem could not be prepared.\n' >&2
        return 1
    }

    for scope in home-manager system; do
        incoming=()
        json_key="$scope"
        [ "$scope" = "home-manager" ] && json_key="home"
        while IFS= read -r attr; do
            [ -n "$attr" ] || continue
            if ! _nix_valid_attr "$attr"; then
                printf 'Refusing invalid Nix package name: %s\n' "$attr" >&2
                return 1
            fi
            incoming+=("$attr")
        done < <(jq -r --arg scope "$json_key" '.[$scope][]? // empty' "$json")
        ((${#incoming[@]})) || continue
        if [ "$scope" = "system" ] && ! _nix_system_paths_resolved; then
            _nix_paths_error system
            failed=1
            continue
        elif [ "$scope" != "system" ] && ! _nix_hm_paths_resolved; then
            _nix_paths_error home-manager
            failed=1
            continue
        fi

        mapfile -t current < <(_nix_module_read_packages "$scope")
        merged=("${current[@]}" "${incoming[@]}")
        mapfile -t merged < <(printf '%s\n' "${merged[@]}" | sed '/^$/d' | sort -u)
        if ! _nix_write_module "$scope" "${merged[@]}"; then
            printf 'Could not write the LinuxToys Nix module for %s.\n' "$scope" >&2
            failed=1
            continue
        fi
        if ! _nix_ensure_import "$scope"; then
            printf 'Could not import the LinuxToys Nix module for %s.\n' "$scope" >&2
            failed=1
            continue
        fi
        if ! _nix_rebuild "$scope"; then
            printf 'The %s Nix rebuild failed. Manifest packages were not applied.\n' "$scope" >&2
            failed=1
            continue
        fi
    done

    ((failed == 0)) || return 1
    _nix_sync_registry || printf 'Warning: could not update the Nix Action Registry entries.\n' >&2
    printf 'Nix manifest packages applied.\n'
    return 0
}

nix_apply_operations() {
    local queue lock scopes scope attr action
    local -a current merged applied_ids
    local -A wanted
    local failed=0 ids_json temporary
    queue=$(_nix_queue_file)
    [ -s "$queue" ] || {
        printf 'No pending Nix operations.\n'
        return 0
    }
    command -v jq >/dev/null 2>&1 || {
        printf 'jq is required to read the Nix queue.\n' >&2
        return 1
    }
    mkdir -p -- "$(dirname -- "$queue")" 2>/dev/null || true
    lock="${queue}.lock"
    exec 9>"$lock" || return 1
    if command -v flock >/dev/null 2>&1; then
        flock -w 10 9 || {
            printf 'Another Nix operation is already running.\n' >&2
            return 1
        }
    fi

    scopes=$(jq -r '.operations[].scope' "$queue" 2>/dev/null | sort -u)
    [ -n "$scopes" ] || return 0

    for scope in $scopes; do
        mapfile -t current < <(_nix_module_read_packages "$scope")
        wanted=()
        for attr in "${current[@]}"; do
            [ -n "$attr" ] && wanted["$attr"]=1
        done
        while IFS=$'\t' read -r attr action; do
            [ -n "$attr" ] && [ -n "$action" ] || continue
            if ! _nix_valid_attr "$attr"; then
                printf 'Refusing invalid Nix package name: %s\n' "$attr" >&2
                failed=1
                continue
            fi
            if [ "$action" = "install" ]; then
                wanted["$attr"]=1
            else
                unset 'wanted[$attr]'
            fi
        done < <(jq -r --arg scope "$scope" \
            '.operations[] | select(.scope == $scope) | [.attr, .action] | @tsv' "$queue")

        merged=()
        ((${#wanted[@]})) && mapfile -t merged < <(printf '%s\n' "${!wanted[@]}" | sort)

        # Every queued scope is rebuilt even when the module list did not change:
        # a previous failed rebuild leaves the module updated and the operation
        # queued, so retrying must not assume the profile is current.
        if ! _nix_write_module "$scope" "${merged[@]}"; then
            printf 'Could not write the LinuxToys Nix module for %s.\n' "$scope" >&2
            failed=1
            continue
        fi
        if ! _nix_ensure_import "$scope"; then
            printf 'Could not import the LinuxToys Nix module for %s.\n' "$scope" >&2
            failed=1
            continue
        fi
        if ! _nix_rebuild "$scope"; then
            printf 'The %s Nix rebuild failed. Pending operations were kept.\n' "$scope" >&2
            failed=1
            continue
        fi

        while IFS= read -r attr; do
            [ -n "$attr" ] && applied_ids+=("$attr")
        done < <(jq -r --arg scope "$scope" \
            '.operations[] | select(.scope == $scope) | .id' "$queue")
    done

    if [ "$failed" -ne 0 ]; then
        printf 'Nix package operations did not fully complete.\n' >&2
        return 1
    fi

    _nix_sync_registry || printf 'Warning: could not update the Nix Action Registry entries.\n' >&2

    if ((${#applied_ids[@]})); then
        ids_json=$(printf '%s\n' "${applied_ids[@]}" | jq -R . | jq -s .)
        temporary=$(mktemp "${queue}.XXXXXX") || return 1
        if jq --argjson ids "$ids_json" \
            '.operations = [.operations[] | select(.id as $id | ($ids | index($id)) | not)]' \
            "$queue" >"$temporary"; then
            mv -f -- "$temporary" "$queue"
        else
            rm -f -- "$temporary"
            return 1
        fi
    fi
    printf 'Nix package operations applied successfully.\n'
    return 0
}
