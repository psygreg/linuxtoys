#!/bin/bash

# Check if rpmbuild is available
if ! command -v rpmbuild &> /dev/null; then
    echo "Error: rpmbuild is not installed."
    echo "Please install it with: sudo dnf install rpm-build rpmdevtools"
    echo "Or on other distributions: sudo apt install rpm-build (Ubuntu/Debian)"
    exit 1
fi

# ask version to package
read -p "Version number: " lt_version
# Clean up any existing build files
rm -rf linuxtoys-* *.tar.xz

# set up directory and copy files from p3
mkdir -p linuxtoys-${lt_version}/usr/bin
mkdir -p linuxtoys-${lt_version}/usr/share/linuxtoys
mkdir -p linuxtoys-${lt_version}/usr/share/applications
mkdir -p linuxtoys-${lt_version}/usr/share/icons/hicolor/scalable/apps
mkdir -p rpmbuild/SOURCES

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
exec /usr/bin/python3 run.py "$@"
EOF
chmod +x linuxtoys-${lt_version}/usr/bin/linuxtoys

# Make sure all shell scripts are executable
find linuxtoys-${lt_version}/usr/share/linuxtoys/scripts/ -name "*.sh" -exec chmod +x {} \;
find linuxtoys-${lt_version}/usr/share/linuxtoys/helpers/ -name "*.sh" -exec chmod +x {} \;
chmod +x linuxtoys-${lt_version}/usr/share/linuxtoys/run.py

# tarball it
tar -cJf linuxtoys-${lt_version}.tar.xz linuxtoys-${lt_version}/
# set up rpmbuild
cp linuxtoys-${lt_version}.tar.xz rpmbuild/SOURCES
day=$(date +%d)
day_abbr=$(LC_TIME=C date +%a)  # This will always be in English
month=$(LC_TIME=C date +%b)
year=$(date +%Y)
specfile_line="Version:        ${lt_version}"
specfile_line2="* ${day_abbr} ${month} ${day} ${year} Victor Gregory <psygreg@pm.me> - ${lt_version}"
sed -i "2c\\$specfile_line" rpmbuild/SPECS/linuxtoys.spec
sed -i "64c\\$specfile_line2" rpmbuild/SPECS/linuxtoys.spec
# build
rm -r $HOME/rpmbuild # ensure there's no leftover build artifacts previous to building
cp -r rpmbuild $HOME # only works with this setup on Silverblue, which is what I use
cd $HOME/rpmbuild || exit 1
rpmbuild -ba SPECS/linuxtoys.spec

# Clean up build artifacts
cd - || exit 1
rm -rf linuxtoys-${lt_version}/ linuxtoys-${lt_version}.tar.xz
echo "All done" && sleep 3 && exit 0