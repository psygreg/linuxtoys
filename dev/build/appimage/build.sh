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
DESKTOP_FILE="$BUILD_DIR/toys.linux.LinuxToys.desktop"
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

# Bundle the symbolic icon themes the UI uses so the AppImage renders status
# icons on hosts that ship neither package. XSI is theme-independent (hicolor);
# the Adwaita set covers the remaining names and hosts where XSI is absent. Only
# the symbolic/xsi SVGs are copied (not whole themes) to keep the bundle small.
# The launcher prepends the bundled icons/parent to XDG_DATA_DIRS at runtime.
bundle_icon_themes() {
    local bundled=0

    # XSI ships as xsi-*.svg inside the hicolor theme. Rebuild just those into a
    # minimal hicolor theme so Gtk.IconTheme falls back to it.
    if [ -d /usr/share/icons/hicolor ]; then
        local xsi_count=0
        local src_rel dst
        mkdir -p "$APPDIR/share/icons/hicolor"
        while IFS= read -r src_rel; do
            [ -n "$src_rel" ] || continue
            dst="$APPDIR/share/icons/hicolor/$src_rel"
            mkdir -p "$(dirname "$dst")"
            cp -a "/usr/share/icons/hicolor/$src_rel" "$dst"
            xsi_count=$((xsi_count + 1))
        done < <(cd /usr/share/icons/hicolor && find . -type f -name 'xsi-*.svg' -printf '%P\n' 2>/dev/null)
        if [ "$xsi_count" -gt 0 ]; then
            _msg info "Bundled $xsi_count XSI symbolic icons into hicolor."
            bundled=$((bundled + 1))
        fi
    fi

    # The Adwaita symbolic set (emblem-ok-symbolic et al.) covers the original
    # Adwaita names and hosts where XSI is not installed.
    for theme_dir in /usr/share/icons/Adwaita /usr/share/icons/AdwaitaLegacy; do
        if [ -d "$theme_dir/symbolic" ]; then
            mkdir -p "$APPDIR/share/icons/$(basename "$theme_dir")"
            cp -a "$theme_dir/symbolic" "$APPDIR/share/icons/$(basename "$theme_dir")/"
            [ -f "$theme_dir/index.theme" ] && cp -a "$theme_dir/index.theme" "$APPDIR/share/icons/$(basename "$theme_dir")/"
            _msg info "Bundled Adwaita symbolic icons from $theme_dir."
            bundled=$((bundled + 1))
            break
        fi
    done

    if [ "$bundled" -eq 0 ]; then
        _msg error "No symbolic icon theme (xapp-symbolic-icons or adwaita-icon-theme) found on the build host. The AppImage would show missing status icons."
        exit 1
    fi

    # Ensure the hicolor fallback theme index exists so Gtk.IconTheme has a base
    # to inherit from even on minimal hosts.
    if [ ! -e "$APPDIR/share/icons/hicolor/index.theme" ] && [ -f /usr/share/icons/hicolor/index.theme ]; then
        mkdir -p "$APPDIR/share/icons/hicolor"
        cp -a /usr/share/icons/hicolor/index.theme "$APPDIR/share/icons/hicolor/"
    fi
}

build_linuxtoys_rust() {
    if ! command -v cargo >/dev/null 2>&1; then
        _msg error "cargo is required to build the LinuxToys Rust components."
        exit 1
    fi
    if ! command -v maturin >/dev/null 2>&1; then
        _msg error "maturin is required to build the LinuxToys Rust catalog extension."
        exit 1
    fi
    if ! command -v pkg-config >/dev/null 2>&1; then
        _msg error "pkg-config is required to build the LinuxToys native GTK library."
        exit 1
    fi
    if ! pkg-config --exists gtk+-3.0; then
        _msg error "GTK3 development files are required to build the LinuxToys native GTK library."
        exit 1
    fi

    _msg info "Building LinuxToys Rust catalog extension and native GTK library..."
    rm -rf \
        "$BUILD_DIR/linuxtoys-catalog-wheel" \
        "$ROOT_DIR/target/wheels/catalog"
    mkdir -p "$ROOT_DIR/target/wheels/catalog"

    (
        cd "$ROOT_DIR/src/catalog-rs"
        maturin build --release --locked --out "$ROOT_DIR/target/wheels/catalog"
    )
    cargo build --release --locked --manifest-path "$ROOT_DIR/src/gui-rs/Cargo.toml"

    local catalog_wheel catalog_extension gui_library
    catalog_wheel="$(find "$ROOT_DIR/target/wheels/catalog" -maxdepth 1 -type f -name '*.whl' -print -quit)"
    [[ -n "$catalog_wheel" ]] || {
        _msg error "maturin did not produce the LinuxToys catalog wheel."
        exit 1
    }

    mkdir -p "$BUILD_DIR/linuxtoys-catalog-wheel"
    python3 -m zipfile -e "$catalog_wheel" "$BUILD_DIR/linuxtoys-catalog-wheel"

    catalog_extension="$(find "$BUILD_DIR/linuxtoys-catalog-wheel" -type f -name '_catalog_rs*.so' -print -quit)"
    gui_library="$ROOT_DIR/target/release/liblinuxtoys_gui.so"
    [[ -n "$catalog_extension" && -f "$gui_library" ]] || {
        _msg error "LinuxToys Rust build artifacts were not produced."
        exit 1
    }

    install -Dm755 "$catalog_extension" "$APP_BIN/app/$(basename "$catalog_extension")"
    install -Dm755 "$gui_library" "$APP_BIN/app/liblinuxtoys_gui.so"
}

