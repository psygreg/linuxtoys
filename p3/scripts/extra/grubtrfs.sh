#!/bin/bash
# name: GRUB-btrfs
# version: 1.0
# description: grubtrfs_desc
# icon: grubtrfs.svg
# compat: ubuntu, debian, arch, fedora, suse, !deepin
# nocontainer
# repo: https://github.com/Antynea/grub-btrfs
# systemd: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

# check dependencies
dep_check () {
    grub_found=false
    if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        if dpkg -l | grep -qE 'grub-efi|grub-pc'; then
            grub_found=true
        fi
    elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
        if rpm -qa | grep -qE 'grub2-efi|grub2-pc'; then
            grub_found=true
        fi
    elif [[ "$ID_LIKE" == *suse* ]]; then
        if rpm -qa | grep -qE 'grub2-efi|grub2-pc'; then
            grub_found=true
        fi
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || \
         [[ "$ID_LIKE" == *arch* ]] || \
         [[ "$ID_LIKE" == *archlinux* ]]; then
        if pacman -Qi grub &>/dev/null; then
            grub_found=true
        fi
    fi
    if [ "$grub_found" = false ]; then
        die "No GRUB found."
    fi
    if is_fedora || is_suse; then
        pkg_install gawk inotify-tools make
    elif is_arch; then
        pkg_install gawk inotify-tools
    elif is_ubuntu || is_debian; then
        pkg_install gawk inotify-tools make
    fi
}

grub_btrfs_set_config () {
    local key="$1"
    local value="$2"
    local config="/etc/default/grub-btrfs/config"
    if grep -qE "^#?${key}=" "$config"; then
        sudo sed -Ei \
            "s|^#?${key}=.*|${key}=\"${value}\"|" \
            "$config"
    else
        echo "${key}=\"${value}\"" | sudo tee -a "$config" >/dev/null
    fi
}

# overlayfs setup
setup_mkinitcpio_overlay () {
    local config="/etc/mkinitcpio.conf"
    if ! grep -Eq '^HOOKS=.*\bgrub-btrfs-overlayfs\b' "$config"; then
        sudo sed -Ei \
            '/^[[:space:]]*HOOKS=/ s/\)[[:space:]]*$/ grub-btrfs-overlayfs)/' \
            "$config"
    fi
}
setup_dracut_overlay () {
    prep_dir /etc/dracut.conf.d
    echo 'add_dracutmodules+=" overlayfs "' |
        sudo tee /etc/dracut.conf.d/90-grub-btrfs-overlayfs.conf >/dev/null
    grub_btrfs_set_config \
        GRUB_BTRFS_SNAPSHOT_KERNEL_PARAMETERS \
        "rd.live.overlay.overlayfs=1"
}
setup_initramfs_tools_overlay () {
    prep_dir \
        /etc/initramfs-tools/hooks \
        /etc/initramfs-tools/scripts/local-bottom
    sudo tee /etc/initramfs-tools/hooks/grub-btrfs-overlayfs >/dev/null <<'EOF'
#!/bin/sh

PREREQ=""

prereqs()
{
    echo "$PREREQ"
}

case "$1" in
    prereqs)
        prereqs
        exit 0
        ;;
esac

. /usr/share/initramfs-tools/hook-functions

manual_add_modules overlay

exit 0
EOF
    sudo chmod 0755 \
        /etc/initramfs-tools/hooks/grub-btrfs-overlayfs
    sudo tee \
        /etc/initramfs-tools/scripts/local-bottom/grub-btrfs-overlayfs \
        >/dev/null <<'EOF'
#!/bin/sh

PREREQ=""

prereqs()
{
    echo "$PREREQ"
}

case "$1" in
    prereqs)
        prereqs
        exit 0
        ;;
esac

# Only modify root when this is a grub-btrfs snapshot boot.
grep -qw 'grub_btrfs_overlay=1' /proc/cmdline || exit 0

BASE=/run/grub-btrfs-overlay

mkdir -p "$BASE"

# The upper and work directories live entirely in RAM.
mount -t tmpfs \
    -o mode=0755 \
    grub-btrfs-overlay "$BASE" || exit 1

mkdir -p \
    "$BASE/lower" \
    "$BASE/upper" \
    "$BASE/work"

