#!/bin/bash

# ensure correct working directory
cd "$(dirname "$(realpath "$0")")"
# make directory structure
mkdir -p appimagebuild/LinuxToys.AppDir/usr/bin
mkdir -p appimagebuild/LinuxToys.AppDir/usr/lib64
mkdir -p appimagebuild/LinuxToys.AppDir/etc/ssl/certs/

# get updated LinuxToys and set proper filename
cp -f appimage/linuxtoys.sh appimagebuild/LinuxToys.AppDir/usr/bin/
mv appimagebuild/LinuxToys.AppDir/usr/bin/linuxtoys.sh appimagebuild/LinuxToys.AppDir/usr/bin/linuxtoys

# get updated libraries
cp -f appimage/linuxtoys.lib appimagebuild/LinuxToys.AppDir/usr/bin/
cp -f src/lang/* appimagebuild/LinuxToys.AppDir/usr/bin/

# fetch dependencies
cp -u /usr/bin/curl /usr/bin/wget /usr/bin/git /usr/bin/zenity /usr/bin/bash appimagebuild/LinuxToys.AppDir/usr/bin/
cp -u /usr/bin/git-* appimagebuild/LinuxToys.AppDir/usr/bin/
cp -u /etc/ssl/certs/ca-certificates.crt appimagebuild/LinuxToys.AppDir/etc/ssl/certs/

# fetch libraries for dependencies
for bin in curl wget git bash; do
    for dep in $(ldd /usr/bin/$bin | awk '{if ($3 ~ /^\//) print $3}'); do
        cp -u --parents "$dep" appimagebuild/LinuxToys.AppDir/usr/lib64/
    done
done
# libwget fix
cp -u /usr/lib/x86_64-linux-gnu/libwget.so.3 appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu/
cp -u /usr/lib/x86_64-linux-gnu/libgnutls-dane.so.0 appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu/
cp -u /usr/lib/x86_64-linux-gnu/libunbound.so.8 appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu/
cp -u /usr/lib/x86_64-linux-gnu/libduktape.so.207 appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu/
cp -u /usr/lib/x86_64-linux-gnu/libproxy.so.1 appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu/
cp -u /usr/lib/x86_64-linux-gnu/libevent-2.1.so.7 appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu/
cp -u /usr/lib/x86_64-linux-gnu/liblz.so.1 appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu/

# get git-core
mkdir -p appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu/git-core
cp -u /usr/lib/git-core/git-* appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu/git-core/
# get git helpers dependencies
for helper in /usr/lib/git-core/*; do
    for hldep in $(ldd $helper | awk '{if ($3 ~ /^\//) print $3}'); do
        cp -u --parents "$hldep" appimagebuild/LinuxToys.AppDir/usr/lib64/
    done
done
# cp -u /usr/lib/x86_64-linux-gnu/libcurl-gnutls.so.4 appimagebuild/LinuxToys-Atom.AppDir/usr/lib64/lib/x86_64-linux-gnu/

# adjust library dir structure
mv appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu appimagebuild/LinuxToys.AppDir/usr/
rm -r appimagebuild/LinuxToys.AppDir/usr/lib64
mv appimagebuild/LinuxToys.AppDir/usr/x86_64-linux-gnu appimagebuild/LinuxToys.AppDir/usr/lib64

# build appimage
./appimagebuild/appimagetool-x86_64.AppImage appimagebuild/LinuxToys.AppDir
