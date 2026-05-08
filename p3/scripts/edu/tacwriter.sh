#!/bin/bash
# name: Tac Writer
# version: 1.0
# description: tacw_desc
# icon: tacwriter.svg
# repo: https://github.com/narayanls/tac-writer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

GITHUB_API="https://api.github.com/repos/narayanls/tac-writer/releases/latest"
TMP_BUNDLE="/tmp/tac-writer.flatpak"
TMP_LOG="/tmp/tac-writer-flatpak-install.log"

sudo_rq
# Resolve latest .flatpak bundle and version tag from GitHub releases
GITHUB_JSON=$(curl -fsSL "$GITHUB_API")
LATEST_BUNDLE_URL=$(echo "$GITHUB_JSON" | grep 'browser_download_url' | grep '\.flatpak"' | head -1 | cut -d'"' -f4)
LATEST_VERSION=$(echo "$GITHUB_JSON" | grep '"tag_name"' | head -1 | cut -d'"' -f4 | sed 's/^v//')
if [ -z "$LATEST_BUNDLE_URL" ]; then
    fatal "Could not find a .flatpak asset in the latest Tac Writer release."
fi

if ! curl -fsSL "$LATEST_BUNDLE_URL" -o "$TMP_BUNDLE"; then
    fatal "Failed to download Tac Writer flatpak bundle."
fi
# Install bundle for current user (silent mode; show details only on failure)
if ! pkg_fromfile "$TMP_BUNDLE" >/dev/null 2>"$TMP_LOG"; then
    cat "$TMP_LOG"
    rm -f "$TMP_LOG"
    rm -f "$TMP_BUNDLE"
    fatal "Tac Writer flatpak installation failed."
fi
# Write version file so the in-app update checker can compare against GitHub tags
if [ -n "$LATEST_VERSION" ]; then
	VERSION_FILE="$HOME/.local/share/tac-writer/version.txt"
    if [ -f "$VERSION_FILE" ]; then
        prep_edit "$VERSION_FILE"
    else
        prep_create "$VERSION_FILE"
    fi
	echo "$LATEST_VERSION" > "$VERSION_FILE"
fi

zeninf "Tac Writer installation completed."
