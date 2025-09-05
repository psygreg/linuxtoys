#!/bin/bash
# name: Webmin
# version: 1.0
# description: webmin_desc
# icon: webmin.png
# compat: debian, ubuntu, fedora

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
sudo_rq
curl -o webmin-setup-repo.sh https://raw.githubusercontent.com/webmin/webmin/master/webmin-setup-repo.sh
sh webmin-setup-repo.sh
_packages=(webmin)
_install_
zeninf $"Operations completed."