#!/bin/bash
# name: OpenLinkHub
# version: 1.0
# description: openlinkhub_desc
# icon: corsair.svg
# repo: https://github.com/jurkovic-nikola/OpenLinkHub
# compat: ubuntu, debian, fedora, ostree, ublue, arch, cachy, rhel

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# for version comparison
askpass
curl -fsSL https://raw.githubusercontent.com/jurkovic-nikola/OpenLinkHub/main/remote-install.sh | bash
_append_transmap "created $HOME/.config/systemd/user/OpenLinkHub.service"
_append_transmap "created $HOME/OpenLinkHub"
_append_transmap "created /etc/udev/rules.d/99-openlinkhub.rules"
_append_transmap "sysd usermode enabled OpenLinkHub.service"
_append_transmap "sysd usermode started OpenLinkHub.service"
xdg-open http://127.0.0.1:27003
info "$rebootmsg"
