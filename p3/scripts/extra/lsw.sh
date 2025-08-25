#!/bin/bash
# name: lsw
# version: 1.0
# description: lsw_desc
# icon: lsw.svg
# compat: ubuntu, debian, fedora, arch, cachy, suse
# noconfirm: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
cd $HOME
sleep 1
{
    echo "$msg209"
    echo "$msg210"
    echo "$msg211"
    echo "$msg212"
    echo "$msg213"
    echo "$msg214"
    echo "$msg215"
    echo "$msg216"
} > txtbox

zenity --text-info \
    --title="LSW" \
    --filename=txtbox \
    --checkbox="$msg276" \
    --width=400 --height=360
    
if zenity --question --title "LSW" --text "$msg217" --height=300 --width=300; then
    bash <(curl -s https://raw.githubusercontent.com/psygreg/lsw/refs/heads/main/src/lsw-in.sh)
    sleep 1
    rm txtbox
fi