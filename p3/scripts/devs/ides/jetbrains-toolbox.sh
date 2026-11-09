#!/bin/bash
# name: JetBrains Toolbox
# version: 1.0
# description: jbtb_desc
# icon: jetbrains-toolbox.svg

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

PKG_NAM="jetbrains-toolbox"
PKG_DIR="${HOME}/.local/${PKG_NAM}"
TOOLBOX_DATA="${HOME}/.local/share/JetBrains/Toolbox"
DESKTOP_FILE="${HOME}/.local/share/applications/${PKG_NAM}.desktop"

if [ -d "${PKG_DIR}" ]; then
	info "$notdomsg" && exit 100
fi

PKG_URL="$(
	curl -fsSL \
		'https://data.services.jetbrains.com/products/releases?code=TBA&latest=true&type=release' |
		grep -Pio '"linux":\{"link":"\K[^"]+'
)" || exit 1
[ -n "$PKG_URL" ] || exit 1
toolbox_archive=$(mktemp --suffix=.tar.gz) || exit 1
trap 'rm -f "$toolbox_archive"' EXIT
curl -fsSL "${PKG_URL}" -o "$toolbox_archive" || exit 1
_architecture_check files "$toolbox_archive"
prep_dir "${PKG_DIR}"
tar -xzf "$toolbox_archive" -C "${PKG_DIR}" || exit 1

TOOLBOX_BIN="$(
	find "${PKG_DIR}" \
		-type f \
		-path "*/bin/${PKG_NAM}" \
		-print -quit
)"
[ -n "$TOOLBOX_BIN" ] || exit 1
prep_dir "${TOOLBOX_DATA}"
"${TOOLBOX_BIN}" &
TOOLBOX_PID=$!
sleep 10
if kill -0 "$TOOLBOX_PID" 2>/dev/null; then
	kill "$TOOLBOX_PID" 2>/dev/null
fi
wait "$TOOLBOX_PID" 2>/dev/null || true
if [ -f "${DESKTOP_FILE}" ]; then
	_append_transmap "created $DESKTOP_FILE"
else
	exit 1
fi

info "$finishmsg"