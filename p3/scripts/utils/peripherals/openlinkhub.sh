#!/bin/bash
# name: OpenLinkHub
# version: 1.0
# description: openlinkhub_desc
# icon: corsair.svg
# repo: https://github.com/jurkovic-nikola/OpenLinkHub
# compat: ubuntu, debian, fedora, ostree, ublue, arch, cachy

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
# for version comparison
tag=$(curl -s "https://api.github.com/repos/jurkovic-nikola/OpenLinkHub/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
sudo_rq
if is_ubuntu; then
    sudo add-apt-repository ppa:jurkovic-nikola/openlinkhub
    sudo apt update
    pkg_install openlinkhub
elif is_debian; then
    prep_tmp
    wget "https://github.com/jurkovic-nikola/OpenLinkHub/releases/download/${tag}/OpenLinkHub_${tag}_amd64.deb"
    pkg_fromfile ./OpenLinkHub_${tag}_amd64.deb
elif is_ostree; then
    prep_tmp
    wget https://copr.fedorainfracloud.org/coprs/jurkovic-nikola/OpenLinkHub/repo/fedora-$(rpm -E %fedora)/jurkovic-nikola-OpenLinkHub-fedora-$(rpm -E %fedora).repo
    sudo install -o 0 -g 0 jurkovic-nikola-OpenLinkHub-fedora-$(rpm -E %fedora).repo /etc/yum.repos.d/jurkovic-nikola-OpenLinkHub-fedora-$(rpm -E %fedora).repo
    rpm-ostree refresh-md
    pkg_install OpenLinkHub
elif is_fedora; then
    sudo dnf copr enable jurkovic-nikola/OpenLinkHub
    pkg_install OpenLinkHub
elif is_arch || is_cachy; then
    pkg_install openlinkhub-bin
fi
sysd_enable OpenLinkHub.service
sleep 1
xdg-open http://127.0.0.1:27003
zeninf "$finishmsg"
exit 0
