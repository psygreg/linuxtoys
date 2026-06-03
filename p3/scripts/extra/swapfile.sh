#!/bin/bash
# name: swapfile
# version: 1.0
# description: swapfile_desc
# icon: swapfile.svg
# compat: ubuntu, debian, arch, fedora, rhel
# noconfirm: yes
# nocontainer
# new

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"

fix_selinux_context () {
    local swapfile_path=$1
    
    # Check if semanage is available and SELinux is enabled
    if command -v semanage &> /dev/null && getenforce &> /dev/null; then
        if [ "$(getenforce)" != "Disabled" ]; then
            sudo semanage fcontext -a -t swapfile_t "$swapfile_path" 2>/dev/null
            sudo restorecon "$swapfile_path" 2>/dev/null
        fi
    fi
}

# create swap at specified location
create_swap () {
    local location=$1
    # Remove trailing slash to avoid double slashes in paths
    location="${location%/}"
    
    if [ "$(findmnt -n -o FSTYPE "$location")" = "btrfs" ]; then
        sudo_rq
        sudo btrfs subvolume create "$location/swap"
        sudo btrfs filesystem mkswapfile --size 10g --uuid clear "$location/swap/swapfile"
        sudo swapon "$location/swap/swapfile"
        echo "# swapfile" | sudo tee -a /etc/fstab
        echo "$location/swap/swapfile none swap defaults 0 0" | sudo tee -a /etc/fstab
        fix_selinux_context "$location/swap/swapfile"
        swapfile_created btrfs "$location/swap/swapfile"
        zeninf "Swapfile creation successful."
        return 0
    else
        sudo_rq
        sudo mkswap -U clear --size 10G --file "$location/swapfile"
        sudo swapon "$location/swapfile"
        echo "# swapfile" | sudo tee -a /etc/fstab
        echo "$location/swapfile none swap defaults 0 0" | sudo tee -a /etc/fstab
        fix_selinux_context "$location/swapfile"
        swapfile_created regular "$location/swapfile"
        zeninf "Swapfile creation successful."
        return 0
    fi
}

# Check for existing active swap
ACTIVE_SWAP=$(swapon --show 2>/dev/null | tail -n +2)
if [ -n "$ACTIVE_SWAP" ]; then
    zenwrn "Swap already enabled in your system:\n$ACTIVE_SWAP"
    exit 100
else
    # menu
    while true; do
        CHOICE=$(zenity --list --title "Swapfile Creator" --text "Create swapfile on:" \
            --column "Options" \
            "/ (root)" \
            "/home (home)" \
            "Custom path..." \
            "Cancel" \
            --height 330 --width 300)

        if [ $? -ne 0 ]; then
            exit 100
        fi

        case $CHOICE in
        "/ (root)") create_swap "/" && break;;
        "/home (home)") create_swap "/home" && break;;
        "Custom path...") 
            CUSTOM_PATH=$(zenity --entry --title "Swapfile Creator" --text "Enter the mount point path for swapfile:\n(e.g., /var, /opt, or any other mount point)")
            if [ $? -eq 0 ] && [ -n "$CUSTOM_PATH" ]; then
                if [ "$CUSTOM_PATH" = "/tmp" ] || [[ "$CUSTOM_PATH" == /tmp/* ]]; then
                    zenwrn "/tmp is not suitable for swapfile storage.\nPlease choose a different location."
                elif [ -d "$CUSTOM_PATH" ]; then
                    create_swap "$CUSTOM_PATH" && break
                else
                    zenwrn "Path does not exist: $CUSTOM_PATH"
                fi
            fi
            ;;
        "Cancel") exit 100 ;;
        *) echo "Invalid Option" ;;
        esac
    done
fi
    