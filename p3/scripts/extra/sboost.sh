#!/bin/bash
# name: Shader Booster
# version: 1.0
# description: sboost_desc
# icon: gaming.svg
# reboot: yes
# nocontainer
# optimized-only: yes

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

GITHUB_BASE="https://raw.githubusercontent.com/psygreg/shader-booster/main"
GITEA_BASE="https://git.linux.toys/psygreg/shader-booster/raw/branch/main"
fetch_with_fallback () {
    local filename="$1"
    local output_file="$2"
    if wget -q -O "$output_file" "${GITHUB_BASE}/${filename}" 2>/dev/null; then
        return 0
    fi
    if wget -q -O "$output_file" "${GITEA_BASE}/${filename}" 2>/dev/null; then
        return 0
    fi

    return 1
}

# patch for Nvidia GPUs
patch_nv () {
    cd $HOME
    if fetch_with_fallback "patch-nvidia" "${HOME}/patch-nvidia"; then
        echo -e "\n$(cat ${HOME}/patch-nvidia)" | sudo tee -a "${DEST_FILE}" > /dev/null
        rm ${HOME}/patch-nvidia
    else
        fatal "Failed to fetch patch-nvidia."
    fi
}

# patch for Mesa-driven GPUs
patch_mesa () {

    cd $HOME
    if fetch_with_fallback "patch-mesa" "${HOME}/patch-mesa"; then
        echo -e "\n$(cat ${HOME}/patch-mesa)" | sudo tee -a "${DEST_FILE}" > /dev/null
        rm ${HOME}/patch-mesa
    else
        fatal "Failed to fetch patch-mesa."
    fi
}
# LÓGICA DE DETECÇÃO ALTERADA para suportar múltiplos GPUs.
HAS_NVIDIA=$(lspci | grep -i 'nvidia')
HAS_MESA=$(lspci | grep -Ei '(vga|3d)' | grep -vi nvidia)
PATCH_APPLIED=0
# A estrutura geral do runtime é mantida, começando pela verificação do .booster
if [ ! -f ${HOME}/.booster ]; then
    # O bloco para encontrar o DEST_FILE é IDÊNTICO AO ORIGINAL
    #if [[ -f "${HOME}/.bash_profile" ]]; then
    #    DEST_FILE="${HOME}/.bash_profile"
    #elif [[ -f "${HOME}/.profile" ]]; then
    #    DEST_FILE="${HOME}/.profile"
    #elif [[ -f "${HOME}/.zshrc" ]]; then
    #    DEST_FILE="${HOME}/.zshrc"
    #else
        # Mensagem de erro idêntica à original
        #whiptail --title "Shader Booster" --msgbox "No valid shell found." 8 78
        #exit 1
    #fi
    DEST_FILE="/etc/environment"

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
    exit 10
fi