# /root is the real root filesystem mounted by initramfs-tools.
# Move the read-only snapshot out of the way.
mount --move /root "$BASE/lower" || exit 1

mkdir -p /root

# Expose a writable root without modifying the snapshot itself.
mount -t overlay overlay \
    -o "lowerdir=$BASE/lower,upperdir=$BASE/upper,workdir=$BASE/work" \
    /root || exit 1

exit 0
EOF
    sudo chmod 0755 /etc/initramfs-tools/scripts/local-bottom/grub-btrfs-overlayfs
    grub_btrfs_set_config \
        GRUB_BTRFS_SNAPSHOT_KERNEL_PARAMETERS \
        "grub_btrfs_overlay=1"
}
setup_snapshot_overlay () {
    if command -v mkinitcpio &>/dev/null && [ -f /etc/mkinitcpio.conf ]; then
        setup_mkinitcpio_overlay
    elif command -v dracut &>/dev/null; then
        setup_dracut_overlay
    elif command -v update-initramfs &>/dev/null && [ -d /etc/initramfs-tools ]; then
        setup_initramfs_tools_overlay
    else
        die "Unable to configure read-only snapshot booting: unsupported initramfs generator."
    fi
    initramfs_upd
}

setup_snapper () {
    pkg_install snapper
    if [ ! -f /etc/snapper/configs/root ]; then
        sudo snapper -c root create-config /
    fi
    sudo sed -i \
        's/^TIMELINE_CREATE=.*/TIMELINE_CREATE="no"/' \
        /etc/snapper/configs/root

    sudo sed -i \
        's/^NUMBER_LIMIT=.*/NUMBER_LIMIT="5"/' \
        /etc/snapper/configs/root

    sudo sed -i \
        's/^NUMBER_LIMIT_IMPORTANT=.*/NUMBER_LIMIT_IMPORTANT="5"/' \
        /etc/snapper/configs/root

    sudo sed -i \
        's/^NUMBER_CLEANUP=.*/NUMBER_CLEANUP="yes"/' \
        /etc/snapper/configs/root

    sudo sed -i \
        's/^EMPTY_PRE_POST_CLEANUP=.*/EMPTY_PRE_POST_CLEANUP="yes"/' \
        /etc/snapper/configs/root
    sysd_enable snapper-boot.timer
    sysd_enable snapper-cleanup.timer
    sysd_start snapper-cleanup.timer
}

install_grub_btrfs () {
    is_fedora && { 
        [ -e /boot/grub ] || \
            sudo ln -s /boot/grub2 /boot/grub || die "Failed to create symlink for /boot/grub2"
        [ -e /usr/bin/grub-script-check ] || \
            sudo ln -s /usr/bin/grub2-script-check /usr/bin/grub-script-check || die "Failed to create symlink for /usr/bin/grub2-script-check"
    } || true
    if is_arch; then
        pkg_install grub-btrfs
    else
        prep_tmp_noram
        git clone https://github.com/Antynea/grub-btrfs.git
        cd grub-btrfs || die "Failed to fetch grub-btrfs"
        sudo make install
    fi
}

grubtrfs_in () {
    setup_snapper
    install_grub_btrfs
    if is_fedora || is_suse; then
        sudo sed -i \
            's|^GRUB_BTRFS_MKCONFIG=.*|GRUB_BTRFS_MKCONFIG=/sbin/grub2-mkconfig|' \
            /etc/default/grub-btrfs/config

        sudo sed -i \
            's|^GRUB_BTRFS_GRUB_DIRNAME=.*|GRUB_BTRFS_GRUB_DIRNAME="/boot/grub2"|' \
            /etc/default/grub-btrfs/config

        sudo sed -i \
            's|^GRUB_BTRFS_SCRIPT_CHECK=.*|GRUB_BTRFS_SCRIPT_CHECK=grub2-script-check|' \
            /etc/default/grub-btrfs/config
    fi
    setup_snapshot_overlay
    bootloader_upd
    sysd_enable grub-btrfsd
    sysd_start grub-btrfsd
}

if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
    askpass
    dep_check
    grubtrfs_in
    info "$rebootmsg"
else
    die "$msg031"
fi