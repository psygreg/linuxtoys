#!/bin/bash
# Debian/DEB build script for LinuxToys
# Usage: build.sh <version> <output_path> <nuitka_binary_path>
# Example: build.sh 1.1 /tmp/builds /path/to/linuxtoys.bin

ROOT_DIR="$PWD"
while [[ "${ROOT_DIR##*/}" != "linuxtoys" && "$ROOT_DIR" != "/" ]]; do ROOT_DIR="${ROOT_DIR%/*}"; done
source "$ROOT_DIR/dev/libs/utils.lib"

# Check CLI arguments
if [ $# -ne 3 ]; then
    _msg error "Usage: $0 <version> <output_path> <nuitka_binary_path>"
    _msg info "Example: $0 1.1 /tmp/builds /path/to/linuxtoys.bin"
    exit 1
fi

LT_VERSION="$1"
OUTPUT_PATH="$2"
NUITKA_BINARY="$3"

_msg info "Building LinuxToys version $LT_VERSION for Debian/Ubuntu (Nuitka binary)..."
_msg info "Output path: $OUTPUT_PATH"
_msg info "Using Nuitka binary: $NUITKA_BINARY"

# Verify the Nuitka binary exists
if [ ! -f "$NUITKA_BINARY" ]; then
    _msg error "Nuitka binary not found at: $NUITKA_BINARY"
    exit 1
fi

# Delete output directory if it exists
rm -rf "$OUTPUT_PATH"
mkdir -p "$OUTPUT_PATH"

# Set up dir structure for the new Nuitka-based app
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION/usr/bin"
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION/usr/share/linuxtoys"
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION/usr/share/applications"
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/source"

_msg info "Copying Nuitka binary to package..."
cp "$NUITKA_BINARY" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/usr/share/linuxtoys/linuxtoys.bin"

# Verify linuxtoys.bin exists
if [ ! -f "$OUTPUT_PATH/linuxtoys-$LT_VERSION/usr/share/linuxtoys/linuxtoys.bin" ]; then
    _msg error "Failed to copy linuxtoys.bin to package!"
    exit 1
fi

# Make linuxtoys.bin executable
chmod +x "$OUTPUT_PATH/linuxtoys-$LT_VERSION/usr/share/linuxtoys/linuxtoys.bin"

# Copy desktop file
cp "$ROOT_DIR/src/LinuxToys.desktop" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/usr/share/applications/"

# Copy icon
cp "$ROOT_DIR/src/linuxtoys.svg" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/usr/share/icons/hicolor/scalable/apps/"

# Create the main executable wrapper script
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/usr/bin/linuxtoys" <<'EOF'
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
chmod +x "$OUTPUT_PATH/linuxtoys-$LT_VERSION/usr/bin/linuxtoys"

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
Depends: ${shlibs:Depends}, ${misc:Depends}, bash, git, curl, wget, zenity, libgtk-3-0, gir1.2-gtk-3.0, gir1.2-vte-2.91
Description: A set of tools for Linux presented in a user-friendly way.
 .
 A menu with various handy tools for Linux gaming, optimization and other tweaks.
 .
 This package includes the precompiled Nuitka binary for optimized performance.
EOF

# Create debian/rules with proper handling of binary
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/rules" <<'EOF'
#!/usr/bin/make -f

%:
	dh $@

override_dh_auto_build:
	# No build needed - binary is precompiled

override_dh_auto_test:
	# No tests needed

override_dh_install:
	dh_install
	chmod +x debian/linuxtoys/usr/bin/linuxtoys
	chmod +x debian/linuxtoys/usr/share/linuxtoys/linuxtoys.bin

override_dh_shlibdeps:
	dh_shlibdeps --dpkg-shlibdeps-params=--ignore-missing-info
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
3.0 (native)
EOF

# Create debian/changelog
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/changelog" <<'EOF'
linuxtoys (5.0-1) noble; urgency=medium

  * Initial release with Nuitka precompiled binary
  * Improved performance with compiled binary
  * Application now runs from /usr/share/linuxtoys/linuxtoys.bin

 -- Victor Gregory <vicgregor@pm.me>  Mon, 19 Aug 2025 03:00:47 -0300
EOF

# Update changelog file with current date and version
day=$(date +%d)
day_abbr=$(LC_TIME=C date +%a)
month=$(LC_TIME=C date +%b)
year=$(date +%Y)
changelog_line="linuxtoys (${LT_VERSION}-1) noble; urgency=medium"
changelog_line2=" -- Victor Gregory <vicgregor@pm.me>  ${day_abbr}, ${day} ${month} ${year} 03:00:47 -0300"
sed -i "1c\\$changelog_line" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/changelog"
sed -i "7c\\$changelog_line2" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/changelog"

# Create debian/install file
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/install" <<'EOF'
usr/bin/linuxtoys /usr/bin/
usr/share/linuxtoys /usr/share/
usr/share/applications/LinuxToys.desktop /usr/share/applications/
usr/share/icons/hicolor/scalable/apps/linuxtoys.svg /usr/share/icons/hicolor/scalable/apps/
EOF

# Create lintian overrides for prebuilt binary
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/linuxtoys.lintian-overrides" <<'EOF'
# Precompiled Nuitka binary - dynamic dependencies are intentional
linuxtoys binary: unresolvable-dependency-in-strict-d-lines
linuxtoys binary: embedded-library
EOF

# Build the package
if (
    cd "$OUTPUT_PATH/linuxtoys-$LT_VERSION" || exit 1
    _msg info "Building Debian package..."
    debuild -us -uc
); then
    _msg info "Build completed successfully!"
    _msg info "Package files:"
    ls -lah "$OUTPUT_PATH"/*.deb "$OUTPUT_PATH"/*.changes 2>/dev/null || true
else
    _msg error "Build failed!"
    exit 1
fi

# Clean up build artifacts but keep the final package
rm -rf "$OUTPUT_PATH/linuxtoys-$LT_VERSION/"
_msg info "All done!"
