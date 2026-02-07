#!/bin/bash
# name: Firefox (no-Snap)
# version: 1.0
# description: firefoxsnap_desc
# icon: firefox.svg
# repo: https://www.mozilla.org
# compat: ubuntu, !zorin
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
wget -q https://packages.mozilla.org/apt/repo-signing-key.gpg -O- | gpg --dearmor | sudo tee /etc/apt/keyrings/packages.mozilla.org.gpg > /dev/null
cat << 'EOF' | sudo tee /etc/apt/sources.list.d/mozilla.sources > /dev/null
Types: deb
URIs: https://packages.mozilla.org/apt
Suites: mozilla
Components: main
Signed-By: /etc/apt/keyrings/packages.mozilla.org.gpg
EOF
cat << 'EOF' | sudo tee /etc/apt/preferences.d/mozilla > /dev/null
Package: firefox*
Pin: origin packages.mozilla.org
Pin-Priority: 1001
EOF
cat << 'EOF' | sudo tee /etc/apt/apt.conf.d/51-unattended-upgrades-firefox > /dev/null
Unattended-Upgrade::Origins-Pattern { "archive=mozilla"; };
EOF
sudo apt remove firefox
sudo apt update
sudo apt install firefox
