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
GITHUB_API="https://api.github.com/repos/psygreg/linuxtoys/releases/latest"
RELEASE_INFO=$(curl -s "$GITHUB_API")

# Check if the API call was successful
if ! echo "$RELEASE_INFO" | grep -q '"tag_name"'; then
    _msg error "Failed to fetch latest release from GitHub. Check your internet connection and GitHub access."
    exit 1
fi

# Extract version from tag (keep original, also extract clean version)
LT_TAG=$(echo "$RELEASE_INFO" | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": "\(.*\)".*/\1/')
LT_VERSION=$(echo "$LT_TAG" | sed 's/^v//')

if [ -z "$LT_VERSION" ]; then
    _msg error "Could not extract version from GitHub release"
    exit 1
fi

OUTPUT_PATH="$OUTPUT_PATH_BASE/$LT_VERSION"

_msg info "Latest version: $LT_VERSION"
_msg info "Downloading tarball and calculating SHA256..."

# The release tarball includes src/, including the desktop file, MIME XML, and AppStream metainfo.
# Get the tarball URL and download it
TARBALL_URL="https://github.com/psygreg/linuxtoys/archive/refs/tags/$LT_TAG.tar.gz"
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

# solbuild runs inside a rootful distrobox container (default: alma).
# Rootful mode is required: solbuild mounts its rootfs image via a loop device
# and chroots into it, which needs CAP_SYS_ADMIN + /dev/loop* (not available in
# a rootless container -> "failed to setup loop device").
SOLUS_CONTAINER="${SOLUS_CONTAINER:-alma}"
DBOX_RUN=(distrobox enter --root -n "$SOLUS_CONTAINER" --)

if ! distrobox list --root 2>/dev/null | grep -qw "$SOLUS_CONTAINER"; then
    _msg error "Rootful distrobox container '$SOLUS_CONTAINER' not found."
    _msg info "Create one with: distrobox create --root --name $SOLUS_CONTAINER --image <image>"
    _msg info "or pick another name with: SOLUS_CONTAINER=<name> $0"
    exit 1
fi

_msg info "Using rootful distrobox container: $SOLUS_CONTAINER"

# check for solbuild inside the container
if ! "${DBOX_RUN[@]}" which solbuild >/dev/null 2>&1; then
    _msg error "solbuild not found inside container '$SOLUS_CONTAINER'."
    _msg info "Install it in the container first (see dev/build/solus/README.md)."
    exit 1
fi

# sanity check: confirm the container really can set up loop devices
_msg info "Checking loop device support inside container '$SOLUS_CONTAINER'..."
if ! "${DBOX_RUN[@]}" sh -c '
    set -e
    tmp=$(mktemp /tmp/solbuild-loopcheck.XXXXXX.img)
    mnt=$(mktemp -d /tmp/solbuild-loopcheck.XXXXXX.mnt)
    trap "rm -f \"$tmp\"; rmdir \"$mnt\" 2>/dev/null || true" EXIT
    dd if=/dev/zero of="$tmp" bs=1k count=64 2>/dev/null
    mount -o loop,ro "$tmp" "$mnt"
    umount "$mnt"
'; then
    _msg error "Container '$SOLUS_CONTAINER' cannot set up loop devices."
    _msg info "solbuild needs to mount its rootfs image through a loop device,"
    _msg info "which requires a privileged (rootful) container."
    _msg info "Recreate the container with rootful mode, for example:"
    _msg info "  distrobox create --root --name $SOLUS_CONTAINER --image <image>"
    exit 1
fi

# Delete output directory if it exists
rm -rf "$OUTPUT_PATH"
# Create directory structure for the package
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION"
# Copy package.yml to the output directory and update version and sha256
cp "$ROOT_DIR/dev/build/solus/package.yml" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/package.yml"

PACKAGE_YML="$OUTPUT_PATH/linuxtoys-$LT_VERSION/package.yml"

# Update version - using more flexible regex to handle varying whitespace
sed -i "s/^version[[:space:]]*:[[:space:]].*/version    : $LT_VERSION/" "$PACKAGE_YML"

# Update the entire source block with new version and sha256
sed -i "s|https://github.com/psygreg/linuxtoys/archive/refs/tags/[^:]*\.tar\.gz[[:space:]]*:[[:space:]]*[a-f0-9]\{64\}|https://github.com/psygreg/linuxtoys/archive/refs/tags/$LT_TAG.tar.gz : $LT_SHA256|g" "$PACKAGE_YML"

# Verify the updates were applied
if ! grep -q "version    : $LT_VERSION" "$PACKAGE_YML"; then
    _msg error "Failed to update version in package.yml"
    exit 1
fi

if ! grep -q "$LT_SHA256" "$PACKAGE_YML"; then
    _msg error "Failed to update SHA256 in package.yml"
    exit 1
fi

_msg info "Updated package.yml with version $LT_VERSION and SHA256 hash"
_msg info "Build structure created at: $OUTPUT_PATH/linuxtoys-$LT_VERSION"
_msg info "Package.yml preview:"
head -5 "$PACKAGE_YML"

# Build with solbuild inside the container
_msg info "Starting solbuild build process in container '$SOLUS_CONTAINER'..."
cd "$OUTPUT_PATH/linuxtoys-$LT_VERSION"
if ! "${DBOX_RUN[@]}" test -d /var/lib/solbuild/images; then
    _msg info "Initializing solbuild (first run, this may take a while)..."
    "${DBOX_RUN[@]}" solbuild init -u -p main-x86_64 \
        || _msg warning "solbuild init may have issues, continuing..."
fi
"${DBOX_RUN[@]}" solbuild build -p main-x86_64 2>&1 | tee "$OUTPUT_PATH/build.log"