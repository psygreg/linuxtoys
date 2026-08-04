#!/bin/bash
# name: Medicat USB
# description: medicat_desc
# icon: medicat.png
# repo: https://medicatusb.com
# nocontainer
# revert: no
# new

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

pkg_install --ostreecheck dos2unix
prep_tmp_noram

REPO="mon5termatt/medicat_installer"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"
LATEST_TAG=$(curl -fsSL -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" "$API_URL" | sed -n 's/^[[:space:]]*"tag_name":[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)
[ -n "$LATEST_TAG" ] || fatal "Could not determine the latest MediCat Installer release."
INSTALLER_URL="https://github.com/${REPO}/releases/download/${LATEST_TAG}/Medicat_Installer.sh"
echo "Latest MediCat Installer release: $LATEST_TAG"
echo "Downloading: $INSTALLER_URL"
if ! wget -O medicat.sh "$INSTALLER_URL"; then
    fatal "Failed to download MediCat Installer release $LATEST_TAG."
fi

dos2unix medicat.sh
chmod +x medicat.sh
./medicat.sh

pkg_rm dos2unix
zeninf "$finishmsg"