# The TUI (p3/app/tui) is built on Textual and renders its embedded terminal
# with pyte. These dependencies ship in-tree under p3/vendor, pinned in
# p3/requirements.txt, so no native packages are required on the build host.
# Verify the vendored stack early, before spending time on any heavy build.
verify_python_tui_deps() {
    local vendor_dir="$ROOT_DIR/p3/vendor"
    local probe
    if ! probe="$(PYTHONPATH="$vendor_dir" python3 -c 'import textual.app, pyte, rich; from importlib.metadata import version; t = version("textual"); p = version("pyte"); print(f"textual {t}, pyte {p}")' 2>&1)"; then
        _msg error "The vendored TUI stack in p3/vendor failed to import:"
        _msg error "$probe"
        _msg error "Materialize it from the pinned requirements and rebuild:"
        _msg error "  ./build-rust.sh vendor"
        exit 1
    fi
    _msg info "Vendored TUI stack OK ($probe)."
}

# The vendored TUI stack must survive the copy into the AppDir and import
# cleanly from its final location before the AppImage is generated.
verify_bundled_python_tui_deps() {
    local probe
    if ! probe="$(PYTHONPATH="$APP_BIN/vendor" python3 -c 'import textual.app, pyte, rich' 2>&1)"; then
        _msg error "The vendored TUI stack failed to import from the AppDir:"
        _msg error "$probe"
        _msg error "Materialize p3/vendor with './build-rust.sh vendor' and rebuild."
        exit 1
    fi
    _msg info "Vendored TUI stack present in the AppDir."
}

# DEPLOY_PYTHON makes quick-sharun copy the build host's /usr/lib/python3.x
# (site-packages included) into the AppDir, so the AppImage's Python
# environment is exactly what the build host has installed. The app needs two
# third-party runtime packages from it: PyGObject (gi) for the GUI and
# requests for the network layer (bug reporting, about/contributors fetch,
# translation endpoints). The deb/rpm/arch packages declare both as distro
# dependencies; the AppImage has no such mechanism, so they must be installed
# on the build host. Verify early, before spending time on any heavy build.
verify_host_python_runtime_deps() {
    local python_bin probe
    # Mirror the interpreter quick-sharun deploys (command -v python, else
    # python3): whatever it picks is what lands in the AppImage.
    python_bin="$(command -v python || command -v python3)" || {
        _msg error "No python interpreter found on the build host."
        exit 1
    }
    if ! probe="$("$python_bin" -c 'import requests, gi; from gi.repository import Gio' 2>&1)"; then
        _msg error "The build host's Python ($python_bin) is missing the app's runtime dependencies:"
        _msg error "$probe"
        _msg error "The AppImage bundles this host's Python site-packages, so the following"
        _msg error "packages must be installed here before building:"
        _msg error "  - python-requests (TUI and network layer)"
        _msg error "  - python-gobject  (PyGObject bindings for the GUI)"
        _msg error "Install them (Arch: pacman -S python-requests python-gobject) and rebuild."
        exit 1
    fi
    _msg info "Host Python runtime dependencies OK (requests, PyGObject)."
}

