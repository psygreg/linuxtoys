#!/bin/bash
# name: unoptimize
# version: 1.0
# description: unoptimize_desc
# icon: optimizer.svg
# compat: ostree, ublue
# reboot: ostree
# noconfirm: yes
# nocontainer

# --- Start of the script code ---
sudo rpm-ostree remove linuxtoys-cfg-atom
# Remove shader booster patches
if [ -f "${HOME}/.booster" ]; then
    echo "Removing shader booster patches..."  
    # Function to remove shader booster lines from a config file
    remove_shader_booster_from_file() {
        local file="$1"
        if [[ -f "$file" ]]; then
            # Create a temporary file to store cleaned content
            local temp_file
            temp_file=$(mktemp)  
            # Remove shader booster related lines
            grep -v -E '^# increase Nvidia shader cache size to 12GB$|^export __GL_SHADER_DISK_CACHE_SIZE=12000000000$|^# enforce RADV vulkan implementation$|^export AMD_VULKAN_ICD=RADV$|^# increase AMD and Intel cache size to 12GB$|^export MESA_SHADER_CACHE_MAX_SIZE=12G$' "$file" > "$temp_file" 
            # Replace original file only if changes were made
            if ! cmp -s "$file" "$temp_file"; then
                mv "$temp_file" "$file"
                echo "  Cleaned shader booster entries from $(basename "$file")"
            else
                rm -f "$temp_file"
            fi
        fi
    }
    # Clean all potential shell configuration files
    remove_shader_booster_from_file "${HOME}/.bash_profile"
    remove_shader_booster_from_file "${HOME}/.profile" 
    remove_shader_booster_from_file "${HOME}/.zshrc"
    # Remove the booster marker file
    rm -f "${HOME}/.booster"
    echo "Shader booster completely removed."
fi
rm $HOME/.local/.autopatch.state
zeninf "$msg036"