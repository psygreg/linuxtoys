#!/bin/bash
# name: Shader Booster
# version: 1.0
# description: sboost_desc
# icon: gaming.svg
# reboot: yes
# nocontainer
# optimized-only: yes

# --- Start of the script code ---
if [ ! -f ${HOME}/.booster ]; then
    prep_tmp
    GITHUB_BASE="https://raw.githubusercontent.com/psygreg/shader-booster/main"
    # patch for Nvidia GPUs
    patch_nv () {
        if wget -q -O "patch-nvidia" "${GITHUB_BASE}/patch-nvidia"; then
            echo -e "\n$(cat patch-nvidia)" | sudo tee -a "${DEST_FILE}" > /dev/null
            return 0
        else
            die "Failed to fetch patch-nvidia."
        fi
    }
    # patch for Mesa-driven GPUs
    patch_mesa () {
        if wget -q -O "patch-mesa" "${GITHUB_BASE}/patch-mesa"; then
            echo -e "\n$(cat patch-mesa)" | sudo tee -a "${DEST_FILE}" > /dev/null
            return 0
        else
            die "Failed to fetch patch-mesa."
        fi
    }
    PATCH_APPLIED=0
    if [ ! -f ${HOME}/.booster ]; then
        askpass
        DEST_FILE="/etc/environment"
        prep_edit /etc/environment
        if is_nvidia; then
            if grep -q "^GL_SHADER_DISK_CACHE_SIZE=" "$DEST_FILE"; then
                sudo sed -i \
                "s/^GL_SHADER_DISK_CACHE_SIZE=.*/GL_SHADER_DISK_CACHE_SIZE=10000000000/" \
                "$DEST_FILE"
            else
                if patch_nv; then
                    PATCH_APPLIED=1
                fi
            fi
        else
            if grep -q "^MESA_SHADER_CACHE_MAX_SIZE=" "$DEST_FILE"; then
                sudo sed -i \
                "s/^MESA_SHADER_CACHE_MAX_SIZE=.*/MESA_SHADER_CACHE_MAX_SIZE=10000000000/" \
                "$DEST_FILE"
            else
                if patch_mesa; then
                    PATCH_APPLIED=1
                fi
            fi
        fi

        if [ $PATCH_APPLIED -eq 1 ]; then
            info "Success! Reboot to apply."
            prep_create "${HOME}/.booster"
            exit 0
        fi
    fi
    zeninf "$finishmsg"
else
    zenwrn "System already patched."
    exit 100
fi