# Verify the Python tree quick-sharun actually deployed into the AppDir:
# site-packages must contain the runtime dependencies the app imports. This
# catches behavior changes in quick-sharun's python deployment before the
# AppImage is generated, instead of shipping an AppImage that fails with
# "No module named 'requests'" (TUI) or "No module named 'gi.repository'" (GUI).
verify_deployed_python_runtime_deps() {
    local python_dir missing=0
    python_dir="$(find "$APPDIR/lib" -maxdepth 1 -type d -name 'python3*' -print -quit)"
    [[ -n "$python_dir" ]] || {
        _msg error "quick-sharun did not deploy a Python tree into the AppDir."
        exit 1
    }
    [[ -f "$python_dir/site-packages/requests/__init__.py" ]] || {
        _msg error "Deployed Python tree is missing the 'requests' package:"
        _msg error "$python_dir/site-packages"
        missing=1
    }
    [[ -f "$python_dir/site-packages/gi/repository/__init__.py" ]] || {
        _msg error "Deployed Python tree is missing PyGObject (gi.repository):"
        _msg error "$python_dir/site-packages"
        missing=1
    }
    [[ "$missing" -eq 0 ]] || {
        _msg error "The AppImage bundles the build host's Python environment; install"
        _msg error "python-requests and python-gobject on the build host and rebuild."
        exit 1
    }
    _msg info "Deployed Python runtime dependencies present in the AppDir."
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

verify_python_tui_deps
verify_host_python_runtime_deps

build_glycin_ng

# Build directly from the official source tree. This replaces pkgforge's
# linuxtoys-bin AUR install + /usr/share/linuxtoys copy step.
cp -a "$ROOT_DIR/p3/." "$APP_BIN/"
# Make bundled Python modules and assets accessible regardless of source modes.
find "$APP_BIN" -type d -exec chmod 755 {} +
find "$APP_BIN" -type f -exec chmod a+r {} +
bundle_icon_themes
build_linuxtoys_rust
find "$APP_BIN" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$APP_BIN" -type f -name '*.pyc' -delete 2>/dev/null || true
[[ -f "$APP_BIN/app/_catalog_rs.abi3.so" ]] || { _msg error "Rust catalog extension missing from AppDir."; exit 1; }
[[ -f "$APP_BIN/app/liblinuxtoys_gui.so" ]] || { _msg error "Rust native GTK library missing from AppDir."; exit 1; }
verify_bundled_python_tui_deps

# LinuxToys entry point, mirroring the /usr/bin/linuxtoys launcher the distro
# packages ship: cd into the app tree, pick CLI mode from the arguments and
# hand over to linuxtoys.py. sharun remains the AppRun (quick-sharun generates
# AppRun.sh itself), so this script must not carry AppImage runtime bootstrapping:
# - GI_TYPELIB_PATH and the XDG data dirs of the bundled icons are provided by
#   sharun at launch ($APPDIR/lib/girepository-* and $APPDIR/share when it
#   exists),
# - the static LINUXTOYS_* env vars are applied through $APPDIR/.env instead
#   (see the block right before --make-appimage).
# Per the quick-sharun maintainer in
# https://github.com/psygreg/linuxtoys/issues/1358.
cat > "$APP_BIN/linuxtoys" <<'LAUNCHER'
#!/bin/sh
cd "${APPDIR:?}/bin"

# CLI mode if arguments are provided; a linuxtoys:// URI always opens the GUI.
if [ "$#" -eq 1 ]; then
    case "$1" in
        linuxtoys://*) unset EASY_CLI ;;
        *) export EASY_CLI=1 ;;
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

# Work on a build-local copy: never alter src/toys.linux.LinuxToys.desktop in the tree.
# No Exec= patching is needed: quick-sharun derives the main binary by taking
# the basename of the desktop file's Exec= value (stripping the /usr/bin/
# prefix), and desktop-integration tools rewrite Exec= to point at the
# integrated AppImage. Same recipe as the pkgforge-dev/LinuxToys-AppImage
# build (see https://github.com/psygreg/linuxtoys/issues/1358).
cp "$ROOT_DIR/src/toys.linux.LinuxToys.desktop" "$DESKTOP_FILE"

export ARCH="$(uname -m)"
export VERSION="$LT_VERSION"
# Pin the artifact filename instead of renaming what quick-sharun produced:
# appimagetool auto-detects the name from the desktop entry and tags it
# "anylinux" otherwise. This value is what the release workflow collects.
export OUTNAME="LinuxToys-$LT_VERSION-$ARCH.AppImage"
export OUTPATH="$OUTPUT_PATH"
export DESKTOP="$DESKTOP_FILE"
export ICON="$ROOT_DIR/src/linuxtoys.svg"
install -Dm644 "$ROOT_DIR/src/toys.linux.LinuxToys.metainfo.xml" "$APPDIR/share/metainfo/toys.linux.LinuxToys.metainfo.xml"
export DEPLOY_PYTHON=1
export ANYLINUX_LIB=1

