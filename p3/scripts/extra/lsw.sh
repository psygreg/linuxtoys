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
cd $HOME
sleep 1
{
    echo $"Welcome to the LSW installer!"
    echo $"This script will guide you through installing Windows on Linux."
    echo ""
    echo $"WARNINGS:"
    echo $"* This is an automated script. Use at your own risk."
    echo $"* A stable internet connection is required."
    echo $"* Do NOT close the terminal during installation."
    echo $"* GPU acceleration is NOT available."
} > txtbox

zenity --text-info \
    --title="LSW" \
    --filename=txtbox \
    --checkbox=$"I have read and understood the warnings." \
    --width=400 --height=360
    
if zenity --question --title="LSW" --text=$"Do you want to proceed with the installation?" --height=300 --width=300; then
    bash <(curl -s https://raw.githubusercontent.com/psygreg/lsw/refs/heads/main/src/lsw-in.sh)
    sleep 1
    rm txtbox
fi