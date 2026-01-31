#!/bin/bash
# Nuitka build script for LinuxToys
# Usage: build.sh <version> <output_path>
# Example: build.sh 1.1 /tmp/builds

set -e
# Source utils.lib
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
VENV_PATH="$ROOT_DIR/dev/build/nuitka/.venv"

setup_venv() {
    local req_path="$ROOT_DIR/p3/requirements.txt"

    _msg info "Checking Python Virtual Environment..."

    # Check if we are already in a venv
    if [[ -n "$VIRTUAL_ENV" ]]; then
        _msg warning "Active Virtual Environment detected: $VIRTUAL_ENV"
        _msg info "Exiting and removing old environment..."

        # Deactivate if possible (though in script it might not affect parent, but good practice if sourced)
        deactivate 2>/dev/null || true

        # Remove the specific venv path as requested
        if [[ -d "$VENV_PATH" ]]; then
            rm -rf "$VENV_PATH"
            _msg info "Removed $VENV_PATH"
        fi

        # Unset VIRTUAL_ENV to ensure we start fresh
        unset VIRTUAL_ENV
    fi

    # Check if venv exists, if not create it
    if [[ -d "$VENV_PATH" ]]; then
        _msg info "Removing old Virtual Environment at $VENV_PATH"
        rm -rf "$VENV_PATH"
    fi

    local python_cmd=""
    # Detect Python version starting from 3.13 down to 3.6
    for ver in 13 12 11 10 9 8 7 6; do
        if command -v "python3.$ver" &>/dev/null; then
            python_cmd="python3.$ver"
            _msg info "Found Python version: $python_cmd"
            break
        fi
    done

    if [[ -z "$python_cmd" ]]; then
        if command -v python3 &>/dev/null; then
            python_cmd="python3"
            _msg error "Specific Python version (3.6-3.13) not found! for secure build, please install one of these versions."
            return 1
        fi
    fi

    _msg info "Creating new Virtual Environment at $VENV_PATH using $python_cmd..."
    $python_cmd -m venv "$VENV_PATH" || {
        _msg error "Failed to create venv"
        return 1
    }

    _msg info "Activating Virtual Environment..."
    source "$VENV_PATH/bin/activate" || {
        _msg error "Failed to activate venv"
        return 1
    }

    # Install dependencies
    _msg info "Ensuring dependencies are installed..."

    if [[ -f "$req_path" ]]; then
        pip install --quiet --upgrade pip
        pip install --quiet -r "$req_path" || {
            _msg error "Failed to install requirements"
            return 1
        }
    else
        _msg warning "Requirements file not found at $req_path"
    fi

    # Ensure Nuitka is installed
    if ! command -v nuitka &>/dev/null; then
        _msg info "Installing Nuitka..."
        pip install --quiet nuitka || {
            _msg error "Failed to install Nuitka"
            return 1
        }
    fi

    _msg info "Environment is ready."
}

setup_venv || exit 1

# Nuitka binary path
NUITKA=$(command -v nuitka)

rm -rf "$OUTPUT_PATH"
mkdir -p "$OUTPUT_PATH"

_msg info "Compiling LinuxToys version $LT_VERSION with Nuitka..."
_msg info "Output path: $OUTPUT_PATH"

$NUITKA --onefile --follow-imports --output-dir="$OUTPUT_PATH" \
    --include-package=requests \
    --include-data-dir="$ROOT_DIR/p3/app/icons=app/icons" \
    --include-data-dir="$ROOT_DIR/p3/helpers=helpers" \
    --include-data-dir="$ROOT_DIR/p3/libs=libs" \
    --include-data-dir="$ROOT_DIR/p3/scripts=scripts" \
    --include-data-file="$ROOT_DIR/p3/LICENSE=LICENSE" \
    --include-data-file="$ROOT_DIR/p3/app/style.css=app/style.css" \
    --include-data-file="$ROOT_DIR/p3/manifest.txt=manifest.txt" \
    --include-data-file="$ROOT_DIR/p3/update_version.py=update_version.py" \
    --enable-plugin=gi \
    --enable-plugin=no-qt \
    "$ROOT_DIR/p3/run.py"

if [ $? -eq 0 ]; then
    _msg info "Nuitka build successful! Artifacts are in $OUTPUT_PATH"
    _msg info "Deleting venv..."
    rm -rf "$VENV_PATH"
else
    _msg error "Nuitka build failed."
    exit 1
fi
