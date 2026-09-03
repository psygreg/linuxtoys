#!/bin/bash
# name: Pip
# version: 1.0
# description: pip_desc
# icon: pip.svg
# repo: https://pypi.org/project/pip/

# --- Start of the script code ---
askpass

if is_arch || is_cachy; then
    pkg_install python-pip python-pipx
elif is_solus; then
    pkg_install pip pipx
else
    pkg_install python3-pip pipx
fi

info "$msg018"