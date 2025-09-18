#!/bin/bash
# name: Active Directory
# version: 1.0
# description: adir_desc
# icon: adir.svg
# compat: debian, ubuntu, fedora, ostree, ublue

#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
if [[ "$ID" =~ "fedora" ]] || [[ "$ID" =~ "rhel" ]] || [[ "$ID_LIKE" =~ "fedora" ]]; then
    _packages=(sssd realmd oddjob oddjob-mkhomedir adcli samba-common samba-common-tools krb5-workstation openldap-clients policycoreutils-python)
elif [ "$ID" == "ubuntu" ]; then
    _packages=(sssd realmd adcli samba-common-bin adsys krb5-user libpam-krb5 libpam-ccreds auth-client-config)
elif [ "$ID" == "debian" ]; then
    _packages=(sssd realmd adcli samba-common-bin adsys krb5-user libpam-krb5 libpam-ccreds auth-client-config oddjob oddjob-mkhomedir)
fi
_install_
zeninf "$msg289"