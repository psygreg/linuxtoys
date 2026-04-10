#!/bin/bash
# name: k6
# version: 1.0
# description: k6_desc
# icon: k6.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy, ostree, ublue
# repo: https://github.com/grafana/k6

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

K6_API_URL="https://api.github.com/repos/grafana/k6/releases/latest"
K6_TMP_DIR="$(mktemp -d /tmp/k6.XXXXXX)"
K6_ARCHIVE="$K6_TMP_DIR/k6.tar.gz"

cleanup() {
    rm -rf "$K6_TMP_DIR"
}
trap cleanup EXIT

sudo_rq

if ! command -v curl >/dev/null 2>&1; then
    if is_debian; then
        sudo apt update || true
    fi
    _packages=(curl)
    _install_
    command -v curl >/dev/null 2>&1 || fatal "curl command not found after installation attempt."
fi

if ! command -v tar >/dev/null 2>&1; then
    if is_debian; then
        sudo apt update || true
    fi
    _packages=(tar)
    _install_
    command -v tar >/dev/null 2>&1 || fatal "tar command not found after installation attempt."
fi

case "$(uname -m)" in
    x86_64) k6_arch="amd64" ;;
    aarch64|arm64) k6_arch="arm64" ;;
    *)
        fatal "Unsupported architecture for k6: $(uname -m)"
        ;;
esac

K6_JSON="$(curl -fsSL "$K6_API_URL")" || fatal "Failed to query the latest k6 release."
K6_URL="$(echo "$K6_JSON" | grep 'browser_download_url' | grep "linux-${k6_arch}\\.tar\\.gz\"" | head -1 | cut -d'"' -f4)"

[ -n "$K6_URL" ] || fatal "Could not find a Linux k6 binary for architecture: $k6_arch"

curl -fsSL "$K6_URL" -o "$K6_ARCHIVE" || fatal "Failed to download k6."
tar -xzf "$K6_ARCHIVE" -C "$K6_TMP_DIR" || fatal "Failed to extract k6 archive."

K6_BIN="$(find "$K6_TMP_DIR" -type f -name k6 | head -1)"
[ -n "$K6_BIN" ] || fatal "k6 executable not found after extraction."

if ! sudo install -Dm755 "$K6_BIN" /usr/local/bin/k6; then
    fatal "Failed to install k6 to /usr/local/bin."
fi

command -v k6 >/dev/null 2>&1 || fatal "k6 command was not found after installation."
zeninf "$msg018"
