#!/bin/bash
# name: Portainer CE
# version: 1.0
# description: portainer_desc
# icon: portainer.svg

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
docker volume create portainer_data || fatal "Failed to create docker volume. Did you install Docker first?"
docker run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:lts
zeninf "Setup complete. Your Portainer dashboard will open in your web browser now."
xdg-open https://localhost:9443