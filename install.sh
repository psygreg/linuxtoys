#!/bin/sh
# LinuxToys Quick-Installer v4 (POSIX /bin/sh with Bash for TUI)
# Features: Fully contained TUI with real progress bars, colorized fallback,
# robust distro detection, and safe package installation.

# --- Setup: TUI, Colors, and Helper Functions ---

# TUI detection
TUI_TOOL=""
if command -v dialog >/dev/null 2>&1; then
    TUI_TOOL="dialog"
elif command -v whiptail >/dev/null 2>&1; then
    TUI_TOOL="whiptail"
fi

# If TUI is available but we are in a basic shell (sh), re-execute with bash
# to get advanced features like pipefail, needed for the progress bar.
if [ -z "$BASH_VERSION" ] && [ -n "$TUI_TOOL" ]; then
    # shellcheck disable=SC2091
    if command -v bash >/dev/null 2>&1; then
        exec bash "$0" "$@"
    else
        # Cannot find bash, disable TUI
        TUI_TOOL=""
    fi
fi

# Check if stdout is a terminal to enable/disable colors
if [ -t 1 ]; then
    C_BOLD=$(tput bold 2>/dev/null || printf '\033[1m')
    C_GREEN=$(tput setaf 2 2>/dev/null || printf '\033[32m')
    C_RED=$(tput setaf 1 2>/dev/null || printf '\033[31m')
    C_YELLOW=$(tput setaf 3 2>/dev/null || printf '\033[33m')
    C_BLUE=$(tput setaf 4 2>/dev/null || printf '\033[34m')
    C_RESET=$(tput sgr0 2>/dev/null || printf '\033[0m')
else
    C_BOLD="" C_GREEN="" C_RED="" C_YELLOW="" C_BLUE="" C_RESET="" TUI_TOOL=""
fi

# Helper functions for consistent messaging
msg_info() { printf '%s\n' "${C_BLUE}==>${C_RESET} ${C_BOLD}$1${C_RESET}"; }
msg_ok() { printf '%s\n' "${C_GREEN}==>${C_RESET} ${C_BOLD}$1${C_RESET}"; }
msg_warn() { printf '%s\n' "${C_YELLOW}==> WARNING:${C_RESET} $1"; }
msg_err() { printf '%s\n' "${C_RED}==> ERROR:${C_RESET} $1" >&2; }
quit() {
    if [ -n "$TUI_TOOL" ]; then
        $TUI_TOOL --title "Error" --msgbox "$1" 8 78
    fi
    # Also print to stderr for logs
    msg_err "$1"
    exit "${2:-1}"
}

# --- TUI-Specific Functions (requires Bash) ---

tui_download_file() {
    local url="$1"
    local filename="$2"
    local title="Downloading"

    # Use awk to parse curl's progress and pipe it to the gauge.
    # 'pipefail' is a bash feature that makes the pipeline's exit status
    # be the status of the first command to fail, not the last one.
    set -o pipefail
    curl --fail -# -L "$url" -o "$filename" 2>&1 | \
    awk -W interactive '
        BEGIN { RS = "\r" }
        {
            if (match($0, /[0-9][0-9.]*%/)) {
                percent = substr($0, RSTART, RLENGTH-1)
                print percent
                fflush(stdout)
            }
        }
    ' | \
    $TUI_TOOL --title "$title" --gauge "Downloading $filename..." 10 70 0
    
    local download_status=$?
    set +o pipefail # Reset to default behavior
    
    return $download_status
}

tui_install_package() {
    local install_cmd="$1"
    local install_log
    install_log=$(mktemp)
    
    if [ "$TUI_TOOL" = "dialog" ]; then
        # dialog's --programbox is perfect for showing command output live.
        set -o pipefail
        eval "$install_cmd" 2>&1 | $TUI_TOOL --title "Installation" --programbox "Installing..." 20 78
        local install_status=${PIPESTATUS[0]}
        set +o pipefail
    else
        # whiptail lacks --programbox, so we show an infobox and log to a file.
        $TUI_TOOL --title "Installation" --infobox "Installing package, please wait..." 8 78
        eval "$install_cmd" >"$install_log" 2>&1
        local install_status=$?
    fi

    if [ "$install_status" -ne 0 ]; then
        # On failure, offer to show the log file.
        $TUI_TOOL --title "Installation Failed" --yesno "Installation failed. View log?" 8 78 && \
        $TUI_TOOL --title "Installation Log" --textbox "$install_log" 20 78
        quit "Package installation failed. Log is at $install_log" 10
    fi
    rm "$install_log"
}


# --- Main Logic ---

if [ -n "$TUI_TOOL" ]; then
    if ! $TUI_TOOL --title "LinuxToys Installer" --yesno "Do you wish to install or update LinuxToys?" 8 78; then
        clear; msg_warn "Installation cancelled."; exit 100
    fi
