#!/bin/bash
# name: Dockhand
# version: 1.0
# description: dockhand_desc
# icon: dockhand.svg
# revert: no
# compat: !steamos
# repo: https://github.com/Finsys/dockhand

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

: "${dockhand_nodocker:=Docker was not found or is not reachable by your user. Install Docker from LinuxToys first, then log out and back in.}"
: "${dockhand_port_text:=Port 3000 is already in use. Choose another port for the Dockhand web interface:}"
: "${dockhand_port_invalid:=Invalid or busy port.}"
: "${dockhand_exists:=Dockhand is already installed. Its dashboard will open in your web browser now.}"
: "${dockhand_done:=Setup complete. Your Dockhand dashboard will open in your web browser now.}"
: "${dockhand_volume_failed:=Failed to create the Docker volume.}"
: "${dockhand_run_failed:=Failed to start the Dockhand container.}"

DOCKHAND_IMAGE="fnsys/dockhand:latest"

command -v docker &>/dev/null && docker info &>/dev/null || fatal "$dockhand_nodocker"

port_busy () {
    ss -Hltn "sport = :$1" 2>/dev/null | grep -q . && return 0
    docker ps --format '{{.Ports}}' 2>/dev/null | grep -qE "(:|^)$1->" && return 0
    return 1
}

# already installed: just open the dashboard
if docker container inspect dockhand &>/dev/null; then
    docker start dockhand &>/dev/null
    port=$(docker port dockhand 3000/tcp 2>/dev/null | head -n1 | sed 's/.*://')
    zeninf "$dockhand_exists"
    xdg-open "http://localhost:${port:-3000}" &>/dev/null &
    exit 0
fi

port=3000
if port_busy "$port"; then
    port=$(userinput --title "Dockhand" --text "$dockhand_port_text" --default "3001") || exit 100
    [[ "$port" =~ ^[0-9]+$ ]] || fatal "$dockhand_port_invalid"
    # normalize before arithmetic: bash would read a leading zero as octal
    port=$((10#$port))
    if (( port < 1024 || port > 65535 )) || port_busy "$port"; then
        fatal "$dockhand_port_invalid"
    fi
fi

docker volume create dockhand_data >/dev/null || fatal "$dockhand_volume_failed"
docker run -d \
    --name dockhand \
    --restart unless-stopped \
    -p "$port":3000 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v dockhand_data:/app/data \
    "$DOCKHAND_IMAGE" || fatal "$dockhand_run_failed"

zeninf "$dockhand_done"
xdg-open "http://localhost:$port" &>/dev/null &
