#!/bin/bash
# name: Webmin
# version: 1.1
# description: webmin_desc
# icon: webmin.png
# compat: debian, ubuntu, fedora

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq

if ! curl -fsSL -o /tmp/webmin-setup-repo.sh https://raw.githubusercontent.com/webmin/webmin/master/webmin-setup-repo.sh; then
    fatal "Failed to download Webmin repository setup script."
fi

if ! sudo sh /tmp/webmin-setup-repo.sh -f; then
    rm -f /tmp/webmin-setup-repo.sh
    fatal "Failed to setup Webmin repository."
fi

pkg_install webmin
zeninf "$msg018"

