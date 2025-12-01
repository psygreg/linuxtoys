#!/bin/bash

# Master build script for LinuxToys packages
# This script builds DEB, RPM, and Arch packages in sequence
# Placeholder, maybe can be made into workflow later?

set -e  # Exit on any error

echo "=== LinuxToys Package Builder ==="
echo "This script will build DEB, RPM, and Arch packages"
echo ""

# Ask for version once
read -p "Version number to package: " lt_version

if [ -z "$lt_version" ]; then
    echo "Error: Version number is required!"
    exit 1
fi

# Update the version file
echo "$lt_version" > ../ver

echo ""
echo "Building packages for version: $lt_version"
echo ""

# Build DEB package
echo "=== Building DEB package ==="
cd deb
echo "$lt_version" | ./builddeb.sh
cd ..
echo "DEB package build completed!"
echo ""

# Build RPM package
echo "=== Building RPM package ==="
cd rpm
echo "$lt_version" | ./buildrpm.sh
cd ..
echo "RPM package build completed!"
echo ""

# Build Arch package
echo "=== Building Arch package ==="
cd pkgbuild
echo "$lt_version" | ./buildpkg.sh
cd ..
echo "Arch package build completed!"
echo ""

echo "=== All packages built successfully! ==="
echo "DEB package: deb/linuxtoys_${lt_version}-1_amd64.deb"
echo "RPM package: Check ~/rpmbuild/RPMS/x86_64/"
echo "Arch package: pkgbuild/linuxtoys-bin-${lt_version}-1-x86_64.pkg.tar.zst"
echo "Arch tarball: pkgbuild/linuxtoys-${lt_version}.tar.xz (kept for packaging)"
