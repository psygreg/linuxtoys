# library of helpers and repository checkers
source "$SCRIPT_DIR/libs/linuxtoys.lib"

# Helper function to fetch from multiple sources with fallback
fetch_from_mirror () {
    local filename="$1"
    local github_url="$2"
    local gitea_url="$3"

    if wget "$github_url" -O "$filename"; then
        return 0
    fi
    if wget "$gitea_url" -O "$filename"; then
        return 0
    fi
    return 1
}

# --- Multilib ---
multilib_chk() {
    pacman -Slq multilib &>/dev/null && return 0;

    printf "\n[multilib]\nInclude = /etc/pacman.d/mirrorlist\n" | sudo tee -a /etc/pacman.conf >/dev/null

    if sudo pacman -Syy && pacman -Slq multilib &>/dev/null; then
        return 0
    else
        _msg error "Failed to enable multilib repository. Please check /etc/pacman.conf manually."
        return 1
    fi
}

# --- CLInfo Test ---
clinfo_chk () {
    if ! command -v clinfo &>/dev/null; then
        _msg info "clinfo not found, installing..."
        sudo_rq
        pkg_install clinfo
    fi
    # Check if OpenCL acceleration is available
    local platform_count
    platform_count=$(clinfo 2>&1 | grep -m1 "Number of platforms" | grep -oE "[0-9]+$")

    if [ -n "$platform_count" ] && [ "$platform_count" -ge 1 ]; then
        _msg info "OpenCL acceleration is available ($platform_count platform(s) found)"
        return 0
    else
        _msg error "OpenCL acceleration is not available"
        return 1
    fi
}

# enable non-free and contrib repos on debian
enable_debian_nonfree () {
    if is_debian; then
        local updated=0
        if ! grep -qE "contrib" /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources 2>/dev/null; then
            if [ -f /etc/apt/sources.list ]; then
                prep_edit /etc/apt/sources.list
                sudo sed -i 's/main$/main contrib/' /etc/apt/sources.list
                updated=1
            fi
            if [ -f /etc/apt/sources.list.d/debian.sources ]; then
                prep_edit /etc/apt/sources.list.d/debian.sources
                sudo sed -i 's/^Components: \(.*\)$/Components: \1 contrib/' /etc/apt/sources.list.d/debian.sources
                updated=1
            fi
        fi
        if ! grep -qE "non-free" /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources 2>/dev/null; then
            if [ -f /etc/apt/sources.list ]; then
                prep_edit /etc/apt/sources.list
                sudo sed -i 's/main$/main non-free/' /etc/apt/sources.list
                updated=1
            fi
            if [ -f /etc/apt/sources.list.d/debian.sources ]; then
                prep_edit /etc/apt/sources.list.d/debian.sources
                sudo sed -i 's/^Components: \(.*\)$/Components: \1 non-free/' /etc/apt/sources.list.d/debian.sources
                updated=1
            fi
        fi
        if [ $updated -eq 1 ]; then
            sudo apt update
        fi
    fi
}

# enable backports repos on debian
enable_debian_backports() {
    is_debian || return 1

    local codename="${VERSION_CODENAME:-}"
    case "$codename" in
    trixie|forky|bookworm|bullseye)
        ;;
    sid|unstable|testing)
        echo "Debian Backports is not applicable to the '$codename' suite." >&2
        return 1
        ;;
    *)
        codename="trixie"
        ;;
    esac

    # Do nothing when the correct Backports repository is already configured.
    if grep -RqsE \
        "^(Suites:[[:space:]]*|deb[[:space:]]+.*[[:space:]])${codename}-backports([[:space:]]|$)" \
        /etc/apt/sources.list \
        /etc/apt/sources.list.d/*.list \
        /etc/apt/sources.list.d/*.sources 2>/dev/null
    then
        return 0
    fi

    local source_file="/etc/apt/sources.list.d/debian-backports.sources"
    if [[ -e "$source_file" ]]; then
        prep_edit "$source_file"
    else
        prep_create "$source_file"
    fi
    sudo tee "$source_file" >/dev/null <<EOF
Types: deb
URIs: https://deb.debian.org/debian
Suites: ${codename}-backports
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF

    sudo apt update
}

# legacy function call support - kept here so older code and local user scripts won't break

chaotic_aur_lib() {
    call_script chaotic
}

rpmfusion_chk() {
    call_script rpmfusion
}

pip_lib() {
    call_script pip
}

flatpak_in_lib() {
    call_script flathub
}