# Ship zero GPU drivers: they are loaded from the host at runtime through
# cross-libc-dlopen instead. LinuxToys is a GTK3 app that does not depend on a
# recent OpenGL nor has a hard Vulkan dependency, so it meets the criteria
# documented in quick-sharun for this mode. This keeps mesa's libgallium (and
# with it the 163 MiB libLLVM.so.22 it drags in) out of the bundle; shipping
# mesa that links to LLVM is also about to become a hard error in quick-sharun
# (pkgforge-dev/Anylinux-AppImages#1033). Suggested by the quick-sharun
# maintainer in https://github.com/psygreg/linuxtoys/issues/1358.
export USE_HOST_DRIVERS_EXPERIMENTAL=1

# LinuxToys now has its own background updater. Do not add pkgforge's generic
# self-updater hook to the official build, otherwise users would get two
# independent update mechanisms.
unset ADD_HOOKS || true
unset UPINFO || true

# Deploy the entry point into bin/, the GTK3 zenity helper used by LinuxToys,
# jq, required by scripts/sysup.sh (Fedora release upgrades) and the
# OpenLinkHub peripheral helper for JSON parsing. Sharun itself becomes the
# AppRun (added by quick-sharun). This follows pkgforge's proven LinuxToys
# recipe, but against our source-built AppDir rather than the AUR package.
WEBP_PIXBUF_LOADER="$(
    find /usr/lib/gdk-pixbuf-2.0 -type f \
        -name 'libpixbufloader-webp.so' \
        -print -quit
)"
[ -n "$WEBP_PIXBUF_LOADER" ] || {
    echo "Error: WebP GdkPixbuf loader not found."
    exit 1
}

(
    cd "$BUILD_DIR"
    "$QUICK_SHARUN" \
        "$APP_BIN/linuxtoys" \
        /usr/bin/zenity \
        /usr/bin/jq \
        /usr/bin/script \
        /usr/lib/libappstream.so.5 \
        "$WEBP_PIXBUF_LOADER"
)

# The AppStream typelib needs no manual bundling: with DEPLOY_PYTHON and the
# detected GTK, quick-sharun deploys libgirepository and then copies the whole
# girepository typelib directory (AppStream included) automatically.
replace_upstream_glycin

# The Python tree (stdlib + site-packages) is now deployed in the AppDir;
# verify the runtime dependencies survived the copy before generating the
# AppImage.
verify_deployed_python_runtime_deps

# Runtime env vars for the AppImage, written into the AppDir .env file sharun
# reads at launch ("env variables can be added to a .env file in the AppDir",
# per the quick-sharun maintainer in
# https://github.com/psygreg/linuxtoys/issues/1358). Unquoted values are
# expanded by sharun, so $APPDIR resolves to the mounted AppDir at runtime.
# These are AppImage-only context: the distro packages never set them.
cat >> "$APPDIR/.env" <<'ENV'
LINUXTOYS_PROCESS_NAME=linuxtoys
LINUXTOYS_APPIMAGE=1
LINUXTOYS_APPIMAGE_DIR=$APPDIR
ENV

(
    cd "$BUILD_DIR"
    "$QUICK_SHARUN" --make-appimage
)

# OUTNAME pinned the artifact filename, exactly the path the release workflow
# collects. Fail loudly against upstream naming changes instead of shipping a
# misnamed artifact.
FINAL_APPIMAGE="$OUTPUT_PATH/LinuxToys-$LT_VERSION-$ARCH.AppImage"
if [[ ! -f "$FINAL_APPIMAGE" ]]; then
    _msg error "Expected AppImage was not produced: $FINAL_APPIMAGE"
    ls -la "$OUTPUT_PATH" >&2 || true
    exit 1
fi
chmod +x "$FINAL_APPIMAGE"

_msg info "Running AppImage smoke test..."
"$QUICK_SHARUN" --simple-test "$FINAL_APPIMAGE"

cleanup_quick_sharun
rm -rf "$BUILD_DIR"
_msg info "AppImage created: $FINAL_APPIMAGE"
