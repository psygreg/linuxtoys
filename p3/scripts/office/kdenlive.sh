#!/bin/bash
# name: Kdenlive
# version: 1.0
# description: kdenlive_desc
# icon: kdenlive.svg
# repo: https://kde.org

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
prep_tmp_noram
# Fetch the latest Kdenlive AppImage version
LATEST_VERSION=$(curl -s https://download.kde.org/stable/kdenlive/ | grep -oP '>[^<]*</a>' | grep -oP '\d+\.\d+' | sort -rV | head -1)
if [ -z "$LATEST_VERSION" ]; then
    echo "Failed to fetch latest Kdenlive version"
    exit 1
fi
LATEST_PATCH=$(curl -s "https://download.kde.org/stable/kdenlive/${LATEST_VERSION}/linux/" | grep -oP "kdenlive-${LATEST_VERSION}\.\d+-x86_64\.AppImage" | sort -rV | head -1)
if [ -z "$LATEST_PATCH" ]; then
    echo "Failed to fetch latest patch version"
    exit 1
fi
URL="https://download.kde.org/stable/kdenlive/${LATEST_VERSION}/linux/${LATEST_PATCH}"

curl -L -o "$LATEST_PATCH" "$URL"
pkg_appimage "$LATEST_PATCH"

zeninf "$finishmsg"
