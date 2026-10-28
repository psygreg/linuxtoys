#!/bin/bash
# Vendor the TUI dependencies into p3/vendor for build and development runs.
#
# The TUI (p3/app/tui) needs Textual and pyte, which are not available as
# native packages on every distribution LinuxToys packages for. Instead of
# relying on them, the pinned dependencies are materialized in-tree into
# p3/vendor (gitignored) before a build. p3/linuxtoys.py inserts that
# directory ahead of site-packages, so the vendored stack always wins over
# whatever the host happens to have installed.
#
# Usage: dev/build/vendor_deps.sh
#
# The pins are read from p3/requirements.txt, which stays the single source
# of truth: bump the pins there, then re-run this script (or a build-rust.sh
# release/develop run) to refresh the vendor tree.

set -euo pipefail

ROOT_DIR="$PWD"
while [[ "${ROOT_DIR##*/}" != "linuxtoys" && "$ROOT_DIR" != "/" ]]; do
    ROOT_DIR="${ROOT_DIR%/*}"
done

if [[ "$ROOT_DIR" == "/" ]]; then
    echo "Error: run this script from inside the LinuxToys source tree." >&2
    exit 1
fi

if [[ -f "$ROOT_DIR/dev/libs/utils.lib" ]]; then
    # shellcheck source=/dev/null
    source "$ROOT_DIR/dev/libs/utils.lib"
else
    _msg() { printf '%s\n' "$2"; }
fi

VENDOR_DIR="$ROOT_DIR/p3/vendor"
REQUIREMENTS="$ROOT_DIR/p3/requirements.txt"

# wcwidth 0.9.x ships an x86_64-only C accelerator wheel; keep the vendored
# tree pure Python by capping it to the last source-only series.
WCWIDTH_CONSTRAINT="wcwidth<0.9"

[[ -f "$REQUIREMENTS" ]] || {
    _msg error "Requirements file not found: $REQUIREMENTS"
    exit 1
}

# Exact == pins only: the vendor tree must be reproducible.
mapfile -t PINS < <(grep -E '^(textual|pyte)==' "$REQUIREMENTS" || true)
if [[ ${#PINS[@]} -eq 0 ]]; then
    _msg error "No exact 'textual==x' / 'pyte==y' pins found in $REQUIREMENTS."
    _msg error "Vendoring requires exact versions to be pinned."
    exit 1
fi

if ! python3 -m pip --version >/dev/null 2>&1; then
    _msg error "pip is not available for the host python3."
    _msg error "Install it first (Arch: python-pip, Debian: python3-pip, Fedora: python3-pip)."
    exit 1
fi

# The vendored tree is reused when every pinned version already matches.
vendor_matches_pins() {
    local pin pkg expected installed
    for pin in "${PINS[@]}"; do
        pkg="${pin%%==*}"
        expected="${pin#*==}"
        installed="$(PYTHONPATH="$VENDOR_DIR" python3 -c \
            "from importlib.metadata import version; print(version('$pkg'))" 2>/dev/null)" || return 1
        [[ "$installed" == "$expected" ]] || return 1
    done
    return 0
}

if [[ -d "$VENDOR_DIR" ]] && vendor_matches_pins; then
    _msg info "Vendored TUI dependencies in p3/vendor already match the pins, skipping."
    exit 0
fi

_msg info "Vendoring TUI dependencies into p3/vendor..."
rm -rf "$VENDOR_DIR"
python3 -m pip install --quiet --target "$VENDOR_DIR" --no-compile \
    --no-warn-script-location "${PINS[@]}" "$WCWIDTH_CONSTRAINT"

# Console-script shims (pygmentize and friends) are dead weight here.
rm -rf "$VENDOR_DIR/bin"

# Guard against platform-specific wheels sneaking into the tree.
if find "$VENDOR_DIR" -type f \( -name '*.so' -o -name '*.so.*' -o -name '*.pyd' \) -print -quit | grep -q .; then
    _msg error "The vendored tree contains binary modules; refusing to continue."
    _msg error "Check the pins in $REQUIREMENTS and re-run this script."
    exit 1
fi

if ! probe="$(PYTHONPATH="$VENDOR_DIR" python3 -B -c 'import textual.app, pyte, rich; from importlib.metadata import version; t = version("textual"); p = version("pyte"); print(f"textual {t}, pyte {p}")' 2>&1)"; then
    _msg error "The vendored TUI stack failed to import:"
    _msg error "$probe"
    exit 1
fi

_msg info "Vendored TUI stack OK ($probe)."
