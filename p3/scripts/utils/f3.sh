#!/bin/bash
# name: F3 (Fight Flash Fraud)
# version: 1.0
# description: f3_desc
# icon: utils.svg
# nocontainer

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
_packages=(f3)
sudo_rq
_install_
zeninf $"F3 has been installed. A browser window will now open with usage instructions."
xdg-open https://fight-flash-fraud.readthedocs.io/en/latest/introduction.html#examples-1