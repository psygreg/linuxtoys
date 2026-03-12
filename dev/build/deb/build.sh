#!/bin/bash
# Debian/DEB build script for LinuxToys
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

_msg info "Building LinuxToys version $LT_VERSION for Debian/Ubuntu (Nuitka binary)..."
_msg info "Output path: $OUTPUT_PATH"

# Delete output directory if it exists
rm -rf "$OUTPUT_PATH"
mkdir -p "$OUTPUT_PATH"

# Set up dir structure for the new Nuitka-based app
mkdir -p "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/bin"
mkdir -p "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys"
mkdir -p "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/applications"
mkdir -p "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/icons/hicolor/scalable/apps"

# Find and extract the Nuitka artifact
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

# Extract or copy the artifact
if [ -f "$NUITKA_ARTIFACT" ]; then
    if [[ "$NUITKA_ARTIFACT" == *.zip ]]; then
        _msg info "Extracting linuxtoys.bin from zip artifact..."
        unzip -q "$NUITKA_ARTIFACT" -d "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys/"
    else
        _msg info "Copying Nuitka binary artifact..."
        cp "$NUITKA_ARTIFACT" "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys/linuxtoys.bin"
    fi
else
    _msg error "Nuitka artifact not found at: $NUITKA_ARTIFACT"
    exit 1
fi

# Verify linuxtoys.bin exists
if [ ! -f "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys/linuxtoys.bin" ]; then
    _msg error "linuxtoys.bin not found in extracted artifact!"
    _msg info "Contents of artifact extraction:"
    ls -la "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys/" || true
    exit 1
fi

# Make linuxtoys.bin executable
chmod +x "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys/linuxtoys.bin"

# Copy desktop file
cp "$ROOT_DIR/src/LinuxToys.desktop" "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/applications/"

# Copy icon
cp "$ROOT_DIR/src/linuxtoys.svg" "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/icons/hicolor/scalable/apps/"

# Create the main executable wrapper script
cat >"$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/bin/linuxtoys" <<'EOF'
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
chmod +x "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/bin/linuxtoys"

# Create orig tarball
tar -C "$OUTPUT_PATH" -cJf "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig.tar.xz" "linuxtoys_$LT_VERSION.orig/"

# Create debian package structure
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION"

# Copy the orig structure into the debian build directory
cp -rf "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig"/* "$OUTPUT_PATH/linuxtoys-$LT_VERSION/"

# Copy debian packaging files from existing structure (assuming they exist)
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/source"

# Create debian/control
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/control" <<'EOF'
Source: linuxtoys
Section: utils
Priority: optional
Maintainer: Victor Gregory <vicgregor@pm.me>
Rules-Requires-Root: no
Build-Depends:
 debhelper-compat (= 13),
Standards-Version: 4.7.2
Homepage: https://git.linux.toys/psygreg/linuxtoys

Package: linuxtoys
Architecture: amd64
Depends: bash, git, curl, wget, zenity, libgtk-3-0, gir1.2-gtk-3.0, gir1.2-vte-2.91
Description: A set of tools for Linux presented in a user-friendly way.
 .
 A menu with various handy tools for Linux gaming, optimization and other tweaks.
 .
 This package includes the precompiled Nuitka binary for optimized performance.
EOF

# Create debian/rules
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/rules" <<'EOF'
#!/usr/bin/make -f

%:
	dh $@

override_dh_install:
	dh_install
	# Set proper permissions for executable files after they are installed
	chmod +x debian/linuxtoys/usr/bin/linuxtoys
	chmod +x debian/linuxtoys/usr/share/linuxtoys/linuxtoys.bin
EOF
chmod +x "$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/rules"

# Create debian/copyright
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/copyright" <<'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: linuxtoys
Source: https://git.linux.toys/psygreg/linuxtoys

Files: *
Copyright: 2024-2025 Victor Gregory <vicgregor@pm.me>
License: GPL-3+

License: GPL-3+
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 .
 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 .
 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <https://www.gnu.org/licenses/>.
 .
 On Debian systems, the complete text of the GNU General
 Public License version 3 can be found in "/usr/share/common-licenses/GPL-3".
EOF

# Create debian/source/format
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/source/format" <<'EOF'
3.0 (quilt)
EOF

# Create initial debian/changelog
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/changelog" <<'EOF'
linuxtoys (5.0-1) noble; urgency=medium

  * Initial release with Nuitka precompiled binary
  * Improved performance with compiled binary
  * Application now runs from /usr/share/linuxtoys/linuxtoys.bin

 -- Victor Gregory <vicgregor@pm.me>  Mon, 19 Aug 2025 03:00:47 -0300
EOF

# Update changelog file with current date and version
day=$(date +%d)
day_abbr=$(LC_TIME=C date +%a) # This will always be in English
month=$(LC_TIME=C date +%b)
year=$(date +%Y)
changelog_line="linuxtoys (${LT_VERSION}-1) noble; urgency=medium"
changelog_line2=" -- Victor Gregory <vicgregor@pm.me>  ${day_abbr}, ${day} ${month} ${year} 03:00:47 -0300"
sed -i "1c\\$changelog_line" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/changelog"
sed -i "7c\\$changelog_line2" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/changelog"

# Update debian/install file for new structure
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/install" <<'EOF'
usr/bin/linuxtoys /usr/bin/
usr/share/linuxtoys /usr/share/
usr/share/applications/LinuxToys.desktop /usr/share/applications/
usr/share/icons/hicolor/scalable/apps/linuxtoys.svg /usr/share/icons/hicolor/scalable/apps/
EOF

# Build and upload for PPA first - doesn't work if done after building the package
if (
    cd "$OUTPUT_PATH/linuxtoys-$LT_VERSION" || exit 1
    debuild -S -sa -kvicgregor@pm.me
    sleep 1
    dput ppa:psygreg/linuxtoys "../linuxtoys_$LT_VERSION-1_source.changes"
    sleep 1
    # build package
    debuild -us -uc # this builder script requires devscripts!!
); then
    _msg info "Build and upload completed successfully!"
else
    _msg error "Build or upload failed!"
    exit 1
fi

# Clean up build artifacts but keep the final package
rm -rf "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/" "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig.tar.xz" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/"
_msg info "All done!"
sleep 1
