#!/bin/bash
# functions

# create swap on root
root_swap () {

    if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
        btrfs subvolume create /swap
        btrfs filesystem mkswapfile --size 8g --uuid clear /swap/swapfile
        swapon /swap/swapfile
        echo "# swapfile" | sudo tee -a /etc/fstab
        echo "/swap/swapfile none swap defaults 0 0" | sudo tee -a /etc/fstab
        title="Swapfile Creator"
        msg="Swapfile creation succesful."
        _msgbox_
        return 0
    else
        mkswap -U clear --size 8G --file /swapfile
        swapon /swapfile
        echo "# swapfile" | sudo tee -a /etc/fstab
        echo "/swapfile none swap defaults 0 0" | sudo tee -a /etc/fstab
        title="Swapfile Creator"
        msg="Swapfile creation succesful."
        _msgbox_
        return 0
    fi

}

# create swap on home
home_swap () {

    if [ "$(findmnt -n -o FSTYPE /home)" = "btrfs" ]; then
        sudo btrfs subvolume create /home/swap
        sudo btrfs filesystem mkswapfile --size 8g --uuid clear /home/swap/swapfile
        sudo swapon /home/swap/swapfile
        echo "# swapfile" | sudo tee -a /etc/fstab
        echo "/home/swap/swapfile none swap defaults 0 0" | sudo tee -a /etc/fstab
        title="Swapfile Creator"
        msg="Swapfile creation succesful."
        _msgbox_
        return 0
    else
        sudo mkswap -U clear --size 8G --file /home/swapfile
        sudo swapon /home/swapfile
        echo "# swapfile" | sudo tee -a /etc/fstab
        echo "/home/swapfile none swap defaults 0 0" | sudo tee -a /etc/fstab
        title="Swapfile Creator"
        msg="Swapfile creation succesful."
        _msgbox_
        return 0
    fi

}

if swapon --show | grep -q '^'; then
    title="Swapfile Creator"
    msg="Swap already enabled in your system."
    _msgbox_
    exit 0
else
    # menu
    while :; do

        CHOICE=$(whiptail --title "Swapfile Creator" --menu "Create swapfile on:" 25 78 16 \
            "0" "/ (root)" \
            "1" "/home (home)" \
            "2" "Cancel" 3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
            # Exit the script if the user presses Esc
            break
        fi

        case $CHOICE in
        0) root_swap && break;;
        1) home_swap && break;;
        2 | q) break ;;
        *) echo "Invalid Option" ;;
        esac
    done
fi