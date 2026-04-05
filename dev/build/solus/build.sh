#!/bin/bash
# Solus/eopkg build script for LinuxToys
# Automatically fetches version and sha256 from latest GitHub release
# Usage: build.sh [output_path]
# Example: build.sh /tmp/builds

ROOT_DIR="$PWD"
while [[ "${ROOT_DIR##*/}" != "linuxtoys" && "$ROOT_DIR" != "/" ]]; do ROOT_DIR="${ROOT_DIR%/*}"; done
source "$ROOT_DIR/dev/libs/utils.lib"

# Check CLI arguments
if [ $# -gt 1 ]; then
    _msg error "Usage: $0 [output_path]"
    _msg info "Example: $0 /tmp/builds"
    _msg info ""
    _msg info "If output_path is not provided, defaults to ./build_output"
    exit 1
fi

OUTPUT_PATH_BASE="${1:-.}/build_output"

_msg info "Fetching latest release information from GitHub..."

# Fetch the latest release from GitHub API
GITHUB_API="https://api.github.com/repos/linuxtoys/linuxtoys/releases/latest"
RELEASE_INFO=$(curl -s "$GITHUB_API")

# Check if the API call was successful
if ! echo "$RELEASE_INFO" | grep -q '"tag_name"'; then
    _msg error "Failed to fetch latest release from GitHub. Check your internet connection and GitHub access."
    exit 1
fi

# Extract version from tag (remove 'v' prefix if present)
LT_VERSION=$(echo "$RELEASE_INFO" | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": "\(.*\)".*/\1/' | sed 's/^v//')

if [ -z "$LT_VERSION" ]; then
    _msg error "Could not extract version from GitHub release"
    exit 1
fi

OUTPUT_PATH="$OUTPUT_PATH_BASE/$LT_VERSION"

_msg info "Latest version: $LT_VERSION"
_msg info "Downloading tarball and calculating SHA256..."

# Get the tarball URL and download it
TARBALL_URL="https://github.com/linuxtoys/linuxtoys/archive/refs/tags/v$LT_VERSION.tar.gz"
TEMP_TARBALL="/tmp/linuxtoys-$LT_VERSION.tar.gz"

# Download the tarball
if ! curl -L -o "$TEMP_TARBALL" "$TARBALL_URL" 2>/dev/null; then
    _msg error "Failed to download tarball from: $TARBALL_URL"
    rm -f "$TEMP_TARBALL"
    exit 1
fi

# Calculate SHA256
LT_SHA256=$(sha256sum "$TEMP_TARBALL" | awk '{print $1}')

# Clean up temporary tarball
rm -f "$TEMP_TARBALL"

if [ -z "$LT_SHA256" ]; then
    _msg error "Failed to calculate SHA256"
    exit 1
fi

_msg info "Building LinuxToys version $LT_VERSION for Solus..."
_msg info "SHA256: $LT_SHA256"
_msg info "Output path: $OUTPUT_PATH"

# check for solbuild
. /etc/os-release
if ! which solbuild >/dev/null 2>&1; then
    _msg info "solbuild not found, installing..."
    if [[ "$ID" != "solus" ]]; then
        git clone https://github.com/getsolus/solbuild.git
        cd solbuild
        make
        sudo make install
        cd ..
    else
        sudo eopkg it -y solbuild
    fi
fi

# Delete output directory if it exists
rm -rf "$OUTPUT_PATH"
# Create directory structure for the package
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION"
# Copy package.yml to the output directory and update version and sha256
cp "$ROOT_DIR/dev/build/solus/package.yml" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/package.yml"
sed -i "s/^version    : .*/version    : $LT_VERSION/" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/package.yml"
sed -i "s/: [a-f0-9]\{64\}$/: $LT_SHA256/" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/package.yml"
# Also update the version in the source URL
sed -i "s|/v[0-9.]\+\.tar\.gz|/v$LT_VERSION.tar.gz|g" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/package.yml"
_msg info "Updated package.yml with version $LT_VERSION and SHA256 hash"
_msg info "Build structure created at: $OUTPUT_PATH/linuxtoys-$LT_VERSION"

# Build with solbuild
_msg info "Starting solbuild build process..."
cd "$OUTPUT_PATH/linuxtoys-$LT_VERSION"
if ! solbuild list-profiles >/dev/null 2>&1; then
    _msg info "Initializing solbuild (first run, this may take a while)..."
    sudo solbuild init -u -p main-x86_64 || _msg warn "solbuild init may have issues, continuing..."
fi
fakeroot solbuild build -p main-x86_64 2>&1 | tee "$OUTPUT_PATH/build.log"