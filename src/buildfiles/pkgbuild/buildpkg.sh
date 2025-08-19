#!/bin/bash
# ask version to package
read -p "Version number: " lt_version
# Clean up any existing build files except the final tarball
rm -rf linuxtoys_${lt_version}.orig linuxtoys-${lt_version} pkg src

# Create directory structure for the Python app
mkdir -p linuxtoys-${lt_version}/usr/bin
mkdir -p linuxtoys-${lt_version}/usr/share/linuxtoys
mkdir -p linuxtoys-${lt_version}/usr/share/applications
mkdir -p linuxtoys-${lt_version}/usr/share/icons/hicolor/scalable/apps

# Copy the Python app from p3 directory
cp -rf ../../../p3/* linuxtoys-${lt_version}/usr/share/linuxtoys/
# Copy desktop file and icon
cp ../../LinuxToys.desktop linuxtoys-${lt_version}/usr/share/applications/
cp ../../linuxtoys.png linuxtoys-${lt_version}/usr/share/icons/hicolor/scalable/apps/

# Create the main executable script
cat > linuxtoys-${lt_version}/usr/bin/linuxtoys << 'EOF'
#!/bin/bash
# Set process name for better desktop integration
export LINUXTOYS_PROCESS_NAME="linuxtoys"
cd /usr/share/linuxtoys
exec python3 run.py "$@"
EOF
chmod +x linuxtoys-${lt_version}/usr/bin/linuxtoys

# Make sure all shell scripts are executable
find linuxtoys-${lt_version}/usr/share/linuxtoys/scripts/ -name "*.sh" -exec chmod +x {} \;
find linuxtoys-${lt_version}/usr/share/linuxtoys/helpers/ -name "*.sh" -exec chmod +x {} \;
chmod +x linuxtoys-${lt_version}/usr/share/linuxtoys/run.py

# Create tarball (this will be kept for Arch packaging)
tar -cJf linuxtoys-${lt_version}.tar.xz linuxtoys-${lt_version}/
# update version and hash on PKGBUILD file
hash=$(sha256sum linuxtoys-${lt_version}.tar.xz | cut -d' ' -f1)
sed -i "s/pkgver='[^']*'/pkgver='$lt_version'/" PKGBUILD
sed -i "s/sha256sums=('[^']*')/sha256sums=('$hash')/" PKGBUILD

# build package
makepkg -s

# Clean up build artifacts but keep the tarball for Arch packaging
rm -rf linuxtoys-${lt_version}/
echo "All done. Tarball linuxtoys-${lt_version}.tar.xz kept for Arch packaging." && sleep 3 && exit 0
