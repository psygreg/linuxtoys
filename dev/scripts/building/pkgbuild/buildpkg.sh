#!/bin/bash

# Source utils library
source "$(dirname "$0")/../../libs/utils.lib"

LT_VERSION="$1"
OUTPUT_DIR="$2"

if [ -z "$LT_VERSION" ] || [ -z "$OUTPUT_DIR" ]; then
    _msg "error" "Usage: $0 <version> <output_dir>"
    exit 1
fi

# Clean up any existing build files except the final tarball
rm -rf linuxtoys_${LT_VERSION}.orig linuxtoys-${LT_VERSION} pkg src

# Create directory structure for the Python app
mkdir -p linuxtoys-${LT_VERSION}/usr/bin
mkdir -p linuxtoys-${LT_VERSION}/usr/share/linuxtoys
mkdir -p linuxtoys-${LT_VERSION}/usr/share/applications
mkdir -p linuxtoys-${LT_VERSION}/usr/share/icons/hicolor/scalable/apps

# Copy the Python app from p3 directory
cp -rf ../../../p3/* linuxtoys-${LT_VERSION}/usr/share/linuxtoys/
# Copy desktop file and icon
cp ../../LinuxToys.desktop linuxtoys-${LT_VERSION}/usr/share/applications/
cp ../../linuxtoys.svg linuxtoys-${LT_VERSION}/usr/share/icons/hicolor/scalable/apps/

# Create the main executable script
cat > linuxtoys-${LT_VERSION}/usr/bin/linuxtoys << 'EOF'
#!/bin/bash
# Set process name for better desktop integration
export LINUXTOYS_PROCESS_NAME="linuxtoys"
cd /usr/share/linuxtoys
exec /usr/bin/python3 run.py "$@"
EOF
chmod +x linuxtoys-${LT_VERSION}/usr/bin/linuxtoys

# Create the CLI shortcut script
cat > linuxtoys-${LT_VERSION}/usr/bin/linuxtoys-cli << 'EOF'
#!/bin/bash
# Set process name for better desktop integration
export LINUXTOYS_PROCESS_NAME="linuxtoys-cli"
# Enable CLI mode
export EASY_CLI=1
cd /usr/share/linuxtoys
exec /usr/bin/python3 run.py "$@"
EOF
chmod +x linuxtoys-${LT_VERSION}/usr/bin/linuxtoys-cli

# Make sure all shell scripts are executable
find linuxtoys-${LT_VERSION}/usr/share/linuxtoys/scripts/ -name "*.sh" -exec chmod +x {} \;
find linuxtoys-${LT_VERSION}/usr/share/linuxtoys/helpers/ -name "*.sh" -exec chmod +x {} \;
chmod +x linuxtoys-${LT_VERSION}/usr/share/linuxtoys/run.py

# Create tarball (this will be kept for Arch packaging)
tar -cJf linuxtoys-${LT_VERSION}.tar.xz linuxtoys-${LT_VERSION}/
# update version and hash on PKGBUILD file
hash=$(sha256sum linuxtoys-${LT_VERSION}.tar.xz | cut -d' ' -f1)
sed -i "s/pkgver='[^']*'/pkgver='$LT_VERSION'/" PKGBUILD
sed -i "s/sha256sums=('[^']*')/sha256sums=('$hash')/" PKGBUILD

# build package
# makepkg -s

# Move artifacts to output dir
mv linuxtoys-${LT_VERSION}.tar.xz "$OUTPUT_DIR/"
# If makepkg was run, move the package too
# mv *.pkg.tar.zst "$OUTPUT_DIR/"

# Clean up build artifacts but keep the tarball for Arch packaging
rm -rf linuxtoys-${LT_VERSION}/
_msg "info" "Arch build prep done. Tarball created."
