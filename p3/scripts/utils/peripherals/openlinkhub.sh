#!/bin/bash
# name: OpenLinkHub
# version: 1.0
# description: openlinkhub_desc
# icon: corsair.svg
# repo: https://github.com/jurkovic-nikola/OpenLinkHub
# compat: ubuntu, debian, fedora, ostree, ublue, arch, cachy, rhel, suse, steamos

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# for version comparison
askpass
if is_ostree || is_steamos; then
    prep_tmp_noram
    TAGNAME=$(curl -s https://api.github.com/repos/jurkovic-nikola/OpenLinkHub/releases/latest | jq -r '.tag_name')
    wget "https://github.com/jurkovic-nikola/OpenLinkHub/releases/latest/download/OpenLinkHub_${TAGNAME}_amd64.tar.gz"
    tar -xf "OpenLinkHub_${TAGNAME}_amd64.tar.gz" -C "$HOME/"
    cd "$HOME/OpenLinkHub"
    chmod +x install-user-space.sh
    ./install-user-space.sh
else
    curl -fsSL https://raw.githubusercontent.com/jurkovic-nikola/OpenLinkHub/main/remote-install.sh | bash
fi
_append_transmap "created $HOME/.config/systemd/user/OpenLinkHub.service"
_append_transmap "created $HOME/OpenLinkHub"
_append_transmap "created /etc/udev/rules.d/99-openlinkhub.rules"
_append_transmap "sysd usermode enabled OpenLinkHub.service"
_append_transmap "sysd usermode started OpenLinkHub.service"
xdg-open http://127.0.0.1:27003
info "$rebootmsg"
