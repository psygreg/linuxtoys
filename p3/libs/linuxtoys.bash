## LinuxToys base shell library

# --- Zenity compatibility layer ---
_zenity_can_run() {
    [[ "$DISABLE_ZENITY" != "1" ]] || return 1
    type -P zenity >/dev/null 2>&1 || return 1
    [[ -n "$DISPLAY" || -n "$WAYLAND_DISPLAY" ]] || return 1
    return 0
}
_zenity_run() {
    _zenity_can_run || return 1
    GTK_A11Y=none NO_AT_BRIDGE=1 command zenity "$@" 2>/dev/null
}
# Wrapper for scripts that call zenity directly after sourcing this library.
zenity() {
    _zenity_run "$@"
}

# privilege escalation
askpass() {
    local mode="${1:-sudo}"
    shift || true

    local title="${1:-LinuxToys}"
    local _pass=""
    local max_attempts=3
    local attempts=0
    local marker="${TMPDIR:-/tmp}/linuxtoys_sudo_validated-${UID}"

    case "$mode" in
        password)
            # Explicit CLI mode.
            if [[ ${DISABLE_ZENITY:-0} == "1" ]]; then
                [[ -t 0 ]] || return 1

                read -rsp "Password: " _pass || return 1
                printf '\n' >&2
            else
                # GUI mode must use Zenity. Do not silently redirect password
                # input to the terminal viewer.
                _zenity_can_run || return 1

                _pass=$(
                    _zenity_run \
                        --password \
                        --title="$title"
                ) || return 1
            fi

            [[ -n "$_pass" ]] || return 1
            printf '%s' "$_pass"
            ;;

        sudo)
            # Only sudo itself can confirm whether the current authorization
            # is still valid. The marker must not bypass this check.
            if sudo -n true 2>/dev/null; then
                return 0
            fi

            # Remove a stale informational marker.
            rm -f "$marker"

            if [[ ${DISABLE_ZENITY:-0} == "1" ]]; then
                while (( attempts < max_attempts )); do
                    _pass=$(askpass password "$title") || return 1

                    if printf '%s\n' "$_pass" |
                        sudo -S -p '' -v >/dev/null 2>&1; then
                        unset _pass

                        if [[ -n ${LINUXTOYS_CHECKLIST:-} ]]; then
                            touch "$marker"
                        fi

                        return 0
                    fi

                    unset _pass
                    ((attempts++))

                    printf '❌ Wrong password. Attempts: %d/%d.\n' \
                        "$attempts" "$max_attempts" >&2
                done

                _msg error \
                    "❌ Wrong password or sudo failed (max attempts reached)." \
                    "Authentication Failed"
                exit 100
            fi

            _pass=$(askpass password "$title") || {
                _msg error \
                    "Password dialog cancelled or could not be displayed." \
                    "Authentication Failed"
                exit 100
            }

            if command -v sudo-rs >/dev/null 2>&1; then
                if ! printf '%s\n' "$_pass" |
                    sudo-rs -Sv >/dev/null 2>&1; then
                    unset _pass

                    _msg error \
                        "Wrong password or authentication failed." \
                        "Authentication Failed"
                    exit 100
                fi
            else
                if ! printf '%s\n' "$_pass" |
                    sudo -S -p '' -v >/dev/null 2>&1; then
                    unset _pass

                    _msg error \
                        "Wrong password or authentication failed." \
                        "Authentication Failed"
                    exit 100
                fi
            fi

            unset _pass

            if [[ -n ${LINUXTOYS_CHECKLIST:-} ]]; then
                touch "$marker"
            fi

            return 0
            ;;

        *)
            printf 'askpass: unknown mode: %s\n' "$mode" >&2
            return 2
            ;;
    esac
}

# Unified message handler
_msg() {
    local type="$1"
    local text="$2"
    local title="${3:-LinuxToys}"

    if [[ "$DISABLE_ZENITY" == "1" ]]; then
        echo "$text"
        return 0
    fi

    case "$type" in
        info)
            _zenity_run --info --text "$text" --width 360 --height 300 || echo "$text"
            ;;
        warning)
            _zenity_run --warning --text "$text" --width 360 --height 300 || echo "$text"
            ;;
        error)
            echo "$text"
            _zenity_run --error --title "$title" --text "$text" --width 360 --height 300 || true
            ;;
        *)       echo "$text" ;;
    esac
}

# message presets
question() {
    local title="$1"
    local text="$2"
    local width="${3:-360}"
    local height="${4:-300}"
    if [[ "$DISABLE_ZENITY" == "1" ]]; then
        return 0
    fi
    if _zenity_run --question --title "$title" --text "$text" --width "$width" --height "$height"; then
        return 0
    fi
    if [[ -t 0 ]]; then
        local _reply
        read -r -p "$text [y/N] " _reply
        [[ "$_reply" =~ ^[Yy]$ ]]
        return $?
    fi
    return 1
}
info() { 
    { ( [ -n "$CALLED_SCRIPT" ] && { [ "$1" = "$finishmsg" ] || [ "$1" = "$rebootmsg" ]; } ) && return 0; } || true
    _zenity_can_run || { echo "$1" && return 0; }
    if [ -n "$CHECKLIST_RUN" ]; then
        echo "$1"; 
    else
        _msg info "$1";
    fi
}
warn() { 
    _zenity_can_run || { echo "$1" && return 0; }
    if [ -n "$CHECKLIST_RUN" ]; then
        echo "WARN: $1"; 
    else
        _msg warning "$1";
    fi
}
error() {
    _zenity_can_run || { echo "$1" && return 1; }
    _msg error "$1" "Error"
    return 1
}
die() {
    _zenity_can_run || { echo "$1" && exit 1; }
    _msg error "$1" "Fatal Error"
    exit 1
}

