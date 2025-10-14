#!/bin/bash

# ask version to package
read -p "Version number: " lt_version
# Clean up any existing build files
rm -rf linuxtoys-* linuxtoys_*.orig* *.tar.xz *.deb *.build* *.changes *.dsc

# set up dir structure for the new Python-based app
mkdir -p linuxtoys_$lt_version.orig/usr/bin
mkdir -p linuxtoys_$lt_version.orig/usr/share/linuxtoys
mkdir -p linuxtoys_$lt_version.orig/usr/share/applications
mkdir -p linuxtoys_$lt_version.orig/usr/share/icons/hicolor/scalable/apps

# Copy the Python app from p3 directory to proper location
cp -rf ../../../p3/* linuxtoys_$lt_version.orig/usr/share/linuxtoys/
# Clean up Python cache files to avoid warnings
find linuxtoys_$lt_version.orig/usr/share/linuxtoys/ -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find linuxtoys_$lt_version.orig/usr/share/linuxtoys/ -name "*.pyc" -delete 2>/dev/null || true
# Copy desktop file and icon
cp ../../LinuxToys.desktop linuxtoys_$lt_version.orig/usr/share/applications/
cp ../../linuxtoys.svg linuxtoys_$lt_version.orig/usr/share/icons/hicolor/scalable/apps/

# Create the main executable script
cat > linuxtoys_$lt_version.orig/usr/bin/linuxtoys << 'EOF'
#!/bin/bash
# Set process name for better desktop integration
export LINUXTOYS_PROCESS_NAME="linuxtoys"
cd /usr/share/linuxtoys
exec /usr/bin/python3 run.py "$@"
EOF
chmod +x linuxtoys_$lt_version.orig/usr/bin/linuxtoys

# Make sure all shell scripts are executable
find linuxtoys_$lt_version.orig/usr/share/linuxtoys/scripts/ -name "*.sh" -exec chmod +x {} \;
find linuxtoys_$lt_version.orig/usr/share/linuxtoys/helpers/ -name "*.sh" -exec chmod +x {} \;
chmod +x linuxtoys_$lt_version.orig/usr/share/linuxtoys/run.py

# Create orig tarball
tar -cJf linuxtoys_$lt_version.orig.tar.xz linuxtoys_$lt_version.orig/

# Create debian package structure
mkdir -p linuxtoys-$lt_version

# Copy the orig structure into the debian build directory
cp -rf linuxtoys_$lt_version.orig/* linuxtoys-$lt_version/

cd linuxtoys-$lt_version || exit 1

# Copy debian packaging files from existing structure (assuming they exist)
mkdir -p debian/source

# Create debian/control
cat > debian/control << 'EOF'
Source: linuxtoys
Section: utils
Priority: optional
Maintainer: Victor Gregory <vicgregor@pm.me>
Rules-Requires-Root: no
Build-Depends:
 debhelper-compat (= 13),
Standards-Version: 4.7.2
Homepage: https://github.com/psygreg/linuxtoys

Package: linuxtoys
Architecture: amd64
Depends: bash, git, curl, wget, zenity, python3, python3-gi, python3-requests, libgtk-3-0, gir1.2-gtk-3.0, gir1.2-vte-2.91
Description: A set of tools for Linux presented in a user-friendly way.
 .
 A menu with various handy tools for Linux gaming, optimization and other tweaks.
EOF

# Create debian/rules
cat > debian/rules << 'EOF'
#!/usr/bin/make -f

%:
	dh $@

override_dh_install:
	dh_install
	# Set proper permissions for executable files after they are installed
	chmod +x debian/linuxtoys/usr/bin/linuxtoys
	chmod +x debian/linuxtoys/usr/share/linuxtoys/run.py
	find debian/linuxtoys/usr/share/linuxtoys/scripts/ -name "*.sh" -exec chmod +x {} \;
	find debian/linuxtoys/usr/share/linuxtoys/helpers/ -name "*.sh" -exec chmod +x {} \;
EOF
chmod +x debian/rules

# Create debian/copyright
cat > debian/copyright << 'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: linuxtoys
Source: https://github.com/psygreg/linuxtoys

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
cat > debian/source/format << 'EOF'
3.0 (quilt)
EOF

# Create initial debian/changelog
cat > debian/changelog << 'EOF'
linuxtoys (5.0-1) noble; urgency=medium

  * Initial release for new Python-based structure
  * Added complete application structure with scripts, libs, and helpers

 -- Victor Gregory <vicgregor@pm.me>  Mon, 19 Aug 2025 03:00:47 -0300
EOF

# set changelog file
day=$(date +%d)
day_abbr=$(LC_TIME=C date +%a)  # This will always be in English
month=$(LC_TIME=C date +%b)
year=$(date +%Y)
changelog_line="linuxtoys (${lt_version}-1) noble; urgency=medium"
changelog_line2=" -- Victor Gregory <vicgregor@pm.me>  ${day_abbr}, ${day} ${month} ${year} 03:00:47 -0300"
sed -i "1c\\$changelog_line" debian/changelog
sed -i "6c\\$changelog_line2" debian/changelog

# Update debian/install file for new structure
cat > debian/install << 'EOF'
usr/bin/linuxtoys /usr/bin/
usr/share/linuxtoys /usr/share/
usr/share/applications/LinuxToys.desktop /usr/share/applications/
usr/share/icons/hicolor/scalable/apps/linuxtoys.svg /usr/share/icons/hicolor/scalable/apps/
EOF

# build and upload for PPA first - doesn't work if done after building the package
debuild -S -sa -kvicgregor@pm.me
sleep 1
dput ppa:psygreg/linuxtoys ../linuxtoys_$lt_version-1_source.changes
sleep 1

# build package
debuild -us -uc # this builder script requires devscripts!!

# Clean up build artifacts but keep the final package
cd ..
rm -rf linuxtoys_$lt_version.orig/ linuxtoys_$lt_version.orig.tar.xz linuxtoys-$lt_version/
echo "All done" && sleep 3 && exit 0
