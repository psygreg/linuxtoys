#!/bin/bash
# name: OMP
# version: 1.0
# description: omp_desc
# icon: omp.svg
# repo: https://github.com/can1357/oh-my-pi
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

if curl -fsSL https://omp.sh/install | sh; then
    if command -v pi &>/dev/null; then
        zeninf "OMP installed successfully!"
    else
        _msg error "Installation completed but the 'pi' binary was not found in PATH."
        exit 1
    fi
else
    _msg error "Failed to install OMP."
    exit 1
fi
