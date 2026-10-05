#!/usr/bin/env bash

# allow Steam flatpak to access storage drives/partitions
if flatpak list --app --columns=application | grep -qx 'com.valvesoftware.Steam'; then
    while IFS= read -r storage_drive; do
        storage_drive="$(printf '%b' "$storage_drive")"
        if mkdir -p "$storage_drive/steam"; then
            flatpak_override user fs "$storage_drive/steam" com.valvesoftware.Steam
        fi
    done < <(
        findmnt -rn --raw -o TARGET,SOURCE,FSTYPE |
        awk '
            $2 ~ "^/dev/" &&
            $3 != "squashfs" &&
            $1 != "/" &&
            $1 != "/home" &&
            $1 != "/boot" &&
            $1 !~ "^/boot/efi(/|$)" &&
            $1 !~ "^/efi(/|$)" {
                print $1
            }
        '
    )
fi
