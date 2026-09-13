#!/usr/bin/env bash

LATEST_VERSION=$(curl -s https://download.kde.org/stable/kdenlive/ | grep -oP '>[^<]*</a>' | grep -oP '\d+\.\d+' | sort -rV | head -1)
if [ -z "$LATEST_VERSION" ]; then
    die "Failed to fetch latest Kdenlive version"
fi
LATEST_PATCH=$(curl -s "https://download.kde.org/stable/kdenlive/${LATEST_VERSION}/linux/" | grep -oP "kdenlive-${LATEST_VERSION}\.\d+-x86_64\.AppImage" | sort -rV | head -1)
if [ -z "$LATEST_PATCH" ]; then
    die "Failed to fetch latest patch version"
fi
URL="https://download.kde.org/stable/kdenlive/${LATEST_VERSION}/linux/${LATEST_PATCH}"
export URL