#!/bin/bash

# ubuntu-debloater-install.sh — Installer for Ubuntu Debloater
# Author: Lucas

set -e

# === Configuration ===
REPO_URL="https://github.com/lucasgab2230/ubuntu-debloater.git"  # Replace with your actual repo
INSTALL_DIR="/opt/ubuntu-debloater"
BIN_LINK="/usr/local/bin/ubuntu-debloater"

# === Colors ===
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# === Functions ===
info() { echo -e "${YELLOW}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }

# === Check for root ===
if [[ "$EUID" -ne 0 ]]; then
    echo "[ERROR] This installer must be run as root. Use sudo."
    exit 1
fi

# === Clone or update repo ===
if [[ -d "$INSTALL_DIR" ]]; then
    info "Updating existing installation at $INSTALL_DIR..."
    git -C "$INSTALL_DIR" pull
else
    info "Cloning Ubuntu Debloater into $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# === Set permissions ===
info "Setting executable permissions..."
find "$INSTALL_DIR/scripts" -type f -name "*.sh" -exec chmod +x {} \;
find "$INSTALL_DIR/utils" -type f -name "*.sh" -exec chmod +x {} \;
chmod +x "$INSTALL_DIR/debloat.sh"

# === Create symlink ===
if [[ -L "$BIN_LINK" || -f "$BIN_LINK" ]]; then
    rm -f "$BIN_LINK"
fi
ln -s "$INSTALL_DIR/debloat.sh" "$BIN_LINK"
success "Created symlink: $BIN_LINK"

# === Done ===
success "Ubuntu Debloater installed successfully!"
echo -e "${YELLOW}You can now run it with: ${NC}ubuntu-debloater"
