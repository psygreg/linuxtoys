#!/bin/bash
# name: S3Drive
# version: 1.0
# description: s3d_desc
# icon: s3drive.png
# repo: https://s3drive.app

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub io.kapsa.drive

