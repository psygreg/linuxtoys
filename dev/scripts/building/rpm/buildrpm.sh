#!/bin/bash

# Source utils library
source "$(dirname "$0")/../../libs/utils.lib"

LT_VERSION="$1"
OUTPUT_DIR="$2"

if [ -z "$LT_VERSION" ] || [ -z "$OUTPUT_DIR" ]; then
    _msg "error" "Usage: $0 <version> <output_dir>"
    exit 1
fi

# Check if rpmbuild is available
if ! command -v rpmbuild &> /dev/null; then
    _msg "error" "rpmbuild is not installed."
    _msg "error" "Please install it with: sudo dnf install rpm-build rpmdevtools"
    _msg "error" "Or on other distributions: sudo apt install rpm-build (Ubuntu/Debian)"
    exit 1
fi

# set up directory and copy files from p3
mkdir -p linuxtoys-${LT_VERSION}/usr/bin
mkdir -p linuxtoys-${LT_VERSION}/usr/share/linuxtoys
mkdir -p linuxtoys-${LT_VERSION}/usr/share/applications
mkdir -p linuxtoys-${LT_VERSION}/usr/share/icons/hicolor/scalable/apps
mkdir -p rpmbuild/SOURCES

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

# Make sure all shell scripts are executable
find linuxtoys-${LT_VERSION}/usr/share/linuxtoys/scripts/ -name "*.sh" -exec chmod +x {} \;
find linuxtoys-${LT_VERSION}/usr/share/linuxtoys/helpers/ -name "*.sh" -exec chmod +x {} \;
chmod +x linuxtoys-${LT_VERSION}/usr/share/linuxtoys/run.py

# set up rpmbuild
cp -r linuxtoys-${LT_VERSION} rpmbuild/SOURCES/
day=$(date +%d)
day_abbr=$(LC_TIME=C date +%a)  # This will always be in English
month=$(LC_TIME=C date +%b)
year=$(date +%Y)
specfile_line="Version:        ${LT_VERSION}"
specfile_line2="* ${day_abbr} ${month} ${day} ${year} Victor Gregory <psygreg@pm.me> - ${LT_VERSION}"
sed -i "2c\\$specfile_line" rpmbuild/SPECS/linuxtoys.spec
sed -i "53c\\$specfile_line2" rpmbuild/SPECS/linuxtoys.spec

# build
rm -r $HOME/rpmbuild 2>/dev/null || true # ensure there's no leftover build artifacts previous to building
cp -r rpmbuild $HOME # only works with this setup on Silverblue, which is what I use
cd $HOME/rpmbuild || exit 1
rpmbuild -ba SPECS/linuxtoys.spec

# Move artifacts to output dir
cd - || exit 1
mv $HOME/rpmbuild/RPMS/x86_64/*.rpm "$OUTPUT_DIR/"
mv $HOME/rpmbuild/SRPMS/*.rpm "$OUTPUT_DIR/"

# Clean up build artifacts
rm -rf linuxtoys-${LT_VERSION}/ linuxtoys-${LT_VERSION}.tar.xz
_msg "info" "RPM build done."