#!/bin/bash
# name: Lossless Scaling
# version: 1.0
# description: lsfg_desc
# icon: lsfgvk

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
zenwrn "$msg251"
tag=$(curl -s "https://api.github.com/repos/PancakeTAS/lsfg-vk/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
ver="${tag#v}"
DLL_FIND="$(find / -name Lossless.dll 2>/dev/null | head -n 1)"
if [ -z "$DLL_FIND" ]; then
    fatal "Lossless.dll not found. Did you install Lossless Scaling?"
else 
    DLL_ABSOLUTE_PATH=$(dirname "$(realpath "$DLL_FIND")")
    ESCAPED_DLL_PATH=$(printf '%s\n' "$DLL_ABSOLUTE_PATH" | sed 's/[&/\]/\\&/g')
    cd $HOME
    # try update if already installed
    if rpm -qi lsfg-vk &> /dev/null || pacman -Qi lsfg-vk 2>/dev/null 1>&2 || dpkg -s lsfg-vk 2>/dev/null 1>&2; then
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            if [[ "$(dpkg-query -W -f='${Version}' lsfg-vk 2>/dev/null | sed 's/^v//')" != "$ver" ]]; then
                wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.deb
                sudo apt install -y lsfg-vk-${ver}.x86_64.deb
                rm lsfg-vk-${ver}.x86_64.deb
            fi
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ] || [[ "$ID_LIKE" =~ suse ]] || [[ "$ID_LIKE" =~ opensuse ]] || [ "$ID" == "suse" ]; then
            if [[ "$(rpm -q --queryformat '%{VERSION}' lsfg-vk)" != "$ver" ]]; then
                wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.rpm
                if command -v rpm-ostree >/dev/null 2>&1; then
                    sudo rpm-ostree install -yA lsfg-vk-${ver}.x86_64.rpm
                elif command -v zypper >/dev/null 2>&1; then
                    sudo zypper install -y lsfg-vk-${ver}.x86_64.rpm
                else
                    sudo dnf install -y lsfg-vk-${ver}.x86_64.rpm
                fi
                rm lsfg-vk-${ver}.x86_64.rpm
            fi
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            if [[ "$(pacman -Qi lsfg-vk 2>/dev/null | awk -F': ' '/^Version/ {print $2}' | sed 's/^v//')" != "$ver" ]]; then
                wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.tar.zst
                sudo pacman -U --noconfirm lsfg-vk-${ver}.x86_64.tar.zst
                rm lsfg-vk-${ver}.x86_64.tar.zst
            fi
        fi
        # update flatpak runtime
        if command -v flatpak &> /dev/null; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak
            flatpak install --reinstall --user -y ./org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak 
            flatpak install --reinstall --user -y ./org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak
            rm org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak
            rm org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak
            # update overrides if new additions are in this script
            flatapps=(com.usebottles.bottles net.lutris.Lutris com.valvesoftware.Steam com.heroicgameslauncher.hgl org.prismlauncher.PrismLauncher com.stremio.Stremio at.vintagestory.VintageStory org.vinegarhq.Sober)
            for flatapp in "${flatapps[@]}"; do
                if flatpak info "$flatapp" &> /dev/null; then
                    flatpak override --user --filesystem="$HOME/.config/lsfg-vk:rw" "$flatapp"
                    flatpak override --user --env=LSFG_CONFIG="$HOME/.config/lsfg-vk/conf.toml" "$flatapp"
                    if [ "$flatapp" != "com.valvesoftware.Steam" ]; then
                        flatpak override --user --filesystem="$DLL_ABSOLUTE_PATH:ro" "$flatapp"
                    fi
                fi
            done
        fi
    else
        # install lsfg-vk
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.deb
            sudo apt install -y ./lsfg-vk-${ver}.x86_64.deb
            rm lsfg-vk-${ver}.x86_64.deb
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.rpm
            if command -v rpm-ostree >/dev/null 2>&1; then
                sudo rpm-ostree install -y ./lsfg-vk-${ver}.x86_64.rpm
            else
                sudo dnf install -y ./lsfg-vk-${ver}.x86_64.rpm
            fi
            rm lsfg-vk-${ver}.x86_64.rpm
        elif [[ "$ID_LIKE" == *suse* ]] || [ "$ID" == "suse" ]; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.rpm
            sudo zypper install -y ./lsfg-vk-${ver}.x86_64.rpm
            rm lsfg-vk-${ver}.x86_64.rpm
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.tar.zst
            sudo pacman -U --noconfirm lsfg-vk-${ver}.x86_64.tar.zst
            rm lsfg-vk-${ver}.x86_64.tar.zst
        fi
        # first time setup: dll tracker
        CONF_LOC="${HOME}/.config/lsfg-vk/conf.toml"
        if [ ! -f "$CONF_LOC" ]; then
            # make sure target dir exists
            mkdir -p ${HOME}/.config/lsfg-vk/
            wget https://raw.githubusercontent.com/psygreg/linuxtoys-atom/refs/heads/main/src/patches/conf.toml
            mv conf.toml ${HOME}/.config/lsfg-vk/
        fi
        # register dll location in config file
        sed -i -E "s|^# dll = \".*\"|dll = \"$ESCAPED_DLL_PATH\"|" ${HOME}/.config/lsfg-vk/conf.toml
        # flatpak runtime
        if command -v flatpak &> /dev/null; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak
            flatpak install --reinstall --user -y ./org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak 
            flatpak install --reinstall --user -y ./org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak
            rm org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak
            rm org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak
            flatapps=(com.usebottles.bottles net.lutris.Lutris com.valvesoftware.Steam com.heroicgameslauncher.hgl org.prismlauncher.PrismLauncher com.stremio.Stremio at.vintagestory.VintageStory org.vinegarhq.Sober)
            for flatapp in "${flatapps[@]}"; do
                if flatpak info "$flatapp" &> /dev/null; then
                    flatpak override --user --filesystem="$HOME/.config/lsfg-vk:rw" "$flatapp"
                    flatpak override --user --env=LSFG_CONFIG="$HOME/.config/lsfg-vk/conf.toml" "$flatapp"
                    if [ "$flatapp" != "com.valvesoftware.Steam" ]; then
                        flatpak override --user --filesystem="$DLL_ABSOLUTE_PATH:ro" "$flatapp"
                    fi
                fi
            done
        fi
    fi
fi