#!/bin/bash
# name: Shader Booster
# version: 1.0
# description: sboost_desc
# icon: gaming.svg
# reboot: yes
# nocontainer

# --- Start of the script code ---
# patch for Nvidia GPUs
patch_nv () {
    cd $HOME
    wget -O patch-nvidia https://raw.githubusercontent.com/psygreg/shader-booster/refs/heads/main/patch-nvidia;
    echo -e "\n$(cat ${HOME}/patch-nvidia)" >> "${DEST_FILE}"
    rm ${HOME}/patch-nvidia
}
# patch for Mesa-driven GPUs
patch_mesa () {
    cd $HOME
    wget -O patch-mesa https://raw.githubusercontent.com/psygreg/shader-booster/refs/heads/main/patch-mesa;
    echo -e "\n$(cat ${HOME}/patch-mesa)" >> "${DEST_FILE}"
    rm ${HOME}/patch-mesa
}
# LÓGICA DE DETECÇÃO ALTERADA para suportar múltiplos GPUs.
HAS_NVIDIA=$(lspci | grep -i 'nvidia')
HAS_MESA=$(lspci | grep -Ei '(vga|3d)' | grep -vi nvidia)
PATCH_APPLIED=0
if [ ! -f ${HOME}/.booster ]; then
    if [[ -f "${HOME}/.bash_profile" ]]; then
        DEST_FILE="${HOME}/.bash_profile"
    elif [[ -f "${HOME}/.profile" ]]; then
        DEST_FILE="${HOME}/.profile"
    elif [[ -f "${HOME}/.zshrc" ]]; then
        DEST_FILE="${HOME}/.zshrc"
    else
        fatal "No valid shell found."
        exit 1
    fi
    
    if [[ -n "$HAS_NVIDIA" ]]; then
        patch_nv
        PATCH_APPLIED=1
    fi
    
    if [[ -n "$HAS_MESA" ]]; then
        patch_mesa
        PATCH_APPLIED=1
    fi

    if [ $PATCH_APPLIED -eq 1 ]; then
        zeninf "Success! Reboot to apply."
        echo "1" > "${HOME}/.booster"
        exit 0
    fi
else
    zenwrn "System already patched."
    exit 0
fi