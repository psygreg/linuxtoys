#!/bin/bash
# ask version to package
read -p "Version number: " lt_version
# use deb tarball for directory structure -- it does require having built the deb package first!
cp -r ../deb/linuxtoys_${lt_version}.orig .
mv linuxtoys_${lt_version}.orig linuxtoys-$lt_version
tar -cJf linuxtoys-${lt_version}.tar.xz linuxtoys-$lt_version/
# update version and hash on PKGBUILD file
hash=$(sha256sum linuxtoys-${lt_version}.tar.xz | cut -d' ' -f1)
sed -i "s/pkgver='[^']*'/pkgver='$lt_version'/" PKGBUILD
sed -i "s/sha256sums=('[^']*')/sha256sums=('$hash')/" PKGBUILD
rm -r ../deb/linuxtoys_${lt_version}.orig
echo "All done" && sleep 3 && exit 0