# legacy function calls
zenpass() { askpass password "$@"; }
sudo_rq() { askpass sudo "$@"; }
zenask() { question "$@"; }
zenwrn() { warn "$@"; }
zeninf() { info "$@"; }
nonfatal() { error "$@"; }
fatal() { die "$@"; }

# sourcing
sysdetect() {
    source /etc/os-release || fatal "Failed to fetch OS information"
}
summon_helpers() {
    source "$SCRIPT_DIR/libs/helpers.lib" || fatal "Helpers library not found"
}
summon_optimizers() {
    source "$SCRIPT_DIR/libs/optimizers.lib" || fatal "Optimizers library not found"
}

# --- Utils ---
_lang_() {
    sysdetect
    local lang="${LANG:0:2}"
    local available=" am ar bn cs de el en es fa fi fr he hi id it ja ko ms nl pl pt ru sv sw ta th tl tr uk ur vi zh bg bs da hr hu is no sk sl sr nb az lv ga ne my sq tg uz hy ka km lo mn ro et lt "

    if [[ "$available" == *" $lang "* ]]; then
        langfile="$lang"
    else
        langfile="en"
    fi
    source "$SCRIPT_DIR/libs/lang/$langfile.lib"
}

# --- System Detection ---
sysdetect_once() { [[ -n ${ID:-} ]] || sysdetect; }
is_arch() { sysdetect_once && [[ ("$ID" =~ arch || "$ID" == "artix" || "$ID_LIKE" =~ arch) && "$ID" != "cachyos" ]]; }
is_cachy() { sysdetect_once && [[ "$ID" == "cachyos" ]]; }
is_fedora() { sysdetect_once && [[ "$ID" == "fedora" || ("$ID_LIKE" =~ "fedora" && "$ID" != "almalinux") ]] && [ ! -f /run/ostree-booted ]; }
is_ostree() { sysdetect_once && [[ ("$ID" == "fedora" || "$ID" == "rhel" || "$ID_LIKE" =~ "fedora" || "$ID_LIKE" =~ "rhel" || "$ID_LIKE" =~ "centos") ]] && command -v rpm-ostree &>/dev/null && [ -f /run/ostree-booted ]; }
is_debian() { sysdetect_once && [[ ("$ID" == "debian" || "$ID" == "deepin" || "$ID_LIKE" =~ debian) && ! ($ID == ubuntu || $ID_LIKE =~ ubuntu) ]]; }
is_ubuntu() { sysdetect_once && [[ "$ID" == "ubuntu" || "$ID_LIKE" =~ "ubuntu" ]]; }
is_suse() {
    suse_leap=""
    sysdetect_once 
    if [[ "$ID" == "suse" || "$ID" == "opensuse" || "$ID_LIKE" =~ "suse" ]]; then
        { [ "$ID" = "opensuse-leap" ] || [[ "$VERSION_ID" =~ ^[0-9]+\.[0-9]+$ ]]; } && suse_leap="1"
        return 0
    else
        return 1
    fi
}
is_solus() { sysdetect_once && [[ "$ID" == "solus" ]]; }
is_zorin() { sysdetect_once && [[ "$ID" == "zorin" ]]; }
is_rhel() { sysdetect_once && [[ ("$ID" == "rhel" || "$ID" == "centos" || "$ID" == "almalinux" || "$ID_LIKE" =~ "rhel") ]] && [ ! -f /run/ostree-booted ] && [[ "$ID" != "nobara" ]]; }
is_deepin() { sysdetect_once && [[ "$ID" == "deepin" ]]; }
is_manjaro() { sysdetect_once && [[ "$ID" == "manjaro" || "$ID_LIKE" =~ "manjaro" ]]; }
is_systemd() { [[ $(ps -p 1 -o comm= || readlink /sbin/init) =~ "systemd" ]] }

