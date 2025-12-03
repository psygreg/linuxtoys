#!/bin/bash
# COPR/RPM build script for LinuxToys
# Usage: build.sh <version> <output_path>
# Example: build.sh 1.1 /tmp/builds

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

_msg info "Building LinuxToys version $LT_VERSION for COPR/RPM..."
_msg info "Output path: $OUTPUT_PATH"

# Delete output directory if it exists
rm -rf "$OUTPUT_PATH"

# set up directory and copy files from p3
mkdir -p "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/bin"
mkdir -p "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/linuxtoys"
mkdir -p "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/applications"
mkdir -p "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$OUTPUT_PATH/SOURCES"

# Copy the Python app from p3 directory
cp -rf "$ROOT_DIR/p3"/* "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/linuxtoys/"
# Copy desktop file and icon
cp "$ROOT_DIR/src/LinuxToys.desktop" "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/applications/"
cp "$ROOT_DIR/src/linuxtoys.svg" "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/icons/hicolor/scalable/apps/"

# Create the main executable script
cat >"$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/bin/linuxtoys" <<'EOF'
#!/bin/bash
# Set process name for better desktop integration
export LINUXTOYS_PROCESS_NAME="linuxtoys"
cd /usr/share/linuxtoys
exec /usr/bin/python3 run.py "$@"
EOF
chmod +x "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/bin/linuxtoys"

# Make sure all shell scripts are executable
find "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/linuxtoys/scripts/" -name "*.sh" -exec chmod +x {} \;
find "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/linuxtoys/helpers/" -name "*.sh" -exec chmod +x {} \;
chmod +x "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/usr/share/linuxtoys/run.py"

# set up rpmbuild
# cp -r "$OUTPUT_PATH/linuxtoys-$LT_VERSION" "$HOME/rpmbuild/SOURCES/"
day=$(date +%d)
day_abbr=$(LC_TIME=C date +%a) # This will always be in English
month=$(LC_TIME=C date +%b)
year=$(date +%Y)
specfile_line="Version:        ${LT_VERSION}"
specfile_line2="* ${day_abbr} ${month} ${day} ${year} Victor Gregory <psygreg@pm.me> - ${LT_VERSION}"
sed -i "2c\\$specfile_line" ${ROOT_DIR}/dev/build/rpm/linuxtoys.spec
sed -i "53c\\$specfile_line2" ${ROOT_DIR}/dev/build/rpm/linuxtoys.spec
# build
# rm -r $HOME/rpmbuild # ensure there's no leftover build artifacts previous to building
# cp -r rpmbuild $HOME # only works with this setup on Silverblue, which is what I use
# cd $HOME/rpmbuild || exit 1
rpmbuild --define "_topdir $OUTPUT_PATH" -ba ${ROOT_DIR}/dev/build/rpm/linuxtoys.spec

# Clean up build artifacts
# cd - || exit 1
# rm -rf linuxtoys-${LT_VERSION}/ linuxtoys-${LT_VERSION}.tar.xz
echo "All done" && sleep 3 && exit 0
