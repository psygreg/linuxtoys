#!/bin/bash
# name: GPU Screen Recorder
# version: 1.0
# description: gsr_desc
# icon: gsr.png
# repo: https://git.dec05eba.com/?p=about

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_flat --skip-user com.dec05eba.gpu_screen_recorder
is_intel && { pkg_flat --skip-user org.freedesktop.Platform.VAAPI.Intel/x86_64/24.08 || fatal "Failed to install Intel VAAPI platform"; } || true
zeninf "$finishmsg"