# GPU detection
is_nvidia() {
    local nvidiaGPU=$(lspci | grep -i 'nvidia')
    if [[ -n "$nvidiaGPU" ]]; then
        return 0
    else
        return 1
    fi
}
is_intel() {
    local dev modalias
    unset intel_arc INTEL_XE_SYSFS
    for dev in /sys/bus/pci/devices/*; do
        [[ -r "$dev/vendor" && -r "$dev/class" && -r "$dev/modalias" ]] || continue
        [[ "$(<"$dev/vendor")" == "0x8086" ]] || continue
        [[ "$(<"$dev/class")" == 0x03* ]] || continue
        intelGPU="yes"
        modalias=$(<"$dev/modalias")
        # Check whether the currently installed kernel's xe module explicitly supports this PCI device, fixes #1069
        if modprobe -R "$modalias" 2>/dev/null | grep -qx 'xe'; then
            intel_arc="yes"
            INTEL_XE_SYSFS="$dev"
        fi
    done
    [[ -n "$intelGPU" ]]
}
is_amd() {
    local amdGPU
    amdGPU=$(lspci | grep -Ei 'vga|3d|display' | grep -Ei 'amd|radeon')
    [[ -n "$amdGPU" ]]
}
is_hybridgpu() {
    if is_nvidia && ( is_intel || is_amd ); then
        return 0
    else
        return 1
    fi
}

# transaction map control
init_transmap() {
    [ -n "$TRANSMAP_PATH" ] && return 0
    TRANSMAP_CALL="1" && prep_tmp
    unset TRANSMAP_CALL
    { [ -d "$TEMPDIR" ] && { 
        { [ -n "$TRANSMAP_PATH" ] || TRANSMAP_PATH="$TEMPDIR/transmap"; }
        { [ -f "$TRANSMAP_PATH" ] || { : > "$TRANSMAP_PATH" && chmod 600 "$TRANSMAP_PATH"; } }
    } } || die "Failed to create transaction map"
}
_append_transmap() {
    init_transmap
    echo "$1" >> "$TRANSMAP_PATH" 2>/dev/null
}

# file preparations
prep_edit() {
    for target in "$@"; do
        [ -f "$target" ] || { _append_transmap "WARN: expected $target not found"; prep_create "$target"; continue; }
        copy_ -r "$target" "$target".bak
        _append_transmap "edited $target"
    done
}
prep_create() {
    for target in "$@"; do
        [ ! -f "$target" ] || { _append_transmap "WARN: unexpected $target already exists"; prep_edit "$target"; continue; }
        { mkdir -p "$(dirname "$target")" && touch "$target"; } 2>/dev/null \
        || { sudo mkdir -p "$(dirname "$target")" && sudo touch "$target"; } \
        || fatal "Failed to create: $target"
        _append_transmap "created $target"
    done
}
prep_rm() {
    for target in "$@"; do
        { [ -f "$target" ] || [ -d "$target" ]; } || { _append_transmap "WARN: expected $target not found"; continue; }
        move_ "$target" "$target".bak
        _append_transmap "removed $target"
    done
}
prep_tmp() {
    [ -d "$TEMPDIR" ] && [ -w "$TEMPDIR" ] && cd "$TEMPDIR" || \
        { mkdir -p /tmp/linuxtoys && [ -w /tmp/linuxtoys ] && cd /tmp/linuxtoys && TEMPDIR="/tmp/linuxtoys"; } || \
        { TEMPDIR="$HOME/.cache/linuxtoys/tmp" && { [ -n "$TRANSMAP_PATH" ] || TRANSMAP_PATH="$TEMPDIR/transmap"; } && prep_tmp_noram; }
}
prep_tmp_noram () {
    { mkdir -p "$HOME/.cache/linuxtoys/tmp" && cd "$HOME/.cache/linuxtoys/tmp"; } || fatal "Failed to create tempdir"
    [ -z "$TRANSMAP_CALL" ] && _append_transmap "tmpdir_noram $HOME/.cache/linuxtoys/tmp"
}
prep_dir() {
    for dir in "$@"; do
        if [ ! -d "$dir" ]; then
            { mkdir -p "$dir" 2>/dev/null || sudo mkdir -p "$dir"; } || fatal "Failed to create $dir"
            _append_transmap "created $dir"
        fi
    done
}
prep_dir_edit() {
    for dir in "$@"; do
        [ -d "$dir" ] || { _append_transmap "WARN: unexpected $dir doesnt exist"; prep_dir "$dir"; continue; }
        copy_ -r "$dir" "$dir.bak"
        _append_transmap "edited $dir"
    done
}
copy_() {
    local -a flags=()
    local -a args=()
    for arg in "$@"; do
        if [[ "$arg" == -* ]]; then
            flags+=("$arg")
        else
            args+=("$arg")
        fi
    done
    
    local dest="${args[-1]}"
    local -a sources=("${args[@]:0:${#args[@]}-1}")
    for src in "${sources[@]}"; do
        [ -e "$src" ] || fatal "Source $src not found"
        { cp "${flags[@]}" "$src" "$dest" 2>/dev/null || sudo cp "${flags[@]}" "$src" "$dest"; } || fatal "Failed to copy $src to $dest"
    done
}
move_() {
    local -a flags=()
    local -a args=()
    for arg in "$@"; do
        if [[ "$arg" == -* ]]; then
            flags+=("$arg")
        else
            args+=("$arg")
        fi
    done
    
    local dest="${args[-1]}"
    local -a sources=("${args[@]:0:${#args[@]}-1}")
    for src in "${sources[@]}"; do
        [ -e "$src" ] || fatal "Source $src not found"
        { mv "${flags[@]}" "$src" "$dest" 2>/dev/null || sudo mv "${flags[@]}" "$src" "$dest"; } || fatal "Failed to move $src to $dest"
    done
}

# Package Management

# Guard against pacman database lock (/var/lib/pacman/db.lck).
# If pacman is actively running, abort with a clear message. If the lock is
# stale (no pacman process holding it), remove it and continue.
pacman_lock_guard () {
    local PACMAN_ACTIVE=false
    if [ -f /var/lib/pacman/db.lck ]; then
        if pgrep -x pacman >/dev/null 2>&1; then
            PACMAN_ACTIVE=true
        elif command -v lsof >/dev/null 2>&1 && lsof /var/lib/pacman/db.lck >/dev/null 2>&1; then
            PACMAN_ACTIVE=true
        fi
        if [ "$PACMAN_ACTIVE" = true ]; then
            die "Another package operation is in progress (pacman is running). Please wait for it to finish, or close it manually and retry."
        else
            warn "Stale pacman lock detected. Removing /var/lib/pacman/db.lck"
            { { [ "$UPD_SERVICE" = "1" ] && rm -f /var/lib/pacman/db.lck; } || sudo rm -f /var/lib/pacman/db.lck; } || die "Failed to remove stale lock. Run: sudo rm /var/lib/pacman/db.lck"
        fi
    fi
}
interrupted_apt_guard () {
    if [ -n "$(dpkg --audit 2>/dev/null)" ]; then
        info "An interrupted package operation was detected. Attempting recovery..."
        { { [ "$UPD_SERVICE" = "1" ] && dpkg --configure -a; } || sudo dpkg --configure -a; } || die "Failed to recover interrupted dpkg operation. Manual user intervention required."
        { { [ "$UPD_SERVICE" = "1" ] && apt --fix-broken install -y; } || sudo apt --fix-broken install -y; } || die "Failed to fix broken packages. Manual user intervention required."
    fi
}

pkg_exists () {
    pkg_found=()
    pkg_notfound=()
    
    for pak in "$@"; do
        if is_debian || is_ubuntu; then
            if dpkg -s "$pak" &>/dev/null; then
                pkg_found+=("$pak")
            else
                pkg_notfound+=("$pak")
            fi
        elif is_arch || is_cachy || is_manjaro; then
            if pacman -Qi "$pak" &>/dev/null; then
                pkg_found+=("$pak")
            else
                pkg_notfound+=("$pak")
            fi
        elif is_fedora || is_ostree || is_suse || is_rhel; then
            if rpm -qi "$pak" &>/dev/null; then
                pkg_found+=("$pak")
            else
                pkg_notfound+=("$pak")
            fi
        elif is_solus; then     
            if eopkg list-installed | grep -qw "$pak"; then
                pkg_found+=("$pak")
            else
                pkg_notfound+=("$pak")
            fi
        fi
    done
}
pkg_install () {
    # Handle --ignore-appends and --ostreecheck flags
    local _ignore_appends=0
    local _ostreecheck=0
    local -a _filtered_args=()
    for arg in "$@"; do
        if [[ "$arg" == "--ignore-appends" ]]; then
            _ignore_appends=1
        elif [[ "$arg" == "--ostreecheck" ]]; then
            _ostreecheck=1
        else
            _filtered_args+=("$arg")
        fi
    done
    
    pkg_exists "${_filtered_args[@]}"
    [[ ${#pkg_notfound[@]} -eq 0 ]] && return 0
    local to_install="${pkg_notfound[*]}"
    if is_debian || is_ubuntu; then
        interrupted_apt_guard
        sudo apt-get install -y "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
    elif is_arch || is_cachy || is_manjaro; then
        if ! is_manjaro; then
            if ! pacman-conf --repo-list 2>/dev/null | grep -qx 'extra'; then 
                prep_edit /etc/pacman.conf
                printf '\n[extra]\nInclude = /etc/pacman.d/mirrorlist\n' |
                    sudo tee -a /etc/pacman.conf >/dev/null
            fi
        fi
        local _pacman_pkgs=()
        local _paru_pkgs=()
        for pak in "${pkg_notfound[@]}"; do
            # Use an exact sync-db lookup so AUR-only packages are not misclassified.
            if pacman -Si "$pak" &>/dev/null; then
                _pacman_pkgs+=("$pak")
            else
                _paru_pkgs+=("$pak")
            fi
        done
        local to_install_pacman="${_pacman_pkgs[*]}"
        local to_install_paru="${_paru_pkgs[*]}"
        # check for lock before installing
        if [ -n "$to_install_pacman" ]; then
            if is_manjaro; then
                pamac install --no-confirm "${_pacman_pkgs[@]}" || fatal "Failed to install $to_install_pacman"
                [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install_pacman"
            else
                pacman_lock_guard
                sudo pacman -S --noconfirm "${_pacman_pkgs[@]}" || fatal "Failed to install $to_install_pacman"
                [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install_pacman"
            fi
        fi
        if [ -n "$to_install_paru" ]; then
            if is_manjaro; then
                pamac build --no-confirm "${_paru_pkgs[@]}" || die "Failed to install $to_install_paru"
            else
                if ! command -v paru &>/dev/null; then
                    if question "Installer" "$msg305" 300 300; then
                        if pacman -Si paru &>/dev/null; then
                            sudo pacman -S --noconfirm paru || fatal "Failed to install paru"
                            [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg paru"
                        else
                            sudo pacman -S --needed base-devel || fatal "Failed to install base-devel"
                            [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg base-devel"
                            prep_tmp
                            git clone https://aur.archlinux.org/paru.git
                            cd paru || fatal "Failed to install paru"
                            makepkg -si
                            [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg paru"
                        fi
                    else
                        die "User cancelled installation of paru"
                    fi
                fi
                paru -S -a --noconfirm --skipreview "${_paru_pkgs[@]}" || die "Failed to install $to_install_paru"
                [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install_paru"
            fi
        fi
    elif is_ostree; then
        sudo rpm-ostree install "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
        # Perform ostree check if requested and packages were actually installed
        if [[ $_ostreecheck -eq 1 && ${#pkg_notfound[@]} -gt 0 ]]; then
            zenwrn "$msgostreepending"
            exit 100
        fi
    elif is_fedora || is_rhel; then
        sudo dnf install -y "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
    elif is_suse; then
        sudo zypper in -y "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
    elif is_solus; then
        sudo eopkg it -y "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
    fi
}
pkg_flat() {
    local _skip_user=0
    local -a _flatpak_args=()
    for arg in "$@"; do
        if [[ "$arg" == "--skip-user" ]]; then
            _skip_user=1
        else
            _flatpak_args+=("$arg")
        fi
    done
    if ! command -v flatpak &>/dev/null || ! flatpak remote-list | grep -q flathub; then
        call_script flathub
    fi
    local flatpak_scope="--user"
    if [[ $_skip_user -eq 1 ]]; then
        flatpak_scope="--system"
    elif flatpak remote-list --system 2>/dev/null | grep -q flathub && \
       ! flatpak remote-list --user 2>/dev/null | grep -q flathub; then
        flatpak_scope="--system"
    fi

    # Extract base package names (remove version/architecture specifications)
    local -a _flatpak_basenames=()
    for arg in "${_flatpak_args[@]}"; do
        local basename="${arg%%/*}"
        _flatpak_basenames+=("$basename")

        # Only mark applications that weren't already installed
        if ! flatpak info "$flatpak_scope" "$arg" &>/dev/null; then
            _flatpak_new+=("$arg")
        fi
    done

    if [ "$flatpak_scope" = "--user" ]; then
        flatpak install --or-update "$flatpak_scope" -y flathub "${_flatpak_args[@]}" || fatal "Failed to install flatpak packages ${_flatpak_args[*]}"
        for basename in "${_flatpak_basenames[@]}"; do
            flatpak list "$flatpak_scope" | grep -q "$basename" || fatal "Failed to install flatpak package $basename"
        done
    else
        flatpak install --or-update "$flatpak_scope" -y flathub "${_flatpak_args[@]}" 2>/dev/null || { sudo_rq && sudo flatpak install --or-update "$flatpak_scope" -y flathub "${_flatpak_args[@]}"; } 
        for basename in "${_flatpak_basenames[@]}"; do
            flatpak list "$flatpak_scope" | grep -q "$basename" || fatal "Failed to install flatpak package $basename"
        done
    fi
    if [[ ${#_flatpak_new[@]} -gt 0 ]]; then
        _append_transmap "flatpak ${_flatpak_new[*]}"
    fi
}
pkg_fromfile () {
    # Handle --ostreecheck flag
    local _ostreecheck=0
    local -a _filtered_args=()
    for arg in "$@"; do
        if [[ "$arg" == "--ostreecheck" ]]; then
            _ostreecheck=1
        else
            _filtered_args+=("$arg")
        fi
    done
    
    # Use filtered args for the rest of the function
    set -- "${_filtered_args[@]}"
    
    if [[ "$1" == *.flatpak ]]; then
        if ! which flatpak &>/dev/null || ! flatpak remote-list | grep -q flathub; then
            summon_helpers
            sudo_rq
            flatpak_in_lib
        fi
        local flatpak_file="$1"
        local flatpak_scope="--user"
        if flatpak remote-list --system 2>/dev/null | grep -q flathub && \
           ! flatpak remote-list --user 2>/dev/null | grep -q flathub; then
            flatpak_scope="--system"
        fi
        local _flatpak_stderr
        if ! flatpak install "$flatpak_scope" --noninteractive "$flatpak_file" &>/dev/null; then  # force --system install
            _flatpak_stderr=$(
                sudo flatpak install --system --noninteractive "$flatpak_file" 2>&1 >/dev/null
            ) || fatal "Failed to install flatpak from file: $flatpak_file due to: $_flatpak_stderr"
        fi
        _append_transmap "pkg file $flatpak_file"
        return 0
    fi
    
    if is_debian || is_ubuntu; then
        { sudo apt-get -o APT::Sandbox::User=root install -y "${@}" || sudo dpkg -i "${@}"; } || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
    elif { is_arch || is_cachy; } && ! is_manjaro; then
        # check for lock before installing local package
        pacman_lock_guard
        if sudo pacman -U "${@}"; then
            _append_transmap "pkg file $*"
        else
            if [ -f PKGBUILD ]; then
                local pkgname=$(grep "^pkgname=" PKGBUILD | head -1 | cut -d'=' -f2 | tr -d "'" '"')
                makepkg -si || fatal "Failed to build and install package $pkgname"
                _append_transmap "pkg file $pkgname"
            else
                fatal "Failed to install package $*"
            fi
        fi
    elif is_manjaro; then
        { pamac install --no-confirm "./${*}" && _append_transmap "pkg file $*"; } || fatal "Failed to install package $*"
    elif is_ostree; then
        sudo rpm-ostree install "${@}" || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
        # Perform ostree check if requested
        if [[ $_ostreecheck -eq 1 ]]; then
            zenwrn "$msgostreepending"
            exit 100
        fi
    elif is_fedora || is_rhel; then
        sudo dnf install -y "${@}" || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
    elif is_suse; then
        sudo zypper in -y "${@}" || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
    elif is_solus; then
        sudo eopkg it -y "${@}" || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
    fi
}
pkg_remove () {
    pkg_exists "$@"
    [[ ${#pkg_found[@]} -eq 0 ]] && return 0
    
    local to_remove="${pkg_found[*]}"
    
    if is_debian || is_ubuntu; then
        sudo apt-get remove -y --allow-unauthenticated "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    elif { is_arch || is_cachy; } && ! is_manjaro; then
        # check for lock before removing (stale lock otherwise aborts pacman -Rsn)
        pacman_lock_guard
        sudo pacman -Rsn --noconfirm "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    elif is_manjaro; then
        pamac remove --no-confirm "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    elif is_ostree; then
        sudo rpm-ostree uninstall "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    elif is_fedora || is_rhel ; then
        sudo dnf remove -y "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    elif is_suse; then
        sudo zypper rm -y "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    elif is_solus; then
        sudo eopkg rmf -y "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    fi
    _append_transmap "pkg rm $to_remove"
}
pkg_rm () { pkg_remove "$@"; }
pkg_appimage () {
    ( is_ubuntu || is_debian ) && {
        if [ "$VERSION_CODENAME" = "bookworm" ]; then 
            pkg_install libfuse2  # workaround for debian 12
        else
            pkg_install libfuse2t64; 
        fi
    }
    { ( is_fedora || is_ostree || is_rhel ) && pkg_install fuse; }
    { ( is_arch || is_cachy || is_solus ) && pkg_install fuse2; }
    
    prep_dir "$HOME/AppImages"
    
    if is_systemd; then
        # Use Gear Lever for systemd systems
        call_script gearlever
        local output
        output=$(echo "y" | flatpak run it.mijorus.gearlever --integrate "$@" 2>&1) || {
            echo "$output"
            fatal "Failed to integrate AppImage."
        }
        local appimage_name
        appimage_name=$(
            find "$HOME/AppImages" -maxdepth 1 -type f -printf '%T@ %f\n' 2>/dev/null |
                sort -nr |
                head -n1 |
                cut -d' ' -f2-
        )
        if [[ -n "$appimage_name" ]]; then
            _append_transmap "appimage $appimage_name"
        else
            nonfatal "Could not determine integrated AppImage filename."
        fi
    else
        # Manual integration for non-systemd systems
        for appimage_file in "$@"; do
            [[ -f "$appimage_file" ]] || fatal "AppImage file not found: $appimage_file"
            local appimage_basename=$(basename "$appimage_file")
            prep_create "$HOME/AppImages/$appimage_basename"
            cp -f "$appimage_file" "$HOME/AppImages/$appimage_basename"
            chmod +x "$HOME/AppImages/$appimage_basename"
            
            prep_tmp_noram
            local extract_dir
            extract_dir="$HOME/.cache/linuxtoys/tmp" || fatal "Failed to create temp directory for extraction"
            cd "$extract_dir" || fatal "Failed to change to temp directory"
            "$HOME/AppImages/$appimage_basename" --appimage-extract >/dev/null 2>&1 || \
                { nonfatal "Failed to extract AppImage: $appimage_basename"; rm -rf "$extract_dir"; continue; }
            local desktop_file
            desktop_file=$(find squashfs-root -name "*.desktop" -type f 2>/dev/null | head -1)
            if [[ -n "$desktop_file" && -f "$desktop_file" ]]; then
                prep_dir "$HOME/.local/share/applications"
                local desktop_basename=$(basename "$desktop_file")
                prep_create "$HOME/.local/share/applications/$desktop_basename"
                cp -f "$desktop_file" "$HOME/.local/share/applications/$desktop_basename" || \
                    fatal "Failed to copy desktop file"
            fi
            local icon_file
            icon_file=$(find squashfs-root \( -name "*.png" -o -name "*.svg" -o -name "*.xpm" \) -type f 2>/dev/null | head -1)
            if [[ -n "$icon_file" && -f "$icon_file" ]]; then
                prep_dir "$HOME/.local/share/icons"
                local icon_basename=$(basename "$icon_file")
                prep_create "$HOME/.local/share/icons/$icon_basename"
                cp -f "$icon_file" "$HOME/.local/share/icons/$icon_basename" || \
                    nonfatal "Failed to copy icon file"
            fi
            _append_transmap "appimage $appimage_basename"
        done
    fi
}
pkg_appimage_rm () {
    if is_systemd; then
        # Use Gear Lever for removal on systemd systems
        cd "$HOME/AppImages"
        echo "y" | flatpak run it.mijorus.gearlever --remove "${@}"
        _append_transmap "appimage rm $*"
    else
        # Manual removal for non-systemd systems
        for appimage_file in "$@"; do
            local appimage_basename=$(basename "$appimage_file")
            local appimage_name_without_ext="${appimage_basename%.*}"
            
            # Remove from AppImages directory
            if [[ -f "$HOME/AppImages/$appimage_basename" ]]; then
                rm -f "$HOME/AppImages/$appimage_basename"
                _append_transmap "appimage rm $appimage_basename"
            fi
        done
    fi
}
pkg_npm () {
    if ! command -v npm &>/dev/null; then
        sudo_rq
        { ( is_ubuntu || is_debian || is_suse ) && pkg_install npm; }
        { ( is_fedora || is_ostree ) && pkg_install nodejs-npm; }
        { ( is_rhel ) && rpmfusion_chk && pkg_install nodejs-npm; }
        { ( is_arch || is_cachy ) && pkg_install npm; }
    fi
    # PATH config
    for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$rc" ]; then
            # Check if PATH modification for .npm-global/bin already exists in the file
            if ! grep -E "PATH=.*/home/$USER/.npm-global/bin|/home/$USER/\.npm-global/bin" "$rc" > /dev/null 2>&1; then
                prep_edit "$rc"
                echo "export PATH=\"/home/$USER/.npm-global/bin:\$PATH\"" >> "$rc"
                export PATH="/home/$USER/.npm-global/bin:$PATH" # handle current term viewer only in case it's not already in PATH
            fi
        fi
    done
    # for fish shells
    fish_config="$HOME/.config/fish/config.fish"
    if [ -f "$fish_config" ]; then
        if ! grep -E "set.*PATH.*/home/$USER/.npm-global/bin|/home/$USER/\.npm-global/bin" "$fish_config" > /dev/null 2>&1; then
            prep_edit "$fish_config"
            echo "set -gx PATH /home/$USER/.npm-global/bin \$PATH" >> "$fish_config"
            export PATH="/home/$USER/.npm-global/bin:$PATH"
        fi
    fi  

    local -a flags=()
    local -a packages=()
    # Separate flags from package names, filtering out -g flag
    for arg in "$@"; do
        if [[ "$arg" == -* ]]; then
            if [[ "$arg" != "-g" && "$arg" != "--global" ]]; then
                flags+=("$arg")
            fi
        else
            packages+=("$arg")
        fi
    done
    for pkg in "${packages[@]}"; do
        if ! npm list -g "$pkg" &>/dev/null; then
            { npm install -g "${flags[@]}" "$pkg" 2>/dev/null || ( sudo_rq && sudo npm install -g "${flags[@]}" "$pkg" ) } || fatal "Failed to install npm package $pkg"
            _append_transmap "npm $pkg"
        fi
    done
}
pkg_bun () {
    if ! command -v bun &>/dev/null; then
        sudo_rq
        { curl -fsSL https://bun.sh/install | bash; } || fatal "Failed to install bun"
    else
        bun upgrade
    fi
    for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$rc" ]; then
            # Check if PATH modification for .bun/bin already exists in the file
            if ! grep -E "PATH=.*\/home\/$USER/.bun/bin|/home/$USER/.bun/bin" "$rc" > /dev/null 2>&1; then
                prep_edit "$rc"
                echo "export PATH=\"/home/$USER/.bun/bin:\$PATH\"" >> "$rc"
                export PATH="/home/$USER/.bun/bin:$PATH" # handle current term viewer only in case it's not already in PATH
            fi
        fi
    done
    # for fish shells
    fish_config="$HOME/.config/fish/config.fish"
    if [ -f "$fish_config" ]; then
        if ! grep -E "set.*PATH.*/home/$USER/.bun/bin|/home/$USER/.bun/bin" "$fish_config" > /dev/null 2>&1; then
            prep_edit "$fish_config"
            echo "set -gx PATH /home/$USER/.bun/bin \$PATH" >> "$fish_config"
            export PATH="/home/$USER/.bun/bin:$PATH"
        fi
    fi
    for pkg in "$@"; do
        if ! bun list -g "$pkg" &>/dev/null; then
            bun install -g "$pkg" || fatal "Failed to install bun package $pkg"
            _append_transmap "bun $pkg"
        fi
    done
}

# bootloader update
bootloader_upd() {
    if ! is_ostree; then
        local exit_status
        if is_fedora || is_suse || is_rhel; then
            sudo grub2-mkconfig -o /boot/grub2/grub.cfg || die "Unable to update bootloader"
            _append_transmap "updated bootloader"
        elif is_arch || is_cachy; then
            if command -v limine-mkinitcpio >/dev/null 2>&1; then
                sudo limine-mkinitcpio || die "Unable to update bootloader"
            elif command -v sdboot-manage >/dev/null 2>&1 &&
                bootctl is-installed >/dev/null 2>&1; then
                sudo sdboot-manage gen || die "Unable to update bootloader"
            elif command -v grub-mkconfig >/dev/null 2>&1; then
                sudo grub-mkconfig -o /boot/grub/grub.cfg || die "Unable to update bootloader"
            elif command -v bootctl >/dev/null 2>&1 && bootctl is-installed >/dev/null 2>&1; then
                sudo bootctl update || die "Unable to update bootloader"
            else
                die "Unable to determine installed bootloader"
            fi
            _append_transmap "updated bootloader"
        elif is_ubuntu; then
            sudo update-grub || fatal "Unable to update bootloader"
            _append_transmap "updated bootloader"
        elif is_debian; then 
            {
                sudo update-grub && exit_status=0 || {
                    if sudo bootctl is-installed >/dev/null 2>&1; then
                        sudo bootctl update
                        exit_status=0
                    else
                        exit_status=1
                    fi
                }
            } 
            [ "$exit_status" -eq 0 ] || fatal "Unable to update bootloader"
            _append_transmap "updated bootloader"
        elif is_solus; then
            { sudo clr-boot-manager update || sudo grub-mkconfig -o /boot/grub/grub.cfg; } || fatal "Unable to update bootloader"
            _append_transmap "updated bootloader"
        fi
    else
        return 0
    fi
}
initramfs_upd() {
    if is_debian; then
        sudo update-initramfs -u || fatal "Failed to update initramfs"
        _append_transmap "updated initramfs"
    elif is_arch || is_cachy; then
        sudo mkinitcpio -P || fatal "Failed to update mkinitcpio"
        _append_transmap "updated initramfs"
    elif is_fedora || is_suse || is_rhel ; then
        sudo dracut -f --regenerate-all || fatal "Failed to update dracut"
        _append_transmap "updated initramfs"
    fi
}
kargs_upd() {
    for arg in "$@"; do
        sudo rpm-ostree kargs --append="$arg" || fatal "Failed to update rpm-ostree kargs"
        _append_transmap "updated kargs $arg"
    done
}
grubbyargs_upd () {
    if ! which grubby &> /dev/null; then
        pkg_install grubby
    fi
    for arg in "$@"; do
        sudo grubby --args="$arg" --update-kernel ALL || fatal "Failed to update grubby kargs"
        _append_transmap "updated grubby kargs $arg"
    done
}

# systemd service operations
sysd_enable() {
    for svc in "$@"; do
        sudo systemctl enable "$svc" || fatal "Failed to enable service $svc"
        _append_transmap "sysd enabled $svc"
    done
}
sysd_disable() {
    for svc in "$@"; do
        sudo systemctl disable "$svc" || fatal "Failed to disable service $svc"
        _append_transmap "sysd disabled $svc"
    done
}
sysd_start() {
    for svc in "$@"; do
        sudo systemctl start "$svc" || fatal "Failed to start service $svc"
        _append_transmap "sysd started $svc"
    done
}
sysd_stop() {
    for svc in "$@"; do
        sudo systemctl stop "$svc" || fatal "Failed to stop service $svc"
        _append_transmap "sysd stopped $svc"
    done
}
sysd_enable_usr() {
    for svc in "$@"; do
        systemctl --user enable "$svc" || fatal "Failed to enable service $svc"
        _append_transmap "sysd usermode enabled $svc"
    done
}
sysd_disable_usr() {
    for svc in "$@"; do
        systemctl --user disable "$svc" || fatal "Failed to disable service $svc"
        _append_transmap "sysd usermode disabled $svc"
    done
}
sysd_start_usr() {
    for svc in "$@"; do
        systemctl --user start "$svc" || fatal "Failed to start service $svc"
        _append_transmap "sysd usermode started $svc"
    done
}
sysd_stop_usr() {
    for svc in "$@"; do
        systemctl --user stop "$svc" || fatal "Failed to stop service $svc"
        _append_transmap "sysd usermode stopped $svc"
    done
}

# shell change
shell_change() {
    sudo chsh -s "$*" || fatal "Failed to change shell: $*"
    _append_transmap "chsh $*"
}

# distrobox container
distrobox_created() {
    _append_transmap "distrobox $*"
}

# rclone mountpoint
rclone_mount() {
    local remote="$1"
    local mount_point="$2"
    if [[ "$remote" != *:* ]]; then
        remote="${remote}:"
    fi
    rclone mount "$remote" "$mount_point" --daemon || fatal "Failed to create rclone mountpoint"
    _append_transmap "rclone mounted $remote at $mount_point" 
}

# swapfile creation
swapfile_created () {
    _append_transmap "swapfile $*"
}

# script calling -- used for scripts to call other scripts from the app.
call_script () {
    local script_name="$1"
    [[ -z "$script_name" ]] && die "call_script: script name not provided"
    [[ -z "$CACHE_DIR" ]] && die "call_script: CACHE_DIR environment variable not set"

    script_name="${script_name%.sh}"
    local script_file="${script_name}.sh"

    local found_script
    found_script=$(find "$CACHE_DIR" -maxdepth 3 -type f \
        -name "$script_file" 2>/dev/null | head -n1)

    [[ -n "$found_script" && -f "$found_script" ]] ||
        die "call_script: Script '$script_name' not found in $CACHE_DIR"

    shift
    # Get the script's registry/display name.
    local script_display_name
    script_display_name=$(
        sed -n 's/^# name:[[:space:]]*//p' "$found_script" |
        head -n1
    )
    [[ -n "$script_display_name" ]] ||
        script_display_name="$script_name"

    # Keep track of the caller's transaction.
    local parent_transmap="$TRANSMAP_PATH"

    # Create an independent transaction for the called script.
    local child_transmap
    child_transmap=$(mktemp "/tmp/linuxtoys-called-XXXXXX.transmap") ||
        die "call_script: Failed to create child transmap"

    (
        export CALLED_SCRIPT=1
        export TRANSMAP_PATH="$child_transmap"

        bash "$found_script" "$@"
    )
    local status=$?

    if [[ $status -eq 0 ]]; then
        # Commit the called script's transaction independently.
        if [[ -s "$child_transmap" ]]; then
            python3 "$SCRIPT_DIR/app/term_registry.py" \
                save "$script_display_name" "$child_transmap" ||
                die "Failed to save transaction for $script_display_name"
        fi

        rm -f "$child_transmap"
        return 0
    fi

    # Failed child: merge its changes into the caller's transaction,
    # allowing the normal top-level auto-revert to undo them.
    if [[ -s "$child_transmap" ]]; then
        if [[ -n "$parent_transmap" ]]; then
            cat "$child_transmap" >> "$parent_transmap"
        else
            init_transmap
            cat "$child_transmap" >> "$TRANSMAP_PATH"
        fi
    fi

    rm -f "$child_transmap"
    return "$status"
}

secureboot_check() {
    local _ubuntumok=0
    for arg in "$@"; do
        if [[ "$arg" == "--ubuntumok" ]]; then
            _ubuntumok=1
        fi
    done
    sudo mokutil --sb-state | grep -q "SecureBoot enabled" || return 0
    if is_fedora || is_rhel || is_ostree; then
        call_script modsign
    elif is_ubuntu; then
        { sudo mokutil --test-key /var/lib/shim-signed/mok/MOK.der | grep -q "not enrolled" && \
            { sudo update-secureboot-policy --enroll-key || die "Failed to update secure boot policy"; }; } || true
    elif is_debian; then
        if [ "$_ubuntumok" -eq 1 ] && [ ! -f /var/lib/shim-signed/mok/MOK.der ]; then
            prep_dir /var/lib/shim-signed/mok/
            openssl req -nodes -new -x509 -newkey rsa:2048 -keyout MOK.priv -outform DER -out MOK.der -days 36500 -subj "/CN=LinuxToys/"
            openssl x509 -inform der -in MOK.der -out MOK.pem
            sudo mokutil --import /var/lib/shim-signed/mok/MOK.der || die "Failed to create ubuntu-like key"
        else
            { sudo mokutil --test-key /var/lib/dkms/mok.pub | grep -q "not enrolled" && \
                { sudo mokutil --import /var/lib/dkms/mok.pub || die "Failed to update secure boot policy"; }; } || true
        fi
    fi
}