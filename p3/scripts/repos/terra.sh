#!/bin/bash
# name: Terra
# version: 1.0
# description: terra_desc
# icon: terra.png
# repo: https://github.com/terrapkg/packages
# compat: fedora, ostree

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

if [ -f /etc/yum.repos.d/terra.repo ]; then
    zeninf "Terra repository is already installed!"
    exit 0
fi

sudo_rq

if is_fedora; then
    if sudo dnf install -y --nogpgcheck --repofrompath 'terra,https://repos.fyralabs.com/terra$releasever' terra-release; then
        zeninf "Terra successfully installed!"
    else
        fatal "Installation failed."
    fi
elif is_ostree; then
    curl -fsSL https://github.com/terrapkg/subatomic-repos/raw/main/terra.repo | sudo tee /etc/yum.repos.d/terra.repo
    if sudo rpm-ostree install -y terra-release; then
        zeninf "Terra successfully installed!"
    else
        fatal "Installation failed."
    fi
fi
