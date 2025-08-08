#!/bin/bash
# ask version to package
read -p "Version number: " lt_version
# use deb tarball for directory structure -- it does require having built the deb package first!
cp ../deb/linuxtoys_${lt_version}.orig.tar.xz .
mv linuxtoys_${lt_version}.orig.tar.xz linuxtoys-${lt_version}.tar.xz
# update version and hash on PKGBUILD file
hash=$(sha256sum linuxtoys-${lt_version}.tar.xz | cut -d' ' -f1)
sed -i "s/pkgver='[^']*'/pkgver='$lt_version'/" PKGBUILD
sed -i "s/sha256sums=('[^']*')/sha256sums=('$hash')/" PKGBUILD
echo "All done" && sleep 3 && exit 0
