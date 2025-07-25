#!/bin/bash

# ensure correct working directory
cd "$(dirname "$(realpath "$0")")"
# make directory structure
mkdir -p appimagebuild/LinuxToys.AppDir/usr/bin
mkdir -p appimagebuild/LinuxToys.AppDir/usr/lib

# get updated LinuxToys and set proper filename
cp src/linuxtoys.sh linuxtoys1.sh
mv linuxtoys1.sh linuxtoys
mv -f linuxtoys appimagebuild/LinuxToys.AppDir/usr/bin/

# fetch dependencies
cp /usr/bin/curl /usr/bin/wget /usr/bin/git /usr/bin/whiptail /usr/bin/bash appimagebuild/LinuxToys.AppDir/usr/bin/
# fetch libraries for dependencies
for bin in curl wget git whiptail bash; do
    for dep in $(ldd /usr/bin/$bin | awk '{if ($3 ~ /^\//) print $3}'); do
        cp -u --parents "$dep" appimagebuild/LinuxToys.AppDir/usr/lib/;
    done;
done

# adjust library dir structure
mv appimagebuild/LinuxToys.AppDir/usr/lib/lib/x86_64-linux-gnu appimagebuild/LinuxToys.AppDir/usr/
rm -r appimagebuild/LinuxToys.AppDir/usr/lib
mv appimagebuild/LinuxToys.AppDir/usr/x86_64-linux-gnu appimagebuild/LinuxToys.AppDir/usr/lib

# build appimage
./appimagebuild/appimagetool-x86_64.AppImage appimagebuild/LinuxToys.AppDir
