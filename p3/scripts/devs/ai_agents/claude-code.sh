#!/bin/bash
# name: Claude Code
# version: 1.0
# description: claude_code_desc
# icon: claude-code.svg
# repo: https://github.com/anthropics/claude-code
# compat: debian, ubuntu, fedora, arch, cachy, ostree, rhel, suse
# noconfirm: yes
# nocontainer:

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
prep_tmp

export PATH="$HOME/.local/bin:$PATH"

if command -v claude &>/dev/null; then
    zeninf "$msg018"
    exit 0
fi

if curl -fsSL https://claude.ai/install.sh | bash; then
    if command -v claude &>/dev/null; then
        zeninf "Claude Code installed successfully!\n\nNote: A paid Anthropic plan (Pro, Max, Team, or Enterprise) is required to use."
    else
        _msg error "Installation completed but the 'claude' binary was not found in PATH."
        exit 1
    fi
else
    _msg error "Failed to install Claude Code."
    exit 1
fi
