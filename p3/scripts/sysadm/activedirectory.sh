#!/bin/bash
# name: Active Directory
# version: 1.0
# description: adir_desc
# icon: adir.svg
# compat: debian, ubuntu, fedora, ostree, ublue

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_fedora; then
    pkg_install sssd realmd oddjob oddjob-mkhomedir adcli samba-common samba-common-tools krb5-workstation openldap-clients policycoreutils-python
elif is_ubuntu; then
    pkg_install sssd realmd adcli samba-common-bin adsys krb5-user libpam-krb5 libpam-ccreds auth-client-config
elif is_debian; then
    pkg_install sssd realmd adcli samba-common-bin adsys krb5-user libpam-krb5 libpam-ccreds auth-client-config oddjob oddjob-mkhomedir
fi
zeninf "$msg289"