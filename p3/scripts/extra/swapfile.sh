#!/bin/bash
# name: swapfile
# version: 1.0
# description: swapfile_desc
# icon: swapfile.svg
# compat: ubuntu, debian, arch, fedora, rhel, suse, gregos
# noconfirm: yes
# nocontainer

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

# Return 0 when the host is configured for hibernation (suspend-to-disk in
# active use). Mere kernel capability does not count — every desktop kernel
# ships it — so the host must not have hibernation disabled at runtime and
# must actually have a resume target configured (kernel command line or the
# Debian/Ubuntu initramfs resume file): a host that never resumes has no use
# for a RAM-sized swapfile.
#
# The probe paths default to the live procfs/sysfs locations; the
# SWAPFILE_TEST_* variables exist only so test harnesses can feed fake
# trees without touching the host.
hibernation_enabled () {
    local power_state="${SWAPFILE_TEST_POWER_STATE:-/sys/power/state}"
    local power_disk="${SWAPFILE_TEST_POWER_DISK:-/sys/power/disk}"
    local cmdline="${SWAPFILE_TEST_CMDLINE:-/proc/cmdline}"
    local sleep_conf="${SWAPFILE_TEST_SLEEP_CONF:-/etc/systemd/sleep.conf}"
    local sleep_conf_dir="${SWAPFILE_TEST_SLEEP_CONF_D:-/etc/systemd/sleep.conf.d}"
    local resume_conf="${SWAPFILE_TEST_RESUME_CONF:-/etc/initramfs-tools/conf.d/resume}"
    local conf_file

    # The kernel must expose suspend-to-disk at all.
    if ! { [ -r "$power_state" ] && grep -qw disk "$power_state" 2>/dev/null; }; then
        return 1
    fi

    # Kernel-level kill switch: the nohibernate boot parameter.
    if [ -r "$power_disk" ] && grep -q '\[disabled\]' "$power_disk" 2>/dev/null; then
        return 1
    fi

    # systemd-level kill switch: AllowHibernation=no in sleep.conf or a
    # sleep.conf.d drop-in.
    for conf_file in "$sleep_conf" "$sleep_conf_dir"/*.conf; do
        [ -r "$conf_file" ] || continue
        if grep -Eisq '^[[:space:]]*AllowHibernation[[:space:]]*=[[:space:]]*(no|false|0|off)([[:space:]]|$)' "$conf_file"; then
            return 1
        fi
    done

    # Enabled in practice: a resume target is configured on the kernel
    # command line (all major bootloaders)...
    if [ -r "$cmdline" ] && grep -Eq '(^|[[:space:]])resume=' "$cmdline" 2>/dev/null; then
        return 0
    fi
    # ...or in the Debian/Ubuntu initramfs resume configuration (RESUME=none
    # explicitly opts out, an empty RESUME= configures nothing).
    if [ -r "$resume_conf" ] \
        && grep -Eisq '^[[:space:]]*RESUME[[:space:]]*=[[:space:]]*[^[:space:]]' "$resume_conf" \
        && ! grep -Eisq '^[[:space:]]*RESUME[[:space:]]*=[[:space:]]*none([[:space:]]|$)' "$resume_conf"; then
        return 0
    fi

    return 1
}

# Determine the swapfile size in GiB and store it in SWAP_SIZE_GIB: total
# RAM + 4 GiB when the host is configured for hibernation (the saved memory
# image must fit into swap), the historical 10 GiB default otherwise — and
# never smaller than that default. Falls back to the default with a warning
# when the installed memory cannot be measured. The result is stored in a
# variable instead of being printed because the warning dialog can echo to
# stdout and would pollute command substitution.
compute_swap_size () {
    SWAP_SIZE_GIB=10

    hibernation_enabled || return 0

    local meminfo="${SWAPFILE_TEST_MEMINFO:-/proc/meminfo}"
    local mem_kb mem_gib
    # `|| true` keeps an unreadable/unavailable meminfo from aborting the
    # script under the set -e some runners use; the regex below then routes
    # the empty result into the warning fallback.
    mem_kb=$(awk '/^MemTotal:/{print $2; exit}' "$meminfo" 2>/dev/null || true)
    if [[ "$mem_kb" =~ ^[0-9]+$ ]] && [ "$mem_kb" -gt 0 ]; then
        # Round the installed memory up to whole GiB, then add the margin.
        mem_gib=$((( mem_kb + 1048575 ) / 1048576 + 4))
        if [ "$mem_gib" -gt "$SWAP_SIZE_GIB" ]; then
            SWAP_SIZE_GIB=$mem_gib
        fi
    else
        zenwrn "Could not determine the total RAM; using the default 10 GiB swapfile size.\nHibernation may fail if the swapfile ends up smaller than RAM."
    fi
    return 0
}

# create swap at specified location
create_swap () {
    local location=$1
    # Remove trailing slash to avoid double slashes in paths
    location="${location%/}"

    compute_swap_size

    if [ "$(findmnt -n -o FSTYPE "$location")" = "btrfs" ]; then
        sudo_rq
        sudo btrfs subvolume create "$location/swap"
        sudo btrfs filesystem mkswapfile --size "${SWAP_SIZE_GIB}g" --uuid clear "$location/swap/swapfile"
        sudo swapon "$location/swap/swapfile"
        echo "# swapfile" | sudo tee -a /etc/fstab
        echo "$location/swap/swapfile none swap defaults 0 0" | sudo tee -a /etc/fstab
        fix_selinux_context "$location/swap/swapfile"
        swapfile_created btrfs "$location/swap/swapfile"
        zeninf "Swapfile creation successful."
        if hibernation_enabled; then
            zenwrn "Hibernation is enabled on this system: for hibernation to use this swapfile, point the resume= kernel parameter at it and set resume_offset to its file offset."
        fi
        return 0
    else
        sudo_rq
        sudo mkswap -U clear --size "${SWAP_SIZE_GIB}G" --file "$location/swapfile"
        sudo swapon "$location/swapfile"
        echo "# swapfile" | sudo tee -a /etc/fstab
        echo "$location/swapfile none swap defaults 0 0" | sudo tee -a /etc/fstab
        fix_selinux_context "$location/swapfile"
        swapfile_created regular "$location/swapfile"
        zeninf "Swapfile creation successful."
        if hibernation_enabled; then
            zenwrn "Hibernation is enabled on this system: for hibernation to use this swapfile, point the resume= kernel parameter at it and set resume_offset to its file offset."
        fi
        return 0
    fi
}

# Check for existing active swap
ACTIVE_SWAP=$(swapon --show 2>/dev/null | tail -n +2)
if [ -n "$ACTIVE_SWAP" ]; then
    zenwrn "Swap already enabled in your system:\n$ACTIVE_SWAP"
    exit 100
elif is_gregos; then
    create_swap "/var"
    info "$finishmsg"
else
    # menu
    while true; do
        CHOICE=$(radioselect --no-default --title "Swapfile Creator" --text "Create swapfile on:" \
            "/ (root)" \
            "/home (home)" \
            "Custom path..." \
            "Cancel") || exit 100

        case $CHOICE in
        "/ (root)") create_swap "/" && break;;
        "/home (home)") create_swap "/home" && break;;
        "Custom path...")
            CUSTOM_PATH=$(userinput --title "Swapfile Creator" --text "Enter the mount point path for swapfile:\n(e.g., /var, /opt, or any other mount point)")
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
