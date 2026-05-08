#!/bin/bash
# name: Android Studio
# version: 1.0
# description: droidstd_desc
# icon: android-studio.svg
# repo: https://developer.android.com/studio/

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_flat com.google.AndroidStudio
zeninf "$msg018"