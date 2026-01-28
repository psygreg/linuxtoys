#!/bin/bash
# name: Tac Writer
# version: 1.0
# description: tacw_desc
# icon: tacwriter.svg
# repo: https://github.com/narayanls/tac-writer

# --- Start of the script code ---
. /etc/os-release
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
# Get the latest release URL from GitHub API
GITHUB_API="https://api.github.com/repos/narayanls/tac-writer/releases/latest"
LATEST_RELEASE=$(curl -s "$GITHUB_API" | grep '"download_url"' | grep 'install.sh' | head -1 | cut -d'"' -f4)
if [ -z "$LATEST_RELEASE" ]; then
    # Fallback: try to construct URL from release tag
    RELEASE_TAG=$(curl -s "$GITHUB_API" | grep '"tag_name"' | head -1 | cut -d'"' -f4)
    if [ -n "$RELEASE_TAG" ]; then
        LATEST_RELEASE="https://github.com/narayanls/tac-writer/releases/download/${RELEASE_TAG}/install.sh"
    fi
fi
if [ -n "$LATEST_RELEASE" ]; then
    # Download and execute the install.sh script
    curl -fsSL "$LATEST_RELEASE" | bash
else
    echo "Error: Could not find install.sh in the latest tac-writer release"
    exit 1
fi
