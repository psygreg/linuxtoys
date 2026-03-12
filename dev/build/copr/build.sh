#!/bin/bash
# COPR/RPM build script for LinuxToys
# Usage: build.sh <version> <output_path>
# Example: build.sh 1.1 /tmp/builds
# NOTE: This script expects the Nuitka artifact (linuxtoys.bin) to be available

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

_msg info "Building LinuxToys version $LT_VERSION for COPR/RPM (Nuitka binary)..."
_msg info "Output path: $OUTPUT_PATH"

# Delete output directory if it exists
rm -rf "$OUTPUT_PATH"

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

# Set up directory structure for RPM build
mkdir -p "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/bin"
mkdir -p "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/linuxtoys"
mkdir -p "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/applications"
mkdir -p "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$OUTPUT_PATH/SOURCES"

# Extract or copy the Nuitka artifact
if [ -f "$NUITKA_ARTIFACT" ]; then
    if [[ "$NUITKA_ARTIFACT" == *.zip ]]; then
        _msg info "Extracting linuxtoys.bin from zip artifact..."
        unzip -q "$NUITKA_ARTIFACT" -d "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/linuxtoys/"
    else
        _msg info "Copying Nuitka binary artifact..."
        cp "$NUITKA_ARTIFACT" "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/linuxtoys/linuxtoys.bin"
    fi
else
    _msg error "Nuitka artifact not found at: $NUITKA_ARTIFACT"
    exit 1
fi

# Verify linuxtoys.bin exists
if [ ! -f "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/linuxtoys/linuxtoys.bin" ]; then
    _msg error "linuxtoys.bin not found in extracted artifact!"
    _msg info "Contents of artifact extraction:"
    ls -la "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/linuxtoys/" || true
    exit 1
fi

# Make linuxtoys.bin executable
chmod +x "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/linuxtoys/linuxtoys.bin"

# Copy desktop file and icon
cp "$ROOT_DIR/src/LinuxToys.desktop" "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/applications/"
cp "$ROOT_DIR/src/linuxtoys.svg" "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/icons/hicolor/scalable/apps/"

# Create the main executable wrapper script
cat >"$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/bin/linuxtoys" <<'EOF'
#!/bin/bash
# LinuxToys wrapper script - executes the Nuitka binary
export LINUXTOYS_PROCESS_NAME="linuxtoys"
# Enable CLI mode if arguments are provided
if [ $# -gt 0 ]; then
    export EASY_CLI=1
fi
exec /usr/share/linuxtoys/linuxtoys.bin "$@"
EOF
chmod +x "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/bin/linuxtoys"

# Create tarball source for COPR
tar -cJf "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION.tar.xz" -C "$OUTPUT_PATH/SOURCES" "linuxtoys-$LT_VERSION"
rm -r "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION"

# Update spec file with current version and date
day=$(date +%d)
day_abbr=$(LC_TIME=C date +%a) # This will always be in English
month=$(LC_TIME=C date +%b)
year=$(date +%Y)
specfile_line="Version:        ${LT_VERSION}"
specfile_line2="* ${day_abbr} ${month} ${day} ${year} Victor Gregory <psygreg@pm.me> - ${LT_VERSION}"
sed -i "2c\\$specfile_line" "${ROOT_DIR}/dev/build/copr/linuxtoys.spec"
sed -i "48c\\$specfile_line2" "${ROOT_DIR}/dev/build/copr/linuxtoys.spec"

# Build RPM package
_msg info "Building RPM package..."
rpmbuild --define "_topdir $OUTPUT_PATH" -ba "${ROOT_DIR}/dev/build/copr/linuxtoys.spec"

if [ $? -eq 0 ]; then
    _msg info "RPM build completed successfully!"
else
    _msg error "RPM build failed!"
    exit 1
fi

_msg info "All done!"
sleep 1
