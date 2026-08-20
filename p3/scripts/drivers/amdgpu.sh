#!/bin/bash
# name: AMD GPU Driver
# version: 1.0
# description: amdgpu_desc
# icon: amd.png
# reboot: yes
# gpu: AMD
# compat: ubuntu, rhel
 
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_

secureboot_check

BASE="https://repo.radeon.com/amdgpu-install"
prep_tmp_noram
OUTDIR="${1:-./amdgpu-install-downloads}"
mkdir -p "$OUTDIR" 

list_dir() {
    local url="$1"
    curl -fsSL "$url" | grep -oP '(?<=href=")[^"?]+(?=")' | grep -v '^\.\./\?$' || true
}
latest_version_dir() {
    sed 's#/$##' | sort -V | tail -1
}

echo "Querying $BASE/ for available release versions..."
VERSION_DIRS=$(list_dir "$BASE/" | grep -E '^[0-9]+\.[0-9]+/$' || true)
if [ -z "$VERSION_DIRS" ]; then
    echo "AMD may have changed the page structure — FIXME $BASE/"
    die "Could not parse version directories from $BASE/"
fi
LATEST_VERSION=$(echo "$VERSION_DIRS" | latest_version_dir)
echo "Latest amdgpu-install version: $LATEST_VERSION"
 
find_latest_point() {
    local parent_url="$1"
    local major="$2"
    list_dir "$parent_url/" \
        | grep -E "^${major}\.[0-9]+/$" \
        | latest_version_dir
}
download_file() {
    local url="$1"
    local dest="$OUTDIR/$(basename "$url")"
    echo "Downloading: $url"
    if curl -fsSL -o "$dest" "$url"; then
        echo "  -> saved to $dest"
    else
        die "  Failed to download $url"
    fi
}
 
# RHEL
if is_rhel; then
    MAJOR="$(rpm -E %rhel)"
    if [ "$MAJOR" != "9" ] && [ "$MAJOR" != "10" ]; then
        die "$incompatmsg"
    fi
    RHEL_BASE="$BASE/$LATEST_VERSION/rhel"
    POINT=$(find_latest_point "$RHEL_BASE" "$MAJOR" || true)
    if [ -z "$POINT" ]; then
        die "No RHEL $MAJOR.x directory found under $RHEL_BASE/"
    fi
    DIR_URL="$RHEL_BASE/$POINT"
    echo "RHEL $MAJOR -> using $POINT"
    RPM=$(list_dir "$DIR_URL/" | grep -E '^amdgpu-install-.*\.rpm$' | latest_version_dir || true)
    if [ -z "$RPM" ]; then
        die "No .rpm found in $DIR_URL/"
    fi
    download_file "$DIR_URL/$RPM"
    askpass
    pkg_fromfile "./$OUTDIR/$RPM"
fi
 
# Ubuntu
if is_ubuntu; then
    if [ -z "$UBUNTU_CODENAME" ]; then
        die "Could not determine Ubuntu codename"
    fi
    case "$UBUNTU_CODENAME" in
        noble|resolute)
            CODENAME="$UBUNTU_CODENAME"
            ;;
        *)
            die "$incompatmsg"
            ;;
    esac
    DIR_URL="$BASE/$LATEST_VERSION/ubuntu/$CODENAME"
    echo "Ubuntu codename $CODENAME -> checking $DIR_URL/"
    DEB=$(
        list_dir "$DIR_URL/" |
            grep -E '^amdgpu-install_.*_all\.deb$' |
            latest_version_dir ||
            true
    )
    if [ -z "$DEB" ]; then
        die "No .deb found in $DIR_URL/"
    fi
    download_file "$DIR_URL/$DEB"
    askpass
    pkg_fromfile "./$OUTDIR/$DEB"
fi

sudo amdgpu-install -y
_append_transmap "exec amdgpu-install"
info "$rebootmsg"