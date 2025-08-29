#!/bin/bash
# name: Cloudflare WARP
# version: 1.0
# description: cloudflare_warp_desc
# icon: cloudflare-warp.svg
# compat: ubuntu, debian, fedora

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"

_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"

# Check if cloudflare-warp is already installed
if command -v warp-cli &> /dev/null; then
    # p3/libs/lang/*.json
    zeninf " ✅ Cloudflare WARP"
    exit 0
fi

sudo_rq

if command -v apt &> /dev/null; then
    # Add cloudflare gpg key
    curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg

    # Check for supported release
    RELEASE=$(lsb_release -cs)
    SUPPORTED_RELEASES=("noble" "jammy" "focal" "bookworm" "bullseye" "buster")
    if [[ ! "${SUPPORTED_RELEASES[*]}" =~ "${RELEASE}" ]]; then
        RELEASE="jammy" # Fallback to a stable LTS release
    fi

    # Add this repo to your apt repositories
    echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ ${RELEASE} main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list

    # Install
    sudo apt-get update && sudo apt-get install -y cloudflare-warp

elif command -v dnf &> /dev/null || command -v dnf &> /dev/null; then
    # Add cloudflare-warp.repo to /etc/yum.repos.d/
    curl -fsSl https://pkg.cloudflareclient.com/cloudflare-warp-ascii.repo | sudo tee /etc/yum.repos.d/cloudflare-warp.repo
    # Update and Install
    if command -v dnf &> /dev/null; then
        sudo dnf install -y cloudflare-warp
    else
        sudo yum install -y cloudflare-warp
    fi
else
    zeninf "$msg003"
    exit 1
fi

if command -v warp-cli &> /dev/null; then
    zeninf "$msg018"
else
    zeninf "❌ Cloudflare WARP."
fi