#!/bin/bash
# Debian/DEB build script for LinuxToys
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

# LINUXTOYS_TEST_MODE arrives as 1/0 from local runs and as true/false from
# the release workflow; normalize it so every comparison in this script is
# exact regardless of the caller.
case "${LINUXTOYS_TEST_MODE:-0}" in
    1|true|yes) PPA_TEST_MODE=1 ;;
    *)          PPA_TEST_MODE=0 ;;
esac

_msg info "Building LinuxToys version $LT_VERSION for Debian/Ubuntu..."
_msg info "Output path: $OUTPUT_PATH"

# Delete output directory if it exists
rm -rf "$OUTPUT_PATH"
mkdir -p "$OUTPUT_PATH"

# set up dir structure for the new Python-based app
mkdir -p "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/bin"
mkdir -p "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys"
mkdir -p "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/applications"
mkdir -p "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/metainfo"
mkdir -p "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/mime/packages"
mkdir -p "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/icons/hicolor/scalable/apps"

# Copy the Python app from p3 directory to proper location
cp -rf "$ROOT_DIR/p3"/* "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys/"
# Include Rust/PyO3 sources so Debian builds the extension in its own build environment.
cp -a "$ROOT_DIR/p3" "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/"
cp -a "$ROOT_DIR/src" "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/"
cp "$ROOT_DIR/Cargo.toml" "$ROOT_DIR/Cargo.lock" "$ROOT_DIR/pyproject.toml" \
    "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/"

# Development builds place native Rust artifacts in p3/app. They are build
# products, not upstream source, and must never enter the Debian orig tarball.
rm -f \
    "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/p3/app/_catalog_rs.abi3.so" \
    "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/p3/app/liblinuxtoys_gui.so" \
    "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys/app/_catalog_rs.abi3.so" \
    "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys/app/liblinuxtoys_gui.so"

# Vendor locked Rust dependencies so sandboxed distro builds need no network.
mkdir -p "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig"/.cargo
(
    cd "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig"
    cargo vendor --locked --manifest-path "$ROOT_DIR/Cargo.toml" vendor > .cargo/config.toml
)

# Prune the vendored crates' Cargo.toml.orig backups and their matching
# entries from .cargo-checksum.json. dpkg and debhelper treat *.orig files in
# the source tree as patch leftovers and can strip them from the build tree
# while the orig tarball keeps them, which leaves cargo's vendored-source
# checksums referencing files that no longer exist and aborts the local
# binary build. Dropping both sides keeps the vendored source reproducibly
# checksum-verified, removes nothing the crates need to compile, and slims
# the Debian source upload.
python3 - "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig" <<'PYVEND'
import json, os, sys

vendor = os.path.join(sys.argv[1], "vendor")
if not os.path.isdir(vendor):
    raise SystemExit("vendor directory missing after cargo vendor")
for entry in sorted(os.listdir(vendor)):
    crate = os.path.join(vendor, entry)
    jpath = os.path.join(crate, ".cargo-checksum.json")
    if not os.path.isfile(jpath):
        continue
    with open(jpath) as fh:
        data = json.load(fh)
    files = data.get("files", {})
    pruned = False
    for name in list(files):
        if name.endswith(".orig"):
            path = os.path.join(crate, name)
            if os.path.exists(path):
                os.remove(path)
            del files[name]
            pruned = True
    if pruned:
        with open(jpath, "w") as fh:
            json.dump(data, fh, separators=(",", ":"), sort_keys=True)
print("Vendored Cargo.toml.orig backups pruned from", vendor)
PYVEND
# Clean up Python cache files from the entire staged source tree
find "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
# Copy desktop file and icon
cp "$ROOT_DIR/src/toys.linux.LinuxToys.desktop" "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/applications/"
cp "$ROOT_DIR/src/linuxtoys-mimetypes.xml" "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/mime/packages/"
cp "$ROOT_DIR/src/toys.linux.LinuxToys.metainfo.xml" "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/metainfo/"
cp "$ROOT_DIR/src/linuxtoys.svg" "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/icons/hicolor/scalable/apps/"

# Create the main executable script
cat >"$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/bin/linuxtoys" <<'EOF'
#!/bin/bash
# Set process name for better desktop integration
export LINUXTOYS_PROCESS_NAME="linuxtoys"
# Enable CLI mode if arguments are provided
if [ "$#" -eq 1 ] && [[ "$1" == linuxtoys://* ]]; then
    unset EASY_CLI
elif [ "$#" -gt 0 ]; then
    export EASY_CLI=1
fi
cd /usr/share/linuxtoys
exec /usr/bin/python3 linuxtoys.py "$@"
EOF
chmod +x "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/bin/linuxtoys"

# Make the installed application accessible to non-root users while
# retaining executable bits on bundled helpers and native binaries.
find "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys" -type d -exec chmod 755 {} +
find "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys" -type f -exec chmod a+r {} +

# Make sure all shell scripts are executable
find "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys/scripts/" -name "*.sh" -exec chmod +x {} \;
chmod +x "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/usr/share/linuxtoys/linuxtoys.py"

# Create orig tarball
tar -C "$OUTPUT_PATH" -cJf "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig.tar.xz" "linuxtoys_$LT_VERSION.orig/"

# Create debian package structure
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION"

# Copy the complete orig structure into the debian build directory, including dotfiles such as .cargo
cp -a "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/." "$OUTPUT_PATH/linuxtoys-$LT_VERSION/"

# Copy debian packaging files from existing structure (assuming they exist)
mkdir -p "$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/source"

# Create debian/control
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/control" <<'EOF'
Source: linuxtoys
Section: utils
Priority: optional
Maintainer: Victor Gregory <psygreg@icloud.com>
Rules-Requires-Root: no
Build-Depends:
 debhelper-compat (= 13),
 cargo,
 rustc,
 python3-dev,
 python3-maturin,
 pkgconf,
 libgtk-3-dev,
 patchelf,
Standards-Version: 4.6.2
Homepage: https://linux.toys

Package: linuxtoys
Architecture: amd64
Depends: ${shlibs:Depends},
 ${misc:Depends},
 bash,
 git,
 curl,
 wget,
 zenity,
 appstream,
 libappstream5,
 util-linux,
 python3,
 python3-gi,
 python3-requests,
 adwaita-icon-theme | xapp-symbolic-icons,
 libgtk-3-0,
 gir1.2-gtk-3.0,
 gir1.2-vte-2.91,
 gir1.2-appstream-1.0,
 webp-pixbuf-loader,
 sudo | sudo-rs
Description: For everything Linux - tools, tweaks and software manager - ready for the age of AI.
EOF

# Create debian/rules
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/rules" <<'EOF'
#!/usr/bin/make -f

%:
	dh $@

override_dh_auto_build:
	mkdir -p target/wheels/catalog
	cd src/catalog-rs && maturin build --release --locked --out ../../target/wheels/catalog
	cargo build --release --locked --manifest-path src/gui-rs/Cargo.toml
	rm -rf wheel-unpack-catalog
	python3 -m zipfile -e $$(find target/wheels/catalog -maxdepth 1 -type f -name '*.whl' -print -quit) wheel-unpack-catalog
	test -n "$$(find wheel-unpack-catalog -type f -name '_catalog_rs*.so' -print -quit)"
	test -f target/release/liblinuxtoys_gui.so

override_dh_install:
	dh_install
	# Normalize the installed tree even if upstream sources have restrictive modes.
	find debian/linuxtoys/usr/share/linuxtoys -type d -exec chmod 755 {} +
	find debian/linuxtoys/usr/share/linuxtoys -type f -exec chmod a+r {} +
	install -m 755 $$(find wheel-unpack-catalog -type f -name '_catalog_rs*.so' -print -quit) debian/linuxtoys/usr/share/linuxtoys/app/
	install -m 755 target/release/liblinuxtoys_gui.so debian/linuxtoys/usr/share/linuxtoys/app/liblinuxtoys_gui.so
	test -f debian/linuxtoys/usr/share/linuxtoys/app/_catalog_rs.abi3.so
	test -f debian/linuxtoys/usr/share/linuxtoys/app/liblinuxtoys_gui.so
	chmod +x debian/linuxtoys/usr/bin/linuxtoys
	chmod +x debian/linuxtoys/usr/share/linuxtoys/linuxtoys.py
	find debian/linuxtoys/usr/share/linuxtoys/scripts/ -name "*.sh" -exec chmod +x {} \;
EOF
chmod +x "$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/rules"

# Create debian/copyright. The metainfo is CC0-1.0 (AppStream only accepts permissive
# metadata licenses), so it needs its own stanza instead of falling under the GPL code.
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/copyright" <<'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: linuxtoys
Source: https://git.linux.toys/psygreg/linuxtoys

Files: *
Copyright: 2024-2025 Victor Gregory <psygreg@icloud.com>
License: GPL-3+

License: GPL-3+
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 .
 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 .
 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <https://www.gnu.org/licenses/>.
 .
 On Debian systems, the complete text of the GNU General
 Public License version 3 can be found in "/usr/share/common-licenses/GPL-3".

Files: src/toys.linux.LinuxToys.metainfo.xml usr/share/metainfo/toys.linux.LinuxToys.metainfo.xml
Copyright: 2024-2025 Victor Gregory <psygreg@icloud.com>
License: CC0-1.0

License: CC0-1.0
 To the extent possible under law, the author has waived all copyright and
 related or neighboring rights to this AppStream metainfo file.
 .
 On Debian systems, the complete text of the CC0 1.0 Universal license can be
 found in "/usr/share/common-licenses/CC0-1.0".
EOF

# Create debian/source/format
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/source/format" <<'EOF'
3.0 (quilt)
EOF

# Cargo's vendored winapi target crates contain upstream Windows GNU import
# libraries. Lintian's source unpacker tries to inspect these .a files with the
# host ar and emits unpack-message-for-orig. They are kept byte-for-byte intact
# because Cargo's vendored source is checksum-verified.
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/source/lintian-overrides" <<'EOF'
linuxtoys source: unpack-message-for-orig *vendor/winapi-*-pc-windows-gnu/lib/*.a*
EOF

# Create initial debian/changelog
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/changelog" <<'EOF'
linuxtoys (5.0-1) noble; urgency=medium

  * Initial release for new Python-based structure
  * Added complete application structure with scripts, libs, and helpers

 -- Victor Gregory <psygreg@icloud.com>  Mon, 19 Aug 2025 03:00:47 -0300
EOF

# set changelog file
day=$(date +%d)
day_abbr=$(LC_TIME=C date +%a) # This will always be in English
month=$(LC_TIME=C date +%b)
year=$(date +%Y)
changelog_line="linuxtoys (${LT_VERSION}-1) noble; urgency=medium"
changelog_line2=" -- Victor Gregory <psygreg@icloud.com>  ${day_abbr}, ${day} ${month} ${year} 03:00:47 -0300"
sed -i "1c\\$changelog_line" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/changelog"
sed -i "6c\\$changelog_line2" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/changelog"

# Update debian/install file for new structure
cat >"$OUTPUT_PATH/linuxtoys-$LT_VERSION/debian/install" <<'EOF'
usr/bin/linuxtoys /usr/bin/
usr/share/linuxtoys /usr/share/
usr/share/applications/toys.linux.LinuxToys.desktop /usr/share/applications/
usr/share/mime/packages/linuxtoys-mimetypes.xml /usr/share/mime/packages/
usr/share/metainfo/toys.linux.LinuxToys.metainfo.xml /usr/share/metainfo/
usr/share/icons/hicolor/scalable/apps/linuxtoys.svg /usr/share/icons/hicolor/scalable/apps/
EOF

# Test-mode PPA upload: the dput probe only proves the client-side transfer
# into the Launchpad incoming queue; Launchpad validates duplicate versions
# and signatures asynchronously (and answers by email), so the job stays
# green either way and the transfer log is dumped with a clear annotation.
ppa_test_upload () {
    local log rc
    log="$OUTPUT_PATH/dput-test-output.log"
    echo "---- dput transfer log (test output) ----"
    dput ppa:psygreg/linuxtoys "../linuxtoys_$LT_VERSION-1_source.changes" >"$log" 2>&1
    rc=$?
    cat "$log"
    echo "::notice::Test-mode dput probe finished (rc=$rc). Launchpad only reports duplicate-version or signature rejections asynchronously through the PPA queue - check the queue/email for the authoritative outcome; 'Successfully uploaded' here is not a Launchpad acceptance."
    return 0
}

ppa_check_state () {
    # Queries the public Launchpad API for linuxtoys <version> in the
    # psygreg/linuxtoys PPA and prints "absent", a source status
    # (Published/Superseded/...) or "error" when the API is unreachable.
    python3 - "$1" <<'LPPY'
import json, sys, urllib.request, urllib.parse
version = sys.argv[1]
url = "https://api.launchpad.net/1.0/~psygreg/+archive/ubuntu/linuxtoys" + "?" + urllib.parse.urlencode({
    "ws.op": "getPublishedSources",
    "exact_match": "true",
    "source_name": "linuxtoys",
    "version": version,
})
try:
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
except Exception:
    print("error")
    raise SystemExit(0)
if int(data.get("total_size", 0)) < 1:
    print("absent")
else:
    print((data.get("entries") or [{}])[0].get("status", "unknown"))
LPPY
}

# Launchpad-side duplicate guard. dput "Successfully uploaded packages" only
# means the transfer landed in the Launchpad incoming queue; duplicate
# sources and signature problems are checked asynchronously afterwards, so a
# failed upload would go unnoticed from here. Query the API instead:
#  * test runs probe versions that are ALREADY on the PPA (their re-upload
#    gets rejected asynchronously, harmless); an unknown version would be
#    queued and PUBLISHED live, which a test must never do.
#  * release runs refuse to proceed at all when the version already exists
#    on the PPA (the upload would be rejected and wasted).
ppa_state="$(ppa_check_state "$LT_VERSION-1")"
if [ "$ppa_state" != "error" ]; then
    if [ "$PPA_TEST_MODE" = "1" ] && [ "$ppa_state" = "absent" ]; then
        echo "::warning::Test run: linuxtoys $LT_VERSION-1 is not on the PPA yet. Skipping the dput probe - uploading a version Launchpad does not know would be queued and PUBLISHED to the PPA."
        export LINUXTOYS_PPA_UPLOAD_SKIP=1
    elif [ "$PPA_TEST_MODE" != "1" ] && [ "$ppa_state" != "absent" ]; then
        echo "::error::Launchpad PPA already contains linuxtoys $LT_VERSION-1 (status: $ppa_state). Duplicate sources are rejected by Launchpad; bump the version before releasing." >&2
        exit 1
    fi
else
    _msg warning "Could not query the Launchpad API - the duplicate-version guard is disabled for this run."
fi

# build and upload for PPA first - doesn't work if done after building the package
(
    cd "$OUTPUT_PATH/linuxtoys-$LT_VERSION" || exit 1
    if [ -n "${LINUXTOYS_PPA_UPLOAD_SKIP:-}" ]; then
        debuild -S -sa -us -uc
        sleep 1
    elif [ "$PPA_TEST_MODE" = "1" ]; then
        if [ "${LINUXTOYS_SKIP_PPA_UPLOAD:-0}" = "1" ]; then
            debuild -S -sa -us -uc
            sleep 1
            ppa_test_upload
            sleep 1
        else
            debuild -S -sa -kpsygreg@icloud.com
            sleep 1
            ppa_test_upload
            sleep 1
        fi
    else
        debuild -S -sa -kpsygreg@icloud.com
        sleep 1
        dput ppa:psygreg/linuxtoys "../linuxtoys_$LT_VERSION-1_source.changes"
        sleep 1
    fi
    # build package
    debuild -us -uc # this builder script requires devscripts!!
)

# Clean up build artifacts but keep the final package
rm -rf "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig/" "$OUTPUT_PATH/linuxtoys_$LT_VERSION.orig.tar.xz" "$OUTPUT_PATH/linuxtoys-$LT_VERSION/"
echo "All done" && sleep 3 && exit 0
