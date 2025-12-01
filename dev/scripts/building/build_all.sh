#!/bin/bash

# Master build script for LinuxToys packages
# This script builds DEB, RPM, and Arch packages in sequence

set -e  # Exit on any error
_import_lib() {
    local lib_path="$1"
    if [ -f "$lib_path" ]; then
        source "$lib_path"
    else
        echo -e "\033[31mERROR:\033[0m Library not found: $lib_path. YOU must be in the same folder as the script."
        exit 1
    fi
}
# Source utils library
_import_lib "../libs/utils.lib"

_msg "info" "=== LinuxToys Package Builder ==="
_msg "info" "This script will build DEB, RPM, Arch, and AppImage packages"

# Get version
if [ -n "$1" ]; then
    LT_VERSION="$1"
else
    read -p "Version number to package: " LT_VERSION
fi

if [ -z "$LT_VERSION" ]; then
    _msg "error" "Version number is required!"
    exit 1
fi

# Update the version file
echo "$LT_VERSION" > ../../../src/ver

_msg "info" "Building packages for version: $LT_VERSION"

# Define Output Directory
BUILD_OUTPUT_DIR="$(pwd)/../../build_output/$LT_VERSION"
mkdir -p "$BUILD_OUTPUT_DIR"

# Build DEB package
_msg "info" "=== Building DEB package ==="
mkdir -p "$BUILD_OUTPUT_DIR/deb"
cd deb
./builddeb.sh "$LT_VERSION" "$BUILD_OUTPUT_DIR/deb"
cd ..
_msg "info" "DEB package build completed!"

# Build RPM package
_msg "info" "=== Building RPM package ==="
mkdir -p "$BUILD_OUTPUT_DIR/rpm"
cd rpm
./buildrpm.sh "$LT_VERSION" "$BUILD_OUTPUT_DIR/rpm"
cd ..
_msg "info" "RPM package build completed!"

# Build Arch package
_msg "info" "=== Building Arch package ==="
mkdir -p "$BUILD_OUTPUT_DIR/pkgbuild"
cd pkgbuild
./buildpkg.sh "$LT_VERSION" "$BUILD_OUTPUT_DIR/pkgbuild"
cd ..
_msg "info" "Arch package build completed!"

# Build AppImage package
_msg "info" "=== Building AppImage package ==="
mkdir -p "$BUILD_OUTPUT_DIR/appimage"
cd appimage
./buildappimage.sh "$LT_VERSION" "$BUILD_OUTPUT_DIR/appimage"
cd ..
_msg "info" "AppImage package build completed!"

_msg "info" "=== All packages built successfully! ==="
_msg "info" "Artifacts are located in: $BUILD_OUTPUT_DIR"
