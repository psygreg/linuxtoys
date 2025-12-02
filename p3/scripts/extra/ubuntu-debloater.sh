#!/bin/bash
# install.sh
# Installation script for Ubuntu Debloater
# This script installs the debloater to your system for easy access.

# Exit immediately if a command exits with a non-zero status.
# Treat unset variables as an error when substituting.
# Exit if any command in a pipeline fails.
set -euo pipefail

# --- Configuration ---
INSTALL_DIR="/opt/ubuntu-debloater"
BIN_LINK="/usr/local/bin/ubuntu-debloater"
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
REPO_URL="https://raw.githubusercontent.com/lucasgab2230/ubuntu-debloater/main"

# List of files and directories to download
FILES_TO_DOWNLOAD=(
    "debloat.sh"
    "uninstall.sh"
)

CONFIG_FILES=(
    "config/common_bloat.list"
    "config/kubuntu_bloat.list"
    "config/lubuntu_bloat.list"
    "config/mint_bloat.list"
    "config/ubuntu_bloat.list"
    "config/xubuntu_bloat.list"
)

SCRIPT_FILES=(
    "scripts/cleanup_after_removal.sh"
    "scripts/functions.sh"
    "scripts/revert_debloat.sh"
)

DOC_FILES=(
    "docs/package_lists_guide.md"
    "docs/troubleshooting.md"
    "docs/usage.md"
)

# --- Logging Functions ---
log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
    exit 1
}

log_success() {
    echo "[SUCCESS] $1"
}

# --- Download Functions ---
# Check if curl or wget is available
check_download_tool() {
    if command -v curl &> /dev/null; then
        echo "curl"
    elif command -v wget &> /dev/null; then
        echo "wget"
    else
        log_error "Neither curl nor wget is installed. Please install one of them to download files."
    fi
}

# Download a single file from the repository
download_file() {
    local file_path="$1"
    local dest_dir="$2"
    local download_tool="$3"
    local url="${REPO_URL}/${file_path}"
    local dest_file="${dest_dir}/${file_path}"
    local dest_parent
    dest_parent="$(dirname "$dest_file")"

    # Create parent directory if it doesn't exist
    mkdir -p "$dest_parent"

    log_info "Downloading ${file_path}..."
    if [[ "$download_tool" == "curl" ]]; then
        if ! curl -fsSL "$url" -o "$dest_file"; then
            log_error "Failed to download ${file_path} from ${url}"
        fi
    else
        if ! wget -q "$url" -O "$dest_file"; then
            log_error "Failed to download ${file_path} from ${url}"
        fi
    fi
}

# Download all required files if they don't exist
download_all_files() {
    local dest_dir="$1"
    local download_tool
    download_tool=$(check_download_tool)

    log_info "Downloading all required files from GitHub..."

    # Download main files
    for file in "${FILES_TO_DOWNLOAD[@]}"; do
        download_file "$file" "$dest_dir" "$download_tool"
    done

    # Download config files
    for file in "${CONFIG_FILES[@]}"; do
        download_file "$file" "$dest_dir" "$download_tool"
    done

    # Download script files
    for file in "${SCRIPT_FILES[@]}"; do
        download_file "$file" "$dest_dir" "$download_tool"
    done

    # Download documentation files
    for file in "${DOC_FILES[@]}"; do
        download_file "$file" "$dest_dir" "$download_tool"
    done

    log_success "All files downloaded successfully!"
}

# Check if all required files exist locally
check_local_files() {
    [[ -f "${SCRIPT_DIR}/debloat.sh" ]] && \
    [[ -f "${SCRIPT_DIR}/uninstall.sh" ]] && \
    [[ -d "${SCRIPT_DIR}/config" ]] && \
    [[ -f "${SCRIPT_DIR}/config/ubuntu_bloat.list" ]] && \
    [[ -d "${SCRIPT_DIR}/scripts" ]] && \
    [[ -f "${SCRIPT_DIR}/scripts/functions.sh" ]]
}

# --- Check for root privileges ---
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)."
    fi
}

# --- Installation ---
install_debloater() {
    log_info "Installing Ubuntu Debloater..."

    # Check if required files exist locally, otherwise download them
    if ! check_local_files; then
        log_info "Required files not found locally. Downloading from GitHub..."
        download_all_files "${SCRIPT_DIR}"
    fi

    # Create installation directory
    log_info "Creating installation directory: ${INSTALL_DIR}"
    mkdir -p "${INSTALL_DIR}"

    # Copy files
    log_info "Copying files to ${INSTALL_DIR}..."
    cp "${SCRIPT_DIR}/debloat.sh" "${INSTALL_DIR}/"
    cp "${SCRIPT_DIR}/uninstall.sh" "${INSTALL_DIR}/"
    cp -r "${SCRIPT_DIR}/config" "${INSTALL_DIR}/"
    cp -r "${SCRIPT_DIR}/scripts" "${INSTALL_DIR}/"

    # Copy documentation if available
    if [[ -d "${SCRIPT_DIR}/docs" ]]; then
        cp -r "${SCRIPT_DIR}/docs" "${INSTALL_DIR}/"
    fi

    # Set permissions
    log_info "Setting permissions..."
    chmod 755 "${INSTALL_DIR}/debloat.sh"
    chmod 755 "${INSTALL_DIR}/uninstall.sh"
    # Set executable permissions for shell scripts in scripts directory
    find "${INSTALL_DIR}/scripts" -type f -name "*.sh" -exec chmod 755 {} +
    # Set read permissions for config files
    find "${INSTALL_DIR}/config" -type f -exec chmod 644 {} +
    # Set directory permissions
    find "${INSTALL_DIR}" -type d -exec chmod 755 {} +

    # Create symbolic link
    log_info "Creating symbolic link: ${BIN_LINK}"
    ln -sf "${INSTALL_DIR}/debloat.sh" "${BIN_LINK}"

    log_success "Ubuntu Debloater installed successfully!"
    echo ""
    echo "You can now run the debloater using:"
    echo "  sudo ubuntu-debloater"
    echo ""
    echo "Installation directory: ${INSTALL_DIR}"
    echo "To uninstall, run: sudo ${INSTALL_DIR}/uninstall.sh"
}

# --- Main ---
check_root
install_debloater
