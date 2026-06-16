#!/bin/bash
# name: Codex
# version: 1.0
# description: codex_desc
# icon: codex.svg
# repo: https://github.com/openai/codex
# compat: debian, ubuntu, fedora, arch, cachy, ostree, rhel, suse
# noconfirm: yes
# nocontainer:

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
zenwrn "$ai_agent_warning"
zenask "Do you want to continue with the installation?" || exit 0
sudo_rq
prep_tmp

export PATH="$HOME/.local/bin:$PATH"

if command -v codex &>/dev/null; then
    zeninf "$msg018"
    exit 0
fi

if curl -fsSL https://chatgpt.com/codex/install.sh | sh; then
    if command -v codex &>/dev/null; then
        zeninf "Codex installed successfully!"
    else
        _msg error "Installation completed but the 'codex' binary was not found in PATH."
        exit 1
    fi
else
    _msg error "Failed to install Codex."
    exit 1
fi
