#!/bin/bash
# name: Windscribe VPN
# version: 1.0
# description: Windscribe VPN
# icon: windscribe.svg
# repo: https://windscribe.com
# compat: !solus

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
prep_tmp
if is_ubuntu || is_debian; then
	wget -O windscribe.deb "https://windscribe.com/install/desktop/linux_deb_x64"
	pkg_fromfile windscribe.deb
	sudo apt-get install -f -y
elif is_fedora || is_ostree; then
	wget -O windscribe.rpm "https://windscribe.com/install/desktop/linux_rpm_x64"
	pkg_fromfile windscribe.rpm
elif is_arch || is_cachy; then
	wget -O windscribe.pkg.tar.zst "https://windscribe.com/install/desktop/linux_zst_x64"
	pkg_fromfile windscribe.pkg.tar.zst
elif is_suse; then
	wget -O windscribe.rpm "https://windscribe.com/install/desktop/linux_rpm_opensuse_x64"
	pkg_fromfile windscribe.rpm
else
    fatal "$msg077"
fi
zeninf "$msg018"
