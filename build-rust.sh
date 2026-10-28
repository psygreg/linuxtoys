#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODE="release"
COMMAND="build"
OUT_DIR="${ROOT}/target/wheels"
TARGET=""

usage() {
    cat <<'EOF'
Usage:
      ./build-rust.sh [build|develop] [--debug] [--out DIR]
      ./build-rust.sh release VERSION
      ./build-rust.sh vendor

Commands:
  build       Build the catalog wheel and native GUI library (default).
  develop     Build both Rust components, deploy their libraries into p3/app
              and vendor the TUI dependencies for running from source.
  release     Build all packages except for Solus for release. The TUI
              dependencies are vendored into p3/vendor beforehand.
  vendor      Materialize the vendored TUI dependencies into p3/vendor
              (reads the pins from p3/requirements.txt).

Options:
  --debug     Build without --release.
  --out DIR   Build output directory (build only).
  -h, --help  Show this help.
EOF
}

if [[ $# -gt 0 && "$1" != -* ]]; then
    COMMAND="$1"
    shift
fi

if [[ "$COMMAND" == "release" ]]; then
    [[ $# -gt 0 && "$1" != -* ]] || {
        echo "error: release requires a version" >&2
        echo "usage: $0 release VERSION" >&2
        exit 2
    }
    TARGET="$1"
    shift
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug)
            MODE="debug"
            shift
            ;;
        --out)
            [[ $# -ge 2 ]] || {
                echo "error: --out requires a directory" >&2
                exit 2
            }
            OUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

case "$COMMAND" in
    build|develop|release|vendor) ;;
    *)
        echo "error: command must be 'build', 'develop', 'release' or 'vendor'" >&2
        usage >&2
        exit 2
        ;;
esac

# Vendoring needs no Rust toolchain, so handle it before those checks.
if [[ "$COMMAND" == "vendor" ]]; then
    exec "$ROOT/dev/build/vendor_deps.sh"
fi

command -v maturin >/dev/null 2>&1 || {
    echo "error: maturin was not found in PATH" >&2
    exit 127
}
command -v cargo >/dev/null 2>&1 || {
    echo "error: cargo was not found in PATH" >&2
    exit 127
}

COMMON=()
[[ "$MODE" == "release" ]] && COMMON+=(--release)

build_python_component() {
    local name="$1"
    local dir="$2"

    echo "==> ${COMMAND}: ${name}"

    if [[ "$COMMAND" != "develop" ]]; then
        mkdir -p "$OUT_DIR"
        (
            cd "$dir"
            maturin build "${COMMON[@]}" --out "$OUT_DIR"
        )
    else
        local wheel_dir="${ROOT}/target/develop-wheels/${name}"
        local extract_dir="${ROOT}/target/develop-extract/${name}"
        local module_path

        rm -rf "$wheel_dir" "$extract_dir"
        mkdir -p "$wheel_dir" "$extract_dir" "${ROOT}/p3/app"

        (
            cd "$dir"
            maturin build "${COMMON[@]}" --out "$wheel_dir"
        )

        local wheel
        wheel="$(find "$wheel_dir" -maxdepth 1 -type f -name '*.whl' -print -quit)"
        [[ -n "$wheel" ]] || {
            echo "error: no wheel produced for ${name}" >&2
            exit 1
        }

        python3 -m zipfile -e "$wheel" "$extract_dir"

        module_path="$(find "$extract_dir" -type f \
            \( -name "${name}.abi3.so" -o -name "${name}.*.so" -o -name "${name}.so" \) \
            -print -quit)"
        [[ -n "$module_path" ]] || {
            echo "error: ${name} extension not found in $(basename "$wheel")" >&2
            exit 1
        }

        # Remove stale variants so Python cannot accidentally load an older build.
        find "${ROOT}/p3/app" -maxdepth 1 -type f \
            \( -name "${name}.abi3.so" -o -name "${name}.*.so" -o -name "${name}.so" \) \
            -delete

        cp -f "$module_path" "${ROOT}/p3/app/$(basename "$module_path")"
        echo "    -> p3/app/$(basename "$module_path")"
    fi
}

build_gui_component() {
    local dir="${ROOT}/src/gui-rs"
    local profile_dir="debug"
    local cargo_args=(build --manifest-path "${dir}/Cargo.toml")

    [[ "$MODE" == "release" ]] && {
        cargo_args+=(--release)
        profile_dir="release"
    }

    echo "==> ${COMMAND}: linuxtoys_gui"
    cargo "${cargo_args[@]}"

    local library="${ROOT}/target/${profile_dir}/liblinuxtoys_gui.so"
    [[ -f "$library" ]] || {
        echo "error: native GUI library not found: ${library}" >&2
        exit 1
    }

    if [[ "$COMMAND" == "develop" ]]; then
        mkdir -p "${ROOT}/p3/app"
        rm -f "${ROOT}/p3/app/liblinuxtoys_gui.so"
        cp -f "$library" "${ROOT}/p3/app/liblinuxtoys_gui.so"
        echo "    -> p3/app/liblinuxtoys_gui.so"
    else
        mkdir -p "$OUT_DIR"
        cp -f "$library" "${OUT_DIR}/liblinuxtoys_gui.so"
        echo "    -> ${OUT_DIR}/liblinuxtoys_gui.so"
    fi
}

if [[ "$COMMAND" == "release" ]]; then
    # The container builds stage the source tree as-is, so materialize the
    # vendored TUI dependencies first; every package then ships them.
    "$ROOT/dev/build/vendor_deps.sh"

    COMMAND="build"
    build_python_component "_catalog_rs" "${ROOT}/src/catalog-rs"
    build_gui_component

    COMMAND="develop"
    build_python_component "_catalog_rs" "${ROOT}/src/catalog-rs"
    build_gui_component

    COMMAND="release"

    echo
    echo "Rust build artifacts written to: ${OUT_DIR}"
    echo "Rust libraries deployed into: ${ROOT}/p3/app"

    distrobox enter fedora -- bash -lc \
        'cd "$1/dev/build/copr" && ./build.sh "$2" "$HOME/copr"' _ "$ROOT" "$TARGET"
    distrobox enter archlinux -- bash -lc \
        'cd "$1/dev/build/pkg" && ./build.sh "$2" "$HOME/pkg"' _ "$ROOT" "$TARGET"
    distrobox enter archlinux -- bash -lc \
        'cd "$1/dev/build/appimage" && ./build.sh "$2" "$HOME/appimage"' _ "$ROOT" "$TARGET"
    distrobox enter ubuntu -- bash -lc \
        'cd "$1/dev/build/deb" && ./build.sh "$2" "$HOME/deb"' _ "$ROOT" "$TARGET"

    echo "All packages done."
else
    if [[ "$COMMAND" == "develop" ]]; then
        # The TUI must be runnable from source right after a develop run.
        "$ROOT/dev/build/vendor_deps.sh"
    fi

    build_python_component "_catalog_rs" "${ROOT}/src/catalog-rs"
    build_gui_component

    echo
    if [[ "$COMMAND" == "develop" ]]; then
        echo "Rust libraries deployed into: ${ROOT}/p3/app"
    else
        echo "Rust build artifacts written to: ${OUT_DIR}"
    fi
fi
