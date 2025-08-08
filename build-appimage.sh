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

# excluding libraries that may break packaging
readarray -t exclude_list < appimagebuild/exclude.list
should_exclude() {
    local lib_name="$1"
    local base_name=$(basename "$lib_name")
    
    for excluded in "${exclude_list[@]}"; do
        # skip empty lines and comments
        [[ -z "$excluded" || "$excluded" =~ ^[[:space:]]*# ]] && continue
        # check if the basename matches the excluded name
        if [[ "$base_name" == "$excluded" ]]; then
            return 0  # should exclude (true)
        fi
    done
    return 1  # should not exclude (false)
}

# fetch libraries for dependencies
for bin in curl wget git bash zenity; do
    for dep in $(ldd /usr/bin/$bin | awk '{if ($3 ~ /^\//) print $3}'); do
        if ! should_exclude "$dep"; then
            cp -u --parents "$dep" appimagebuild/LinuxToys.AppDir/usr/lib64/
        fi
    done
done
# libwget fix
cp -u /usr/lib/libwget.so.2 appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu/
for lib in /usr/lib/x86_64-linux-gnu/libwget.so.3; do
    for dep in $(ldd $lib | awk '{if ($3 ~ /^\//) print $3}'); do
        if ! should_exclude "$dep"; then
            cp -u --parents "$dep" appimagebuild/LinuxToys.AppDir/usr/lib64/
        fi
    done
done

# get git-core
mkdir -p appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu/git-core
cp -u /usr/lib/git-core/git-* appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu/git-core/
# get git helpers dependencies
for helper in /usr/lib/git-core/*; do
    for hldep in $(ldd $helper | awk '{if ($3 ~ /^\//) print $3}'); do
        if ! should_exclude "$hldep"; then
            cp -u --parents "$hldep" appimagebuild/LinuxToys.AppDir/usr/lib64/
        fi
    done
done
# cp -u /usr/lib/x86_64-linux-gnu/libcurl-gnutls.so.4 appimagebuild/LinuxToys-Atom.AppDir/usr/lib64/lib/x86_64-linux-gnu/

# adjust library dir structure
mv appimagebuild/LinuxToys.AppDir/usr/lib64/lib/x86_64-linux-gnu appimagebuild/LinuxToys.AppDir/usr/
rm -r appimagebuild/LinuxToys.AppDir/usr/lib64
mv appimagebuild/LinuxToys.AppDir/usr/x86_64-linux-gnu appimagebuild/LinuxToys.AppDir/usr/lib64

# build appimage
./appimagebuild/appimagetool-x86_64.AppImage appimagebuild/LinuxToys.AppDir