else
    printf '%s\n' "${C_GREEN}${C_BOLD}================== LINUXTOYS QUICK-INSTALLER ====================${C_RESET}"
    printf "Do you wish to install or update LinuxToys? (y/n) "
    read -r answer; answer=$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')
    if [ "$answer" != "y" ]; then
        msg_warn "Installation cancelled."; exit 100
    fi
fi

for cmd in curl grep sed; do
    command -v "$cmd" >/dev/null 2>&1 || quit "Required command not found: '$cmd'." 2
done

if [ -n "$TUI_TOOL" ]; then
    $TUI_TOOL --title "Fetching Info" --infobox "Getting latest release from GitHub..." 5 70
fi
tag=$(curl -fsSL "https://api.github.com/repos/psygreg/linuxtoys/releases/latest" | grep -o '"tag_name": *"[^"]*"' | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')
if [ -z "$tag" ]; then
    quit "Could not determine the latest release tag from GitHub." 4
fi

detect_distro() {
    [ -r /etc/os-release ] || quit "Cannot detect OS: /etc/os-release is not readable." 5
    # shellcheck disable=SC1091
    . /etc/os-release
    command -v rpm-ostree >/dev/null 2>&1 && { PKG_MANAGER="rpm-ostree"; PKG_TYPE="rpm"; return; }
    distro_id="${ID:-}${ID_LIKE:-}"
    case "$distro_id" in
        *debian*|*ubuntu*|*pop*|*mint*) PKG_MANAGER="apt"; PKG_TYPE="deb" ;;
        *fedora*|*rhel*|*centos*|*rocky*|*almalinux*)
            PKG_MANAGER="dnf"; command -v dnf >/dev/null 2>&1 || PKG_MANAGER="yum"; PKG_TYPE="rpm" ;;
        *suse*) PKG_MANAGER="zypper"; PKG_TYPE="rpm" ;;
        *arch*|*cachyos*|*manjaro*) PKG_MANAGER="pacman"; PKG_TYPE="pacman" ;;
        *) quit "Your OS ($PRETTY_NAME) is not supported by this script." 6 ;;
    esac
}

detect_distro

case "$PKG_TYPE" in
    "deb") pkg_file="linuxtoys_${tag}-1_amd64.deb" ;;
    "rpm") pkg_file="linuxtoys-${tag}-1.x86_64.rpm" ;;
    "pacman") pkg_file="linuxtoys-${tag}-1-x86_64.pacman" ;;
esac
pkg_url="https://github.com/psygreg/linuxtoys/releases/download/${tag}/${pkg_file}"

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT
cd "$tmp_dir" || quit "Failed to enter temporary directory." 7

if [ -n "$TUI_TOOL" ]; then
    $TUI_TOOL --title "Ready to Install" --infobox "Version: $tag\nDistro: ${PRETTY_NAME:-$ID}\nPackage: $pkg_file" 8 78
    sleep 2
    tui_download_file "$pkg_url" "$pkg_file" || quit "Failed to download package from: $pkg_url" 8
else
    msg_ok "Latest version found: $tag"
    msg_ok "Detected Distro Family: $PKG_TYPE, using: $PKG_MANAGER"
    msg_info "Downloading: $pkg_file"
    curl --fail -# -L "$pkg_url" -o "$pkg_file" || quit "Failed to download package from: $pkg_url" 8
fi

install_cmd=""
case "$PKG_MANAGER" in
    "apt") install_cmd="sudo dpkg -i ./$pkg_file && sudo apt-get install -f -y" ;;
    "dnf") install_cmd="sudo dnf install -y ./$pkg_file" ;;
    "yum") install_cmd="sudo yum install -y ./$pkg_file" ;;
    "zypper") install_cmd="sudo zypper --non-interactive install ./$pkg_file" ;;
    "pacman") install_cmd="sudo pacman -U --noconfirm ./$pkg_file" ;;
    "rpm-ostree")
        if rpm -q linuxtoys >/dev/null 2>&1; then
            install_cmd="sudo rpm-ostree uninstall linuxtoys && sudo rpm-ostree install ./$pkg_file"
        else
            install_cmd="sudo rpm-ostree install ./$pkg_file"
        fi ;;
esac

if [ -n "$TUI_TOOL" ]; then
    tui_install_package "$install_cmd"
else
    msg_info "Installing package... (sudo password may be required)"
    eval "$install_cmd" || quit "Package installation failed. Check output for errors." 10
fi

final_msg="LinuxToys has been successfully installed/updated!"
[ "$PKG_MANAGER" = "rpm-ostree" ] && final_msg="$final_msg\n\nA system reboot is required to apply the changes."

if [ -n "$TUI_TOOL" ]; then
    $TUI_TOOL --title "Success" --msgbox "$final_msg" 10 78; clear
else
    msg_ok "LinuxToys has been successfully installed/updated!"
    [ "$PKG_MANAGER" = "rpm-ostree" ] && msg_warn "A system reboot is required to apply the changes."
fi

exit 0
