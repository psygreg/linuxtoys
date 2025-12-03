#!/bin/bash

# Master build script for LinuxToys packages
# This script builds DEB, RPM, and Arch packages in sequence

set -e # Exit on any error
ROOT_DIR="$PWD"
while [[ "${ROOT_DIR##*/}" != "linuxtoys" && "$ROOT_DIR" != "/" ]]; do ROOT_DIR="${ROOT_DIR%/*}"; done

source "$ROOT_DIR/dev/libs/utils.lib"

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

BUILD_OUTPUT_DIR="$ROOT_DIR/dev/build_output/$LT_VERSION"

# Update the version file
echo "$LT_VERSION" >"$ROOT_DIR/src/ver"
_msg "info" "Building packages for version: $LT_VERSION"

# Build DEB package
_msg "info" "=== Building DEB package ==="
$ROOT_DIR/dev/build/deb/build.sh "$LT_VERSION" "$BUILD_OUTPUT_DIR/deb"
_msg "info" "DEB package build completed!"

# Build RPM package
_msg "info" "=== Building RPM package ==="
$ROOT_DIR/dev/build/rpm/build.sh "$LT_VERSION" "$BUILD_OUTPUT_DIR/rpm"
_msg "info" "RPM package build completed!"

# Build Arch package
_msg "info" "=== Building Arch package ==="
$ROOT_DIR/dev/build/pkg/build.sh "$LT_VERSION" "$BUILD_OUTPUT_DIR/pkg"
_msg "info" "Arch package build completed!"

# Deprecated and removed
# Build AppImage package
# _msg "info" "=== Building AppImage package ==="
# mkdir -p "$BUILD_OUTPUT_DIR/appimage"
# ./appimage/build.sh "$LT_VERSION" "$BUILD_OUTPUT_DIR/appimage"
# _msg "info" "AppImage package build completed!"

_msg "info" "=== All packages built successfully! ==="
_msg "info" "Artifacts are located in: $BUILD_OUTPUT_DIR"
