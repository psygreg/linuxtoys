#!/bin/bash
# name: Snapcraft
# version: 1.0
# description: snap_desc
# icon: snap.png
# reboot: yes
# repo: https://snapcraft.io
# compat: !ostree, !steamos
# systemd: yes
# nocontainer

snap_packages=("snapd")
is_fedora && snap_packages+=("snapd-selinux")
askpass

if is_suse; then
    if grep -qi tumbleweed /etc/os-release; then
        snap_repo="openSUSE_Tumbleweed"
    elif grep -qi slowroll /etc/os-release; then
        snap_repo="openSUSE_Slowroll"
    else
        snap_repo="openSUSE_Leap_$(. /etc/os-release; printf '%s' "$VERSION_ID")"
    fi

    if ! zypper lr -a 2>/dev/null | awk -F'|' '{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2}' | grep -Fxq snappy; then
        sudo_ zypper addrepo --refresh "https://download.opensuse.org/repositories/system:/snappy/$snap_repo" snappy || die "Failed to add the Snap repository"
    fi

    sudo_ zypper --gpg-auto-import-keys refresh || die "Failed to refresh the Snap repository"
    sudo_ zypper dup -y --from snappy || die "Failed to update packages from the Snap repository"
fi

pkg_install "${snap_packages[@]}"

if is_suse; then
    { sysd_enable snapd && sysd_start snapd; } || die "Failed to enable snapd"
    { sysd_enable snapd.apparmor && sysd_start snapd.apparmor; } || die "Failed to enable snapd AppArmor support"
elif is_solus; then
    sudo_ ln -s /var/lib/snapd/snap /snap
fi
