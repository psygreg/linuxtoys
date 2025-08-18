#!/bin/bash
# ask version to package
read -p "Version number: " lt_version
# Clean up any existing build files
rm -rf linuxtoys-* linuxtoys_*.orig* *.tar.xz *.deb *.build* *.changes *.dsc

# set up dir structure for the new Python-based app
mkdir -p linuxtoys_$lt_version.orig/usr/bin/linuxtoys
mkdir -p linuxtoys_$lt_version.orig/usr/share/applications
mkdir -p linuxtoys_$lt_version.orig/usr/share/icons/hicolor/scalable/apps

# Copy the Python app from p3 directory
cp -rf ../../../p3/* linuxtoys_$lt_version.orig/usr/bin/linuxtoys/
# Copy desktop file and icon
cp ../../../src/LinuxToys.desktop linuxtoys_$lt_version.orig/usr/share/applications/
cp ../../../src/linuxtoys.png linuxtoys_$lt_version.orig/usr/share/icons/hicolor/scalable/apps/

# Create the main executable script
cat > linuxtoys_$lt_version.orig/usr/bin/linuxtoys << 'EOF'
#!/bin/bash
cd /usr/bin/linuxtoys
python3 run.py "$@"
EOF
chmod +x linuxtoys_$lt_version.orig/usr/bin/linuxtoys

# Create orig tarball
tar -cJf linuxtoys_$lt_version.orig.tar.xz linuxtoys_$lt_version.orig/

# Create debian package structure
mkdir -p linuxtoys-$lt_version

# Copy the orig structure into the debian build directory
cp -rf linuxtoys_$lt_version.orig/* linuxtoys-$lt_version/

cd linuxtoys-$lt_version || exit 1

# Copy debian packaging files from existing structure (assuming they exist)
if [ -d "../linuxtoys-4.3/debian" ]; then
    cp -rf ../linuxtoys-4.3/debian .
else
    echo "Error: debian packaging files not found!"
    exit 1
fi

# set changelog file
day=$(date +%d)
day_abbr=$(LC_TIME=C date +%a)  # This will always be in English
month=$(LC_TIME=C date +%b)
year=$(date +%Y)
changelog_line="linuxtoys (${lt_version}-1) noble; urgency=medium"
changelog_line2=" -- Victor Gregory <psygreg@pm.me>  ${day_abbr}, ${day} ${month} ${year} 3:00:47 -0300"
sed -i "1c\\$changelog_line" debian/changelog
sed -i "5c\\$changelog_line2" debian/changelog

# Update debian/install file for new structure
cat > debian/install << 'EOF'
usr/bin/linuxtoys /usr/bin/
usr/bin/linuxtoys/* /usr/bin/linuxtoys/
usr/share/applications/LinuxToys.desktop /usr/share/applications/
usr/share/icons/hicolor/scalable/apps/linuxtoys.png /usr/share/icons/hicolor/scalable/apps/
EOF

# build and upload for PPA first - doesn't work if done after building the package
debuild -S -sa
dput ppa:psygreg/linuxtoys *.changes

# build package
debuild -us -uc # this builder script requires devscripts!!

# Clean up build artifacts but keep the final package
cd ..
rm -rf linuxtoys_$lt_version.orig/ linuxtoys_$lt_version.orig.tar.xz linuxtoys-$lt_version/
echo "All done" && sleep 3 && exit 0
