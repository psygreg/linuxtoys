#!/bin/bash
# PKGBUILD/Arch build script for LinuxToys
# Usage: build.sh <version> <output_path>
# Example: build.sh 1.1 /tmp/builds
# Note: This script expects Nuitka artifacts to be available in ./nuitka-artifacts/

# Source utils.lib
ROOT_DIR="$PWD"
while [[ "${ROOT_DIR##*/}" != "linuxtoys" && "$ROOT_DIR" != "/" ]]; do ROOT_DIR="${ROOT_DIR%/*}"; done
source "$ROOT_DIR/dev/libs/utils.lib"

# Check CLI arguments
if [ $# -ne 2 ]; then
    _msg error "Usage: $0 <version> <output_path>"
    _msg info "Example: $0 1.1 /tmp/builds"
    exit 1
fi

LT_VERSION="$1"
OUTPUT_PATH="$2"

_msg info "Building LinuxToys version $LT_VERSION for Arch Linux (Nuitka binary)..."
_msg info "Output path: $OUTPUT_PATH"

rm -rf "$OUTPUT_PATH"

# Create directory structure for Nuitka-based app
mkdir -p "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/bin"
mkdir -p "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/linuxtoys"
mkdir -p "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/applications"
mkdir -p "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/icons/hicolor/scalable/apps"

# Find and locate the Nuitka artifact
_msg info "Looking for Nuitka artifact..."
NUITKA_ARTIFACT=""

# Check multiple possible locations for the artifact
# 1. Current working directory nuitka-artifacts (from workflow dispatch)
if [ -d "./nuitka-artifacts" ]; then
    NUITKA_ARTIFACT=$(find "./nuitka-artifacts" -type f \( -name "*.zip" -o -name "linuxtoys.bin" \) | head -1)
    if [ -n "$NUITKA_ARTIFACT" ]; then
        _msg info "Found artifact in ./nuitka-artifacts"
    fi
fi

# 2. Repository root nuitka-artifacts
if [ -z "$NUITKA_ARTIFACT" ] && [ -d "$ROOT_DIR/nuitka-artifacts" ]; then
    NUITKA_ARTIFACT=$(find "$ROOT_DIR/nuitka-artifacts" -type f \( -name "*.zip" -o -name "linuxtoys.bin" \) | head -1)
    if [ -n "$NUITKA_ARTIFACT" ]; then
        _msg info "Found artifact in $ROOT_DIR/nuitka-artifacts"
    fi
fi

# 3. Common build location
if [ -z "$NUITKA_ARTIFACT" ] && [ -f "/tmp/nuitka-build/linuxtoys.bin" ]; then
    NUITKA_ARTIFACT="/tmp/nuitka-build/linuxtoys.bin"
    _msg info "Found artifact in /tmp/nuitka-build"
fi

# If still not found, show error and exit
if [ -z "$NUITKA_ARTIFACT" ] || [ ! -e "$NUITKA_ARTIFACT" ]; then
    _msg error "Nuitka artifact (linuxtoys.bin or .zip) not found!"
    _msg error "Expected locations checked:"
    _msg error "  1. ./nuitka-artifacts/"
    _msg error "  2. $ROOT_DIR/nuitka-artifacts/"
    _msg error "  3. /tmp/nuitka-build/linuxtoys.bin"
    _msg error ""
    _msg error "Available files:"
    [ -d "./nuitka-artifacts" ] && ls -la "./nuitka-artifacts/" || _msg error "  ./nuitka-artifacts/ does not exist"
    [ -d "$ROOT_DIR/nuitka-artifacts" ] && ls -la "$ROOT_DIR/nuitka-artifacts/" || _msg error "  $ROOT_DIR/nuitka-artifacts/ does not exist"
    [ -d "/tmp/nuitka-build" ] && ls -la "/tmp/nuitka-build/" || _msg error "  /tmp/nuitka-build/ does not exist"
    exit 1
fi

_msg info "Using Nuitka artifact: $NUITKA_ARTIFACT"

# Extract or copy the Nuitka artifact
if [ -f "$NUITKA_ARTIFACT" ]; then
    if [[ "$NUITKA_ARTIFACT" == *.zip ]]; then
        _msg info "Extracting linuxtoys.bin from zip artifact..."
        unzip -q "$NUITKA_ARTIFACT" -d "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/linuxtoys/"
    else
        _msg info "Copying Nuitka binary artifact..."
        cp "$NUITKA_ARTIFACT" "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/linuxtoys/linuxtoys.bin"
    fi
else
    _msg error "Nuitka artifact not found at: $NUITKA_ARTIFACT"
    exit 1
fi

# Verify linuxtoys.bin exists
if [ ! -f "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/linuxtoys/linuxtoys.bin" ]; then
    _msg error "linuxtoys.bin not found in extracted artifact!"
    _msg info "Contents of artifact extraction:"
    ls -la "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/linuxtoys/" || true
    exit 1
fi

# Make linuxtoys.bin executable
chmod +x "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/linuxtoys/linuxtoys.bin"

# Copy desktop file and icon
cp "$ROOT_DIR/src/LinuxToys.desktop" "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/applications/"
# Update WMClass in desktop file to use linuxtoys.bin instead of run.py
sed -i 's/StartupWMClass=run.py/StartupWMClass=linuxtoys.bin/' "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/applications/LinuxToys.desktop"

cp "$ROOT_DIR/src/linuxtoys.svg" "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/icons/hicolor/scalable/apps/"

# Create the main executable wrapper script
cat >"$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/bin/linuxtoys" <<'EOF'
#!/bin/bash
# LinuxToys wrapper script - executes the Nuitka binary
# Set process name for better desktop integration
export LINUXTOYS_PROCESS_NAME="linuxtoys"
# Enable CLI mode if arguments are provided
if [ $# -gt 0 ]; then
    export EASY_CLI=1
fi
exec /usr/share/linuxtoys/linuxtoys.bin "$@"
EOF
chmod +x "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/bin/linuxtoys"

# Create tarball (this will be kept for Arch packaging)
_msg info "Creating tarball for Arch packaging..."
tar -cJf "$OUTPUT_PATH/linuxtoys-${LT_VERSION}.tar.xz" -C "$OUTPUT_PATH" "linuxtoys-${LT_VERSION}/"

# Copy PKGBUILD to output directory
cp "$ROOT_DIR/dev/build/pkg/PKGBUILD" "$OUTPUT_PATH/PKGBUILD"

# Update version and hash on PKGBUILD file
_msg info "Updating PKGBUILD with version and hash..."
hash=$(sha256sum "$OUTPUT_PATH/linuxtoys-${LT_VERSION}.tar.xz" | cut -d' ' -f1)
sed -i "s/pkgver='[^']*'/pkgver='$LT_VERSION'/" "$OUTPUT_PATH/PKGBUILD"
sed -i "s/sha256sums=('[^']*')/sha256sums=('$hash')/" "$OUTPUT_PATH/PKGBUILD"

# Build the Arch package
_msg info "Building Arch Linux package..."
(
    cd "$OUTPUT_PATH" || exit 1
    makepkg
)

if [ $? -eq 0 ]; then
    _msg info "Arch package build completed successfully!"
else
    _msg error "Arch package build failed!"
    exit 1
fi

# Clean up build artifacts but keep the tarball for Arch packaging
_msg info "Cleaning up build artifacts..."
# Keep linuxtoys-${LT_VERSION}/ and linuxtoys-${LT_VERSION}.tar.xz for potential re-use
_msg info "All done! Tarball and package files are in $OUTPUT_PATH"
sleep 1
