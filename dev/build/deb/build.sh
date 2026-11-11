#!/usr/bin/env bash
# Local native DEB construction only. No signing, upload or publishing path.
set -euo pipefail
umask 022
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT_DIR/dev/libs/utils.lib"
if [[ $# -ne 2 ]]; then
    _msg error "Usage: $0 <upstream-version> <new-output-directory>"
    exit 2
fi
VERSION="$1"
REVISION="${DEB_REVISION:-1}"
dpkg --validate-version "$VERSION-$REVISION"
[[ "$VERSION" == "$(cat "$ROOT_DIR/src/ver")" ]] || {
    _msg error "Upstream version must match src/ver"; exit 2;
}
ARCH="$(python3 "$ROOT_DIR/p3/app/architecture_cli.py" label deb)"
[[ "$(uname -s)" == Linux && "$ARCH" == "$(dpkg --print-architecture)" && "$ARCH" == "$(dpkg-architecture -qDEB_HOST_ARCH)" ]] || {
    _msg error "A native Linux build matching M1 and dpkg architecture is required"; exit 2;
}
: "${SOURCE_DATE_EPOCH:?Set SOURCE_DATE_EPOCH to the reviewed source commit timestamp}"
[[ "$SOURCE_DATE_EPOCH" =~ ^[0-9]+$ ]] || exit 2
export SOURCE_DATE_EPOCH PYTHONDONTWRITEBYTECODE=1 CARGO_INCREMENTAL=0
OUTPUT_PATH="$(python3 - "$ROOT_DIR" "$2" <<'PY'
from pathlib import Path
import sys
source = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).absolute()
if any(p.is_symlink() for p in (output, *output.parents)):
    raise SystemExit('Output must not traverse symlinks')
output = output.resolve()
if output.is_relative_to(source) or output.exists():
    raise SystemExit('Output must be new and outside the source checkout')
print(output)
PY
)"
for tool in cargo maturin dpkg-deb dpkg-shlibdeps; do command -v "$tool" >/dev/null; done
python3 "$ROOT_DIR/dev/prepare_script_rollout.py" --check
python3 "$ROOT_DIR/dev/build/deb/package.py" check-inputs "$ROOT_DIR/p3"
mkdir -p -- "$OUTPUT_PATH"
WORK="$OUTPUT_PATH/build"
mkdir -- "$WORK"
cp -a -- "$ROOT_DIR/p3" "$ROOT_DIR/src" "$ROOT_DIR/dev" "$ROOT_DIR/Cargo.toml" "$ROOT_DIR/Cargo.lock" "$ROOT_DIR/pyproject.toml" "$ROOT_DIR/build-rust.sh" "$WORK/"
# Rebuild native modules; never reuse development extensions or bytecode.
find "$WORK/p3" -type d -name __pycache__ -prune -exec rm -rf -- {} +
find "$WORK/p3" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
find "$WORK/p3/app" -maxdepth 1 -type f \( -name '_catalog_rs*.so' -o -name 'liblinuxtoys_gui.so' \) -delete
export CARGO_TARGET_DIR="$WORK/target"
export RUSTFLAGS="${RUSTFLAGS:-} --remap-path-prefix=$WORK=/usr/src/linuxtoys --remap-path-prefix=${CARGO_HOME:-$HOME/.cargo}=/usr/share/cargo"
_msg info "Building LinuxToys $VERSION-$REVISION natively for $ARCH"
bash "$WORK/dev/build/vendor_deps.sh"
bash "$WORK/build-rust.sh" build --out "$WORK/native"
PACKAGE_ROOT="$WORK/package"
python3 "$WORK/dev/build/deb/package.py" stage "$WORK" "$PACKAGE_ROOT" "$WORK/native"
mkdir -p "$WORK/debian"
printf 'Source: linuxtoys\nPackage: linuxtoys\nArchitecture: %s\nDescription: LinuxToys\n' "$ARCH" > "$WORK/debian/control"
# Use the native package database/symbols; missing linkage metadata is an error.
SHLIBS="$(cd -- "$WORK" && dpkg-shlibdeps -O -e"$PACKAGE_ROOT/usr/lib/linuxtoys/app/_catalog_rs.abi3.so" -e"$PACKAGE_ROOT/usr/lib/linuxtoys/app/liblinuxtoys_gui.so")"
[[ "$SHLIBS" == shlibs:Depends=* && "$SHLIBS" != *$'\n'* ]] || exit 1
python3 "$WORK/dev/build/deb/package.py" control "$WORK" "$PACKAGE_ROOT" "$VERSION-$REVISION" "$ARCH" "${SHLIBS#shlibs:Depends=}"
PACKAGE="$OUTPUT_PATH/linuxtoys_${VERSION}-${REVISION}_${ARCH}.deb"
find "$PACKAGE_ROOT" -exec touch -h --date="@$SOURCE_DATE_EPOCH" -- {} +
dpkg-deb --root-owner-group --uniform-compression -Zxz -z9 --build "$PACKAGE_ROOT" "$PACKAGE"
python3 "$WORK/p3/app/architecture_cli.py" files "$PACKAGE"
python3 "$WORK/dev/build/deb/package.py" provenance "$WORK" "$PACKAGE" "$OUTPUT_PATH/build-provenance.json"
sha256sum "$PACKAGE" > "$OUTPUT_PATH/SHA256SUMS"
_msg info "Local package: $PACKAGE"
