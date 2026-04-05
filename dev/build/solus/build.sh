#!/bin/bash
# Solus/eopkg build script for LinuxToys
# Usage: build.sh <version> <sha256sum> <output_path>
# Example: build.sh 5.6.15 bb3147cb840a76c1abba11a5ecf9b77156c3f8f429f769b2da9113ed6f26ee89 /tmp/builds

ROOT_DIR="$PWD"
while [[ "${ROOT_DIR##*/}" != "linuxtoys" && "$ROOT_DIR" != "/" ]]; do ROOT_DIR="${ROOT_DIR%/*}"; done
source "$ROOT_DIR/dev/libs/utils.lib"

# Check CLI arguments
if [ $# -lt 2 ] || [ $# -gt 3 ]; then
    _msg error "Usage: $0 <version> <sha256sum> [output_path]"
    _msg info "Example: $0 5.6.15 bb3147cb840a76c1abba11a5ecf9b77156c3f8f429f769b2da9113ed6f26ee89 /tmp/builds"
    _msg info ""
    _msg info "If output_path is not provided, defaults to ./build_output/<version>"
    exit 1
fi

LT_VERSION="$1"
LT_SHA256="$2"
OUTPUT_PATH="${3:-.}/build_output/$LT_VERSION"

_msg info "Building LinuxToys version $LT_VERSION for Solus..."
_msg info "SHA256: $LT_SHA256"
_msg info "Output path: $OUTPUT_PATH"

# Validate sha256sum format (64 hex characters)
if ! [[ "$LT_SHA256" =~ ^[a-f0-9]{64}$ ]]; then
    _msg error "Invalid SHA256 hash format. Expected 64 hexadecimal characters."
    exit 1
fi

# Delete output directory if it exists
rm -rf "$OUTPUT_PATH"

# Create directory structure for the package
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION"

# Copy package.yml to the output directory and update version and sha256
cp "$ROOT_DIR/dev/build/solus/package.yml" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/package.yml"

# Update version in package.yml
sed -i "s/^version    : .*/version    : $LT_VERSION/" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/package.yml"

# Update SHA256 in package.yml (the source URL line with the hash at the end)
sed -i "s/: [a-f0-9]\{64\}$/: $LT_SHA256/" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/package.yml"

# Also update the version in the source URL
sed -i "s|/v[0-9.]\+\.tar\.gz|/v$LT_VERSION.tar.gz|g" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/package.yml"

_msg info "Updated package.yml with version $LT_VERSION and SHA256 hash"

# Create files directory (Solus packages store sources in a files/ directory)
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION/files"

# Copy the Python app from p3 directory
cp -rf "$ROOT_DIR/p3"/* "$OUTPUT_PATH/linuxtoys-$LT_VERSION/files/"

# Copy desktop file and icon
cp "$ROOT_DIR/src/LinuxToys.desktop" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/files/"
cp "$ROOT_DIR/src/linuxtoys.svg" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/files/"

# Create the main executable script
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/files/linuxtoys" <<'EOF'
#!/bin/bash
# Set process name for better desktop integration
export LINUXTOYS_PROCESS_NAME="linuxtoys"
# Enable CLI mode if arguments are provided
if [ $# -gt 0 ]; then
    export EASY_CLI=1
fi
cd /usr/share/linuxtoys
exec /usr/bin/python3 run.py "$@"
EOF
chmod +x "$OUTPUT_PATH/linuxtoys-$LT_VERSION/files/linuxtoys"

_msg info "Build structure created at: $OUTPUT_PATH/linuxtoys-$LT_VERSION"

# Build with solbuild
_msg info "Starting solbuild build process..."
cd "$OUTPUT_PATH/linuxtoys-$LT_VERSION"

# Initialize solbuild if needed (creates base images)
if ! solbuild list-profiles >/dev/null 2>&1; then
    _msg info "Initializing solbuild (first run, this may take a while)..."
    sudo solbuild init -u -p main-x86_64 || _msg warn "solbuild init may have issues, continuing..."
fi

# Run the actual build
if sudo solbuild build -p main-x86_64 2>&1 | tee "$OUTPUT_PATH/build.log"; then
    _msg success "solbuild completed successfully"
else
    _msg error "solbuild failed. Check $OUTPUT_PATH/build.log for details."
    exit 1
fi

# Collect built artifacts
_msg info "Collecting .eopkg artifacts..."
ARTIFACTS_DIR="$OUTPUT_PATH/artifacts"
mkdir -p "$ARTIFACTS_DIR"

# Search for .eopkg files in solbuild cache
if [ -d "/var/lib/solbuild" ]; then
    find /var/lib/solbuild -name "*.eopkg" -type f -exec cp {} "$ARTIFACTS_DIR/" \; 2>/dev/null && \
        _msg info "Found artifacts in /var/lib/solbuild"
fi

if [ -d "$HOME/.cache/solbuild" ]; then
    find "$HOME/.cache/solbuild" -name "*.eopkg" -type f -exec cp {} "$ARTIFACTS_DIR/" \; 2>/dev/null && \
        _msg info "Found artifacts in $HOME/.cache/solbuild"
fi

# Verify artifacts were created
if [ "$(ls -A "$ARTIFACTS_DIR")" ]; then
    _msg success "Build complete! Artifacts located at: $ARTIFACTS_DIR"
    ls -lh "$ARTIFACTS_DIR"
else
    _msg warn "No .eopkg artifacts found. Check $OUTPUT_PATH/build.log for build errors."
    exit 1
fi
