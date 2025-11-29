#!/bin/bash
# name: unoptimize
# version: 1.0
# description: unoptimize_desc
# icon: optimizer.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy
# reboot: yes
# noconfirm: yes
# nocontainer

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
PATH_UDEV="/usr/lib/udev/rules.d"
sudo rm $PATH_UDEV/20-audio-pm.rules \
        $PATH_UDEV/40-hpet-permissions.rules \
        $PATH_UDEV/50-sata.rules \
        $PATH_UDEV/60-ioschedulers.rules \
        $PATH_UDEV/69-hdparm.rules \
        $PATH_UDEV/99-cpu-dma-latency.rules
PATH_TEMPFILES="/usr/lib/tmpfiles.d/"
sudo rm $PATH_TEMPFILES/coredump.conf \
        $PATH_TEMPFILES/thp-shrinker.conf \
        $PATH_TEMPFILES/thp.conf
PATH_MODPROBE="/usr/lib/modprobe.d/"
sudo rm $PATH_MODPROBE/20-audio-pm.conf \
        $PATH_MODPROBE/amdgpu.conf \
        $PATH_MODPROBE/blacklist.conf \
        $PATH_MODPROBE/nvidia.conf
sudo rm /usr/lib/sysctl.d/99-cachyos-settings.conf
sudo rm /usr/lib/systemd/journald.conf.d/00-journal-size.conf
sudo rm /usr/share/X11/xorg.conf.d/20-touchpad.conf
sudo rm /etc/sysctl.d/99-splitlock.conf
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
    # revert ondemand governor
    if [ -f /etc/systemd/system/set-ondemand-governor.service ]; then
        if [ -f /etc/grub.d/01_intel_pstate_disable ]; then
            sudo rm -f /etc/grub.d/01_intel_pstate_disable
            # Update GRUB configuration
            if [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]] || [[ "$ID_LIKE" == *suse* ]] || [[ "$ID" == *suse* ]]; then
                sudo grub2-mkconfig -o /boot/grub2/grub.cfg
            elif [[ "$ID" =~ ^(arch)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
                sudo grub-mkconfig -o /boot/grub/grub.cfg
            elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
                sudo update-grub
            fi
        fi
    fi
    sudo systemctl disable set-ondemand-governor.service
    sudo rm -f /etc/systemd/system/set-ondemand-governor.service
fi
rm $HOME/.local/.autopatch.state
zeninf "$msg036"