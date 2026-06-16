#!/bin/bash
# name: OpenCode
# version: 1.0
# description: opencode_desc
# icon: opencode.svg
# repo: https://github.com/opencode-ai/opencode
# compat: debian, ubuntu, fedora, arch, cachy, ostree, rhel, suse
# noconfirm: yes
# nocontainer:

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
prep_tmp

export PATH="$HOME/.opencode/bin:$PATH"

if command -v opencode &>/dev/null; then
    zeninf "$msg018"
    exit 0
fi

if curl -fsSL https://opencode.ai/install | bash; then
    if command -v opencode &>/dev/null; then
        zeninf "OpenCode installed successfully!"
    else
        _msg error "Installation completed but the 'opencode' binary was not found in PATH."
        exit 1
    fi
else
    _msg error "Failed to install OpenCode."
    exit 1
fi
