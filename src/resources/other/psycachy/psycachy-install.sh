#!/bin/bash
releases=$(curl -s "https://api.github.com/repos/psygreg/linux-psycachy/releases")
lts_tag=$(echo "$releases" | jq -r '.[].tag_name' | grep -i '^LTS-' | sort -Vr | head -n 1)
std_tag=$(echo "$releases" | jq -r '.[].tag_name' | grep -i '^STD-' | sort -Vr | head -n 1)
kver_lts="${lts_tag#LTS-}"
kver_psycachy="${std_tag#STD-}"
_kv_url_latest=$(curl -s https://www.kernel.org | grep -A 1 'id="latest_link"' | awk 'NR==2' | grep -oP 'href="\K[^"]+')
# extract only the version number
_kv_latest=$(echo $_kv_url_latest | grep -oP 'linux-\K[^"]+')
# remove the .tar.xz extension
_kv_latest=$(basename $_kv_latest .tar.xz)

# psycachy standard edition
psycachy_std () {

    local psycachy_tag="$kver_psycachy"
    cd $HOME
    wget "https://github.com/psygreg/linux-cachyos-deb/releases/download/${psycachy_tag}/linux-headers-psycachy_${psycachy_tag}-1_amd64.deb"
    wget "https://github.com/psygreg/linux-cachyos-deb/releases/download/${psycachy_tag}/linux-image-psycachy_${psycachy_tag}-1_amd64.deb"
    wget "https://github.com/psygreg/linux-cachyos-deb/releases/download/${psycachy_tag}/linux-libc-dev_${psycachy_tag}-1_amd64.deb"
    sleep 1
    sudo dpkg -i linux-image-psycachy_${psycachy_tag}-1_amd64.deb linux-headers-psycachy_${psycachy_tag}-1_amd64.deb linux-libc-dev_${psycachy_tag}-1_amd64.deb || exit 10
    cd $HOME/.local
    sleep 1
    wget -O "kernelsetting" https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/kernelsetting-defaults
    cd $HOME
    sleep 1
    rm linux-image-psycachy_${psycachy_tag}-1_amd64.deb
    rm linux-headers-psycachy_${psycachy_tag}-1_amd64.deb
    rm linux-libc-dev_${psycachy_tag}-1_amd64.deb
    # sign kernel image for secure boot
    if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
        bash <(curl -s https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/secureboot/create-key.sh) --linuxtoys
    fi

}

# psycachy lts edition
psycachy_lts () {

    local psycachy_tag="$kver_lts"
    cd $HOME
    wget "https://github.com/psygreg/linux-cachyos-deb/releases/download/${psycachy_tag}/linux-headers-psycachy_${psycachy_tag}-1_amd64.deb"
    wget "https://github.com/psygreg/linux-cachyos-deb/releases/download/${psycachy_tag}/linux-image-psycachy_${psycachy_tag}-1_amd64.deb"
    wget "https://github.com/psygreg/linux-cachyos-deb/releases/download/${psycachy_tag}/linux-libc-dev_${psycachy_tag}-1_amd64.deb"
    sleep 1
    sudo dpkg -i linux-image-psycachy-lts_${psycachy_tag}-1_amd64.deb linux-headers-psycachy-lts_${psycachy_tag}-1_amd64.deb linux-libc-dev_${psycachy_tag}-1_amd64.deb || exit 10
    cd $HOME/.local
    sleep 1
    wget -O "kernelsetting-lts" https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/kernelsetting-defaults
    cd $HOME
    sleep 1
    rm linux-image-psycachy-lts_${psycachy_tag}-1_amd64.deb
    rm linux-headers-psycachy-lts_${psycachy_tag}-1_amd64.deb
    rm linux-libc-dev_${psycachy_tag}-1_amd64.deb
    # sign kernel image for secure boot
    if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
        bash <(curl -s https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/secureboot/create-key.sh) --lts
    fi

}

# check if any argument was passed
if [ -n "$1" ]; then
    case "$1" in
    --lts | -l)
        psycachy_lts
        exit 0
        ;;
    --std | -s)
        psycachy_std
        exit 0
        ;;
    esac
fi

# menu
while :; do

    CHOICE=$(whiptail --title "Kernel Version" --menu "Select:" 25 78 16 \
        "Standard" "$kver_psycachy" \
        "LTS" "$kver_lts" \
        "Latest" "$_kv_latest" \
        "Cancel" "" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        exit 2
    fi

    case $CHOICE in
    Standard) psycachy_std && exit 0 ;;
    LTS) psycachy_lts && exit 0 ;;
    Latest) bash <(curl -s https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/src/cachyos-deb.sh) && exit 1 ;;
    Cancel | q) exit 2 ;;
    *) echo "Invalid Option" ;;
    esac
done
