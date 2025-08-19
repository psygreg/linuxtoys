#!/bin/bash
# name: swapfile
# version: 1.0
# description: swapfile_desc
# icon: swapfile.svg
# compat: ubuntu, debian, arch
# noconfirm: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# create swap on root
root_swap () {
    if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
        sudo_rq
        btrfs subvolume create /swap
        btrfs filesystem mkswapfile --size 8g --uuid clear /swap/swapfile
        swapon /swap/swapfile
        echo "# swapfile" | sudo tee -a /etc/fstab
        echo "/swap/swapfile none swap defaults 0 0" | sudo tee -a /etc/fstab
        zeninf "Swapfile creation successful."
        return 0
    else
        sudo_rq
        sudo mkswap -U clear --size 8G --file /swapfile
        sudo swapon /swapfile
        echo "# swapfile" | sudo tee -a /etc/fstab
        echo "/swapfile none swap defaults 0 0" | sudo tee -a /etc/fstab
        zeninf "Swapfile creation successful."
        return 0
    fi
}

# create swap on home
home_swap () {
    if [ "$(findmnt -n -o FSTYPE /home)" = "btrfs" ]; then
        sudo_rq
        sudo btrfs subvolume create /home/swap
        sudo btrfs filesystem mkswapfile --size 8g --uuid clear /home/swap/swapfile
        sudo swapon /home/swap/swapfile
        echo "# swapfile" | sudo tee -a /etc/fstab
        echo "/home/swap/swapfile none swap defaults 0 0" | sudo tee -a /etc/fstab
        zeninf "Swapfile creation successful."
        return 0
    else
        sudo_rq
        sudo mkswap -U clear --size 8G --file /home/swapfile
        sudo swapon /home/swapfile
        echo "# swapfile" | sudo tee -a /etc/fstab
        echo "/home/swapfile none swap defaults 0 0" | sudo tee -a /etc/fstab
        zeninf "Swapfile creation successful."
        return 0
    fi
}

if swapon --show | grep -q '^'; then
    nonfatal "Swap already enabled in your system."
    exit 0
else
    # menu
    while true; do
        CHOICE=$(zenity --list --title "Swapfile Creator" --text "Create swapfile on:" \
            --column "Options" \
            "/ (root)" \
            "/home (home)" \
            "Cancel" \
            --height 330 --width 300)

        if [ $? -ne 0 ]; then
            exit 100
        fi

        case $CHOICE in
        "/ (root)") root_swap && break;;
        "/home (home)") home_swap && break;;
        "Cancel") exit 100 ;;
        *) echo "Invalid Option" ;;
        esac
    done
fi
    