#!/bin/bash
# COPR/RPM build script for LinuxToys
# Usage: build.sh <version> <output_path>
# Example: build.sh 1.1 /tmp/builds

ROOT_DIR="$PWD"
while [[ "${ROOT_DIR##*/}" != "linuxtoys" && "$ROOT_DIR" != "/" ]]; do ROOT_DIR="${ROOT_DIR%/*}"; done
source "$ROOT_DIR/dev/libs/utils.lib"

# Check CLI arguments
if [ $# -ne 2 ]; then
    _msg error "Usage: $0 <version> <output_path>"
    _msg info "Example: $0 1.1 /tmp/builds"
    exit 1
fi

LT_VERSION="$1"
OUTPUT_PATH="$2"

_msg info "Building LinuxToys version $LT_VERSION for COPR/RPM..."
_msg info "Output path: $OUTPUT_PATH"

# Delete output directory if it exists
rm -rf "$OUTPUT_PATH"

# Stage the complete source needed by the distro build environment.
mkdir -p "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION" "$OUTPUT_PATH/SOURCES"
cp -a "$ROOT_DIR/p3" "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/"
cp -a "$ROOT_DIR/src" "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/"
cp "$ROOT_DIR/Cargo.toml" "$ROOT_DIR/Cargo.lock" "$ROOT_DIR/pyproject.toml" \
    "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION/"

# Vendor locked Rust dependencies so sandboxed distro builds need no network.
mkdir -p "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION"/.cargo
(
    cd "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION"
    cargo vendor --locked --manifest-path "$ROOT_DIR/Cargo.toml" vendor > .cargo/config.toml
)

# Source tarball for COPR/RPM. Rust is compiled by rpmbuild, not prebuilt here.
tar -cJf "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION.tar.xz" -C "$OUTPUT_PATH/SOURCES" "linuxtoys-$LT_VERSION"
rm -rf "$OUTPUT_PATH/SOURCES/linuxtoys-$LT_VERSION"
# set up rpmbuild
# cp -r "$OUTPUT_PATH/linuxtoys-$LT_VERSION" "$HOME/rpmbuild/SOURCES/"
day=$(date +%d)
day_abbr=$(LC_TIME=C date +%a) # This will always be in English
month=$(LC_TIME=C date +%b)
year=$(date +%Y)
specfile_line="Version:        ${LT_VERSION}"
specfile_line2="* ${day_abbr} ${month} ${day} ${year} Victor Gregory <psygreg@pm.me> - ${LT_VERSION}"
sed -i "s/^Version:.*/$specfile_line/" ${ROOT_DIR}/dev/build/copr/linuxtoys.spec
sed -i "0,/^\\* .*Victor Gregory <psygreg@pm.me> - .*/s//$specfile_line2/" \
    "${ROOT_DIR}/dev/build/copr/linuxtoys.spec"
# build
# rm -r $HOME/rpmbuild # ensure there's no leftover build artifacts previous to building
# cp -r rpmbuild $HOME # only works with this setup on Silverblue, which is what I use
# cd $HOME/rpmbuild || exit 1
rpmbuild --define "_topdir $OUTPUT_PATH" -ba ${ROOT_DIR}/dev/build/copr/linuxtoys.spec

# Clean up build artifacts
# cd - || exit 1
# rm -rf linuxtoys-${LT_VERSION}/ linuxtoys-${LT_VERSION}.tar.xz
echo "All done" && sleep 3 && exit 0
