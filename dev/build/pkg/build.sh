#!/bin/bash
# PKGBUILD/Arch build script for LinuxToys
# Usage: build.sh <version> <output_path>
# Example: build.sh 1.1 /tmp/builds

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

_msg info "Building LinuxToys version $LT_VERSION for Arch Linux..."
_msg info "Output path: $OUTPUT_PATH"

rm -rf "$OUTPUT_PATH"

# Create directory structure for the Python app
mkdir -p "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/bin"
mkdir -p "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/linuxtoys"
mkdir -p "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/applications"
mkdir -p "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/icons/hicolor/scalable/apps"

# Copy the Python app from p3 directory
cp -rf "$ROOT_DIR/p3"/* "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/linuxtoys/"
# Copy desktop file and icon
cp "$ROOT_DIR/src/LinuxToys.desktop" "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/applications/"
cp "$ROOT_DIR/src/linuxtoys.svg" "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/icons/hicolor/scalable/apps/"

# Create the main executable script
cat >"$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/bin/linuxtoys" <<'EOF'
#!/bin/bash
# Set process name for better desktop integration
export LINUXTOYS_PROCESS_NAME="linuxtoys"
cd /usr/share/linuxtoys
exec /usr/bin/python3 run.py "$@"
EOF
chmod +x "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/bin/linuxtoys"

# Create the CLI shortcut script
cat >"$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/bin/linuxtoys-cli" <<'EOF'
#!/bin/bash
# Set process name for better desktop integration
export LINUXTOYS_PROCESS_NAME="linuxtoys-cli"
# Enable CLI mode
export EASY_CLI=1
cd /usr/share/linuxtoys
exec /usr/bin/python3 run.py "$@"
EOF
chmod +x "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/bin/linuxtoys-cli"

# Make sure all shell scripts are executable
find "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/linuxtoys/scripts/" -name "*.sh" -exec chmod +x {} \;
find "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/linuxtoys/helpers/" -name "*.sh" -exec chmod +x {} \;
chmod +x "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/usr/share/linuxtoys/run.py"

# Create tarball (this will be kept for Arch packaging)
tar -cJf "$OUTPUT_PATH/linuxtoys-${LT_VERSION}.tar.xz" -C "$OUTPUT_PATH" "linuxtoys-${LT_VERSION}/"

# Copy PKGBUILD to output directory
cp "$ROOT_DIR/dev/build/pkg/PKGBUILD" "$OUTPUT_PATH/PKGBUILD"

# update version and hash on PKGBUILD file
hash=$(sha256sum "$OUTPUT_PATH/linuxtoys-${LT_VERSION}.tar.xz" | cut -d' ' -f1)
sed -i "s/pkgver='[^']*'/pkgver='$LT_VERSION'/" "$OUTPUT_PATH/PKGBUILD"
sed -i "s/sha256sums=('[^']*')/sha256sums=('$hash')/" "$OUTPUT_PATH/PKGBUILD"
# Update source to use local tarball
sed -i "s|source=.*|source=(\"linuxtoys-${LT_VERSION}.tar.xz\")|" "$OUTPUT_PATH/PKGBUILD"

(
    cd "$OUTPUT_PATH"
    makepkg
)

# Clean up build artifacts but keep the tarball for Arch packaging
# rm -rf "$OUTPUT_PATH/linuxtoys-${LT_VERSION}/"
echo "All done. Tarball linuxtoys-${LT_VERSION}.tar.xz kept for Arch packaging." && sleep 3 && exit 0
