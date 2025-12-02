#!/bin/bash
# PKGBUILD/Arch build script for LinuxToys
# Usage: build.sh <version> <output_path>
# Example: build.sh 1.1 /tmp/builds

# Source utils.lib
SCRIPT_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
source "$SCRIPT_DIR/../../libs/utils.lib"

# Detect project root automatically
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

# Check CLI arguments
if [ $# -ne 2 ]; then
    _msg error "Usage: $0 <version> <output_path>"
    _msg info "Example: $0 1.1 /tmp/builds"
    exit 1
fi

LT_VERSION="$1"
OUTPUT_PATH="$2"

# Validate project structure
if [ ! -d "$PROJECT_ROOT/p3" ]; then
    _msg error "Invalid project structure: $PROJECT_ROOT/p3 not found"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_PATH"

_msg info "Building LinuxToys version $LT_VERSION for Arch Linux..."
_msg info "Output path: $OUTPUT_PATH"

# Change to output directory
cd "$OUTPUT_PATH"

# Clean up any existing build files except the final tarball
rm -rf linuxtoys_${lt_version}.orig linuxtoys-${lt_version} pkg src

# Create directory structure for the Python app
mkdir -p linuxtoys-${lt_version}/usr/bin
mkdir -p linuxtoys-${lt_version}/usr/share/linuxtoys
mkdir -p linuxtoys-${lt_version}/usr/share/applications
mkdir -p linuxtoys-${lt_version}/usr/share/icons/hicolor/scalable/apps

# Copy the Python app from p3 directory
cp -rf "$PROJECT_ROOT/p3"/* linuxtoys-${lt_version}/usr/share/linuxtoys/
# Copy desktop file and icon
cp "$PROJECT_ROOT/dev/LinuxToys.desktop" linuxtoys-${lt_version}/usr/share/applications/
cp "$PROJECT_ROOT/dev/linuxtoys.svg" linuxtoys-${lt_version}/usr/share/icons/hicolor/scalable/apps/

# Create the main executable script
cat > linuxtoys-${lt_version}/usr/bin/linuxtoys << 'EOF'
#!/bin/bash
# Set process name for better desktop integration
export LINUXTOYS_PROCESS_NAME="linuxtoys"
cd /usr/share/linuxtoys
exec /usr/bin/python3 run.py "$@"
EOF
chmod +x linuxtoys-${lt_version}/usr/bin/linuxtoys

# Create the CLI shortcut script
cat > linuxtoys-${lt_version}/usr/bin/linuxtoys-cli << 'EOF'
#!/bin/bash
# Set process name for better desktop integration
export LINUXTOYS_PROCESS_NAME="linuxtoys-cli"
# Enable CLI mode
export EASY_CLI=1
cd /usr/share/linuxtoys
exec /usr/bin/python3 run.py "$@"
EOF
chmod +x linuxtoys-${lt_version}/usr/bin/linuxtoys-cli

# Make sure all shell scripts are executable
find linuxtoys-${lt_version}/usr/share/linuxtoys/scripts/ -name "*.sh" -exec chmod +x {} \;
find linuxtoys-${lt_version}/usr/share/linuxtoys/helpers/ -name "*.sh" -exec chmod +x {} \;
chmod +x linuxtoys-${lt_version}/usr/share/linuxtoys/run.py

# Create tarball (this will be kept for Arch packaging)
tar -cJf linuxtoys-${lt_version}.tar.xz linuxtoys-${lt_version}/
# update version and hash on PKGBUILD file
hash=$(sha256sum linuxtoys-${lt_version}.tar.xz | cut -d' ' -f1)
sed -i "s/pkgver='[^']*'/pkgver='$LT_VERSION'/" PKGBUILD
sed -i "s/sha256sums=('[^']*')/sha256sums=('$hash')/" PKGBUILD

# build package
# makepkg -s

# Clean up build artifacts but keep the tarball for Arch packaging
rm -rf linuxtoys-${lt_version}/
echo "All done. Tarball linuxtoys-${lt_version}.tar.xz kept for Arch packaging." && sleep 3 && exit 0
