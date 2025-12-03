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

# Get container names
read -p "Fedora container name (for RPM, Copr, Nuitka): " FEDORA_CONTAINER
read -p "Arch container name (for PKG): " ARCH_CONTAINER
read -p "Debian container name (for DEB): " DEBIAN_CONTAINER

if [ -z "$FEDORA_CONTAINER" ] || [ -z "$ARCH_CONTAINER" ] || [ -z "$DEBIAN_CONTAINER" ]; then
    _msg "error" "All container names are required!"
    exit 1
fi

BUILD_OUTPUT_DIR="$ROOT_DIR/dev/build_output/$LT_VERSION"

_msg "info" "Building packages for version: $LT_VERSION"
_msg "info" "Updating version file..."
cp "$ROOT_DIR/src/ver" "$ROOT_DIR/src/ver.bkp"
echo "$LT_VERSION" >"$ROOT_DIR/src/ver"

# Build RPM package
_msg "info" "=== Building RPM package (Fedora) ==="
distrobox-enter -n "$FEDORA_CONTAINER" -- "$ROOT_DIR/dev/build/rpm/build.sh" "$LT_VERSION" "$BUILD_OUTPUT_DIR/rpm"
_msg "info" "RPM package build completed!"

# Build Copr package
_msg "info" "=== Building Copr package (Fedora) ==="
distrobox-enter -n "$FEDORA_CONTAINER" -- "$ROOT_DIR/dev/build/copr/build.sh" "$LT_VERSION" "$BUILD_OUTPUT_DIR/copr"
_msg "info" "Copr package build completed!"

# Build Nuitka package
_msg "info" "=== Building Nuitka package (Fedora) ==="
distrobox-enter -n "$FEDORA_CONTAINER" -- "$ROOT_DIR/dev/build/nuitka/build.sh" "$LT_VERSION" "$BUILD_OUTPUT_DIR/nuitka"
_msg "info" "Nuitka package build completed!"

# Build Arch package
_msg "info" "=== Building Arch package (Arch) ==="
distrobox-enter -n "$ARCH_CONTAINER" -- "$ROOT_DIR/dev/build/pkg/build.sh" "$LT_VERSION" "$BUILD_OUTPUT_DIR/pkg"
_msg "info" "Arch package build completed!"

# Build DEB package
_msg "info" "=== Building DEB package (Debian) ==="
distrobox-enter -n "$DEBIAN_CONTAINER" -- "$ROOT_DIR/dev/build/deb/build.sh" "$LT_VERSION" "$BUILD_OUTPUT_DIR/deb"
_msg "info" "DEB package build completed!"

# Deprecated and removed
# Build AppImage package
# _msg "info" "=== Building AppImage package ==="
# mkdir -p "$BUILD_OUTPUT_DIR/appimage"
# ./appimage/build.sh "$LT_VERSION" "$BUILD_OUTPUT_DIR/appimage"
# _msg "info" "AppImage package build completed!"

_msg "info" "=== All packages built successfully! ==="
_msg "info" "Artifacts are located in: $BUILD_OUTPUT_DIR"
