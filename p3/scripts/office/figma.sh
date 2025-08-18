#!/bin/bash
# name: Figma
# version: 1.0
# description: figma_desc
# compat: ubuntu, debian, fedora, suse, cachy, arch
# icon: figma

# --- Start of the script code ---
sudo_rq
cd $HOME
figma_tag=$(curl -s https://api.github.com/repos/Figma-Linux/figma-linux/releases/latest | grep '"tag_name"' | cut -d '"' -f4 | sed 's/^v//')
wget https://github.com/Figma-Linux/figma-linux/releases/download/v${figma_tag}/figma-linux_${figma_tag}_linux_x86_64.AppImage
chmod +x figma-linux-*.AppImage
sudo ./figma-linux-*.AppImage -i
sleep 1
rm figma-linux-*.AppImage
