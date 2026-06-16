#!/bin/bash
# name: Pi
# version: 1.0
# description: pi_desc
# icon: pi-coding-agent.svg
# repo: https://github.com/priatic/pi-coding-agent
# compat: debian, ubuntu, fedora, arch, cachy, ostree, rhel, suse
# noconfirm: yes
# nocontainer:

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
prep_tmp

export PATH="$HOME/.local/bin:$PATH"

if command -v pi &>/dev/null; then
    zeninf "$msg018"
    exit 0
fi

if curl -fsSL https://pi.dev/install.sh | sh; then
    if command -v pi &>/dev/null; then
        zeninf "Pi installed successfully!"
    else
        _msg error "Installation completed but the 'pi' binary was not found in PATH."
        exit 1
    fi
else
    _msg error "Failed to install Pi."
    exit 1
fi
