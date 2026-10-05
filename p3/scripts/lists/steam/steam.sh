#!/usr/bin/env bash

# allow Steam flatpak to access storage drives/partitions
if flatpak list --app --columns=application | grep -qx 'com.valvesoftware.Steam'; then
    while IFS= read -r storage_drive; do
        if mkdir -p "$storage_drive/steam"; then
            flatpak_override user fs "$storage_drive/steam" com.valvesoftware.Steam
        fi
    done < <(list_storage_drives)
fi
