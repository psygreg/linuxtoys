#!/bin/bash
# AppImage build script for LinuxToys
# Usage: build-appimage.sh <version> <output_path>
# Example: build-appimage.sh 6.7.1 /tmp/builds
#
# This reuses the pkgforge quick-sharun approach while building directly from
# the official LinuxToys source tree instead of installing linuxtoys-bin.

set -euo pipefail

ROOT_DIR="$PWD"
while [[ "${ROOT_DIR##*/}" != "linuxtoys" && "$ROOT_DIR" != "/" ]]; do
    ROOT_DIR="${ROOT_DIR%/*}"
done

if [[ "$ROOT_DIR" == "/" ]]; then
    echo "Error: run this script from inside the LinuxToys source tree." >&2
    exit 1
fi

# Keep the same messaging helper used by the other official builders when it
# is available, but remain usable in stripped-down AppImage build containers.
if [[ -f "$ROOT_DIR/dev/libs/utils.lib" ]]; then
    # shellcheck source=/dev/null
    source "$ROOT_DIR/dev/libs/utils.lib"
else
    _msg() { printf '%s\n' "$2"; }
fi

if [[ $# -ne 2 ]]; then
    _msg error "Usage: $0 <version> <output_path>"
    _msg info "Example: $0 6.7.1 /tmp/builds"
    exit 1
fi

LT_VERSION="$1"
OUTPUT_PATH="$(realpath -m "$2")"
BUILD_DIR="$OUTPUT_PATH/appimage-build"
APPDIR="$BUILD_DIR/AppDir"
APP_BIN="$APPDIR/bin"
DESKTOP_FILE="$BUILD_DIR/LinuxToys.desktop"
QUICK_SHARUN="$BUILD_DIR/quick-sharun"
QUICK_SHARUN_URL="https://raw.githubusercontent.com/pkgforge-dev/Anylinux-AppImages/main/useful-tools/quick-sharun.sh"
GLYCIN_NG_REPO="https://github.com/QaidVoid/glycin-ng.git"
GLYCIN_NG_REF="${GLYCIN_NG_REF:-main}"
GLYCIN_NG_SRC="$BUILD_DIR/glycin-ng"


cleanup_quick_sharun() {
    rm -f "$QUICK_SHARUN"
}
trap cleanup_quick_sharun EXIT

build_glycin_ng() {
    if ! command -v git >/dev/null 2>&1; then
        _msg error "git is required to fetch glycin-ng."
        exit 1
    fi
    if ! command -v cargo >/dev/null 2>&1; then
        _msg error "cargo is required to build glycin-ng."
        exit 1
    fi

    _msg info "Fetching glycin-ng ($GLYCIN_NG_REF)..."
    rm -rf "$GLYCIN_NG_SRC"
    git clone --quiet --depth 1 --branch "$GLYCIN_NG_REF" \
        "$GLYCIN_NG_REPO" "$GLYCIN_NG_SRC" 2>/dev/null || {
        # GLYCIN_NG_REF may be a commit rather than a branch/tag.
        git clone --quiet --depth 1 "$GLYCIN_NG_REPO" "$GLYCIN_NG_SRC"
        (
            cd "$GLYCIN_NG_SRC"
            git fetch --quiet --depth 1 origin "$GLYCIN_NG_REF"
            git checkout --quiet FETCH_HEAD
        )
    }

    _msg info "Building glycin-ng and libglycin compatibility shim..."
    (
        cd "$GLYCIN_NG_SRC"
        cargo build --release -p glycin-ng-c
        GLYCIN_NG_LIB_DIR="$GLYCIN_NG_SRC/target/release" \
            cargo build --release -p glycin-ng-libglycin-shim
    )

    [[ -f "$GLYCIN_NG_SRC/target/release/libglycin_ng.so" ]] || {
        _msg error "glycin-ng build did not produce libglycin_ng.so."
        exit 1
    }
    [[ -f "$GLYCIN_NG_SRC/target/release/libglycin_2.so" ]] || {
        _msg error "glycin-ng shim build did not produce libglycin_2.so."
        exit 1
    }
}

replace_upstream_glycin() {
    _msg info "Replacing upstream Glycin deployment with glycin-ng..."

    # Remove upstream Glycin's client library, loader configuration and helper
    # executables that quick-sharun may have pulled in through gdk-pixbuf.
    find "$APPDIR/lib" -maxdepth 1 \
        \( -name 'libglycin-*.so*' -o -name 'libglycin.so*' \) \
        -delete 2>/dev/null || true

    rm -rf \
        "$APPDIR/share/glycin-loaders" \
        "$APPDIR/share/glycin" \
        "$APPDIR/libexec/glycin" \
        "$APPDIR/lib/glycin" 2>/dev/null || true

    if [[ -d "$APPDIR/shared/bin" ]]; then
        find "$APPDIR/shared/bin" -maxdepth 1 -type f \
            \( -name 'glycin-*' -o -name 'glycin_*' \) \
            -delete 2>/dev/null || true
    fi
    if [[ -d "$APPDIR/bin" ]]; then
        find "$APPDIR/bin" -maxdepth 1 -type f \
            \( -name 'glycin-*' -o -name 'glycin_*' \) \
            -delete 2>/dev/null || true
    fi

    # Arch gdk-pixbuf2 links against libglycin-2.so.0. glycin-ng provides a
    # compatibility shim with that SONAME which forwards to libglycin_ng.so.
    install -Dm755 \
        "$GLYCIN_NG_SRC/target/release/libglycin_ng.so" \
        "$APPDIR/lib/libglycin_ng.so"
    install -Dm755 \
        "$GLYCIN_NG_SRC/target/release/libglycin_2.so" \
        "$APPDIR/lib/libglycin-2.so.0"
    ln -sfn libglycin-2.so.0 "$APPDIR/lib/libglycin-2.so"

    # Verify the replacement before creating the AppImage.
    if ! readelf -d "$APPDIR/lib/libglycin-2.so.0" 2>/dev/null \
        | grep -q 'SONAME.*libglycin-2\.so\.0'; then
        _msg error "glycin-ng compatibility shim has an unexpected SONAME."
        exit 1
    fi

    if find "$APPDIR/shared/bin" "$APPDIR/bin" \
        -maxdepth 1 -type f \( -name 'glycin-*' -o -name 'glycin_*' \) \
        -print -quit 2>/dev/null | grep -q .; then
        _msg error "Upstream Glycin helper binaries remain in AppDir."
        exit 1
    fi

    _msg info "glycin-ng replacement installed successfully."
}

_msg info "Building LinuxToys $LT_VERSION AppImage..."
_msg info "Output path: $OUTPUT_PATH"

rm -rf "$BUILD_DIR"
mkdir -p "$APP_BIN" "$OUTPUT_PATH"

# Bootstrap quick-sharun for this build only. Keep it inside the temporary
# build directory and remove it automatically on both success and failure.
_msg info "Fetching quick-sharun..."
if command -v curl >/dev/null 2>&1; then
    curl -fL --retry 3 --retry-delay 2 "$QUICK_SHARUN_URL" -o "$QUICK_SHARUN"
elif command -v wget >/dev/null 2>&1; then
    wget -O "$QUICK_SHARUN" "$QUICK_SHARUN_URL"
else
    _msg error "Neither curl nor wget is available to fetch quick-sharun."
    exit 1
fi
chmod +x "$QUICK_SHARUN"

build_glycin_ng

# Build directly from the official source tree. This replaces pkgforge's
# linuxtoys-bin AUR install + /usr/share/linuxtoys copy step.
cp -a "$ROOT_DIR/p3/." "$APP_BIN/"
find "$APP_BIN" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$APP_BIN" -type f -name '*.pyc' -delete 2>/dev/null || true

# LinuxToys launcher for the AppImage runtime. quick-sharun/uruntime provides
# APPDIR, so no host /usr/share/linuxtoys path is involved.
cat > "$APP_BIN/linuxtoys" <<'LAUNCHER'
#!/bin/sh
set -eu

cd "${APPDIR:?}/bin"
export LINUXTOYS_PROCESS_NAME=linuxtoys
export LINUXTOYS_APPIMAGE=1
export LINUXTOYS_APPIMAGE_DIR="$APPDIR"
export GI_TYPELIB_PATH="$APPDIR/lib/girepository-1.0${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"

if [ "$#" -eq 1 ]; then
    case "$1" in
        linuxtoys://*)
            unset EASY_CLI
            ;;
        *)
            export EASY_CLI=1
            ;;
    esac
elif [ "$#" -gt 0 ]; then
    export EASY_CLI=1
fi

exec python3 ./linuxtoys.py "$@"
LAUNCHER
chmod +x "$APP_BIN/linuxtoys"

# Preserve executable bits expected by LinuxToys.
find "$APP_BIN/scripts" -type f -name '*.sh' -exec chmod +x {} \; 2>/dev/null || true
find "$APP_BIN/helpers" -type f -name '*.sh' -exec chmod +x {} \; 2>/dev/null || true
chmod +x "$APP_BIN/linuxtoys.py"

# Work on a build-local copy: never alter src/LinuxToys.desktop in the tree.
cp "$ROOT_DIR/src/LinuxToys.desktop" "$DESKTOP_FILE"

# AppImage desktop integration launches the Exec target *inside* the AppImage.
# The packaged desktop file used by DEB/RPM installs intentionally points at
# /usr/bin/linuxtoys, so patch only this build-local copy. The replacement is
# idempotent whether the source already says /usr/bin/linuxtoys or linuxtoys.
if grep -q '^Exec=' "$DESKTOP_FILE"; then
    sed -i -E 's|^Exec=(/usr/bin/)?linuxtoys([[:space:]].*)?$|Exec=linuxtoys\2|' "$DESKTOP_FILE"
else
    printf '\nExec=linuxtoys %%u\n' >> "$DESKTOP_FILE"
fi

# Fail rather than silently emit an AppImage whose desktop integration would
# escape to a host-installed LinuxToys binary.
if ! grep -qE '^Exec=linuxtoys([[:space:]]|$)' "$DESKTOP_FILE"; then
    _msg error "Could not make the desktop Exec entry AppImage-safe:"
    grep '^Exec=' "$DESKTOP_FILE" >&2 || true
    exit 1
fi

export ARCH="$(uname -m)"
export VERSION="$LT_VERSION"
export OUTPATH="$OUTPUT_PATH"
export DESKTOP="$DESKTOP_FILE"
export ICON="$ROOT_DIR/src/linuxtoys.svg"
export DEPLOY_PYTHON=1
export ANYLINUX_LIB=1

# LinuxToys now has its own background updater. Do not add pkgforge's generic
# self-updater hook to the official build, otherwise users would get two
# independent update mechanisms.
unset ADD_HOOKS || true
unset UPINFO || true

# Deploy the launcher/runtime and the GTK3 zenity helper used by LinuxToys.
# This follows pkgforge's proven LinuxToys recipe, but against our source-built
# AppDir rather than the AUR package.
(
    cd "$BUILD_DIR"
    "$QUICK_SHARUN" \
        "$APP_BIN/linuxtoys" \
        /usr/bin/zenity \
        /usr/lib/libappstream.so.5
)

# AppStream is loaded dynamically through GObject Introspection, so its typelib
# is not discoverable from the ELF dependency graph followed by quick-sharun.
# Arch's appstream package supplies both files; bundle the typelib explicitly.
install -Dm644 \
    /usr/lib/girepository-1.0/AppStream-1.0.typelib \
    "$APPDIR/lib/girepository-1.0/AppStream-1.0.typelib"

replace_upstream_glycin

(
    cd "$BUILD_DIR"
    "$QUICK_SHARUN" --make-appimage
)

# quick-sharun names the artifact itself. Normalize it to an official,
# predictable filename while keeping any generated .zsync alongside it.
mapfile -t APPIMAGES < <(find "$OUTPUT_PATH" -maxdepth 1 -type f -name '*.AppImage' -print)
if [[ ${#APPIMAGES[@]} -ne 1 ]]; then
    _msg error "Expected exactly one AppImage in $OUTPUT_PATH, found ${#APPIMAGES[@]}."
    exit 1
fi

FINAL_APPIMAGE="$OUTPUT_PATH/LinuxToys-$LT_VERSION-$ARCH.AppImage"
if [[ "${APPIMAGES[0]}" != "$FINAL_APPIMAGE" ]]; then
    mv -f "${APPIMAGES[0]}" "$FINAL_APPIMAGE"
fi
chmod +x "$FINAL_APPIMAGE"

_msg info "Running AppImage smoke test..."
"$QUICK_SHARUN" --simple-test "$FINAL_APPIMAGE"

cleanup_quick_sharun
rm -rf "$BUILD_DIR"
_msg info "AppImage created: $FINAL_APPIMAGE"
