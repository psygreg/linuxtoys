#!/usr/bin/env bash

# allow Steam flatpak to access storage drives/partitions
if flatpak list --app --columns=application | grep -qx 'org.localsend.localsend_app'; then
    while IFS= read -r storage_drive; do
        flatpak_override user fs "$storage_drive" org.localsend.localsend_app
    done < <(list_storage_drives)
fi
