#!/bin/bash
# name: mergerfs
# version: 1.0
# description: mergerfs_desc
# icon: archive.svg
# compat: debian, ubuntu, fedora, rhel, arch, cachy
# nocontainer
# repo: https://github.com/trapexit/mergerfs

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

: "${mfs_title:=mergerfs}"
: "${mfs_branches_text:=Folders to pool, separated by ':'. Wildcards are allowed, e.g. /mnt/disk* or /mnt/disk1:/mnt/disk2}"
: "${mfs_branches_invalid:=No valid folders matched. Mount your drives first, then run this again.}"
: "${mfs_mount_text:=Folder where the pool will be mounted:}"
: "${mfs_mount_invalid:=Invalid mount point. It must be an absolute path outside the pooled folders, and empty if it already exists.}"
: "${mfs_mount_used:=This mount point is already configured in /etc/fstab.}"
: "${mfs_options_text:=mergerfs options (leave the default unless you know you need something else):}"
: "${mfs_options_invalid:=Options cannot contain spaces.}"
: "${mfs_confirm:=The following line will be added to /etc/fstab and mounted now. Continue?}"
: "${mfs_mount_failed:=Mounting failed. /etc/fstab was restored to its previous state.}"
: "${mfs_done:=Your pool is mounted at}"
: "${mfs_install_failed:=mergerfs was not found after installation.}"
: "${mfs_fstab_failed:=Failed to write /etc/fstab.}"

MFS_DEFAULT_BRANCHES="/mnt/disk*"
MFS_DEFAULT_MOUNT="/srv/mergerfs"
# upstream recommendation for Linux 6.6+ (mergerfs quickstart)
MFS_DEFAULT_OPTIONS="cache.files=off,category.create=pfrd,func.getattr=newest,dropcacheonclose=false"

sudo_rq

mfs_install () {
    command -v mergerfs &>/dev/null && return 0
    if is_debian || is_ubuntu || is_arch || is_cachy; then
        # Debian/Ubuntu repositories; AUR on Arch-based systems
        pkg_install fuse3 mergerfs
    elif is_fedora; then
        pkg_install fuse3
        pkg_fromrelease https://github.com/trapexit/mergerfs "mergerfs-*.fc$(rpm -E %fedora).*.rpm"
    elif is_rhel; then
        pkg_install fuse3
        pkg_fromrelease https://github.com/trapexit/mergerfs "mergerfs-*.el$(rpm -E %rhel).*.rpm"
    fi
    command -v mergerfs &>/dev/null || fatal "$mfs_install_failed"
}

mfs_trim () {
    local v="$1"
    v="${v#"${v%%[![:space:]]*}"}"
    printf '%s' "${v%"${v##*[![:space:]]}"}"
}

mfs_ask_branches () {
    local input spec path
    local -a parts=() matches=()
    local -A seen_dir=()
    input=$(userinput --title "$mfs_title" --text "$mfs_branches_text" --default "$MFS_DEFAULT_BRANCHES") || exit 100
    input=$(mfs_trim "$input")
    [[ -n "$input" && "$input" != *[[:space:]]* && "$input" != *'#'* ]] || fatal "$mfs_branches_invalid"
    IFS=':' read -r -a parts <<< "$input"
    MFS_DIRS=()
    for spec in "${parts[@]}"; do
        [[ "$spec" == /* ]] || fatal "$mfs_branches_invalid"
        matches=()
        # expand the glob now to check it matches something; fstab keeps the glob itself
        while IFS= read -r path; do
            [ -d "$path" ] && matches+=("${path%/}")
        done < <(compgen -G "$spec")
        (( ${#matches[@]} > 0 )) || fatal "$mfs_branches_invalid ($spec)"
        for path in "${matches[@]}"; do
            # a repeated spec would duplicate branches in the fstab line
            [[ -n "${seen_dir[$path]:-}" ]] && continue
            seen_dir[$path]=1
            MFS_DIRS+=("$path")
        done
    done
    MFS_BRANCHES="$input"
}

mfs_ask_mount () {
    local input dir
    input=$(userinput --title "$mfs_title" --text "$mfs_mount_text" --default "$MFS_DEFAULT_MOUNT") || exit 100
    input=$(mfs_trim "$input")
    [ "$input" != "/" ] && input="${input%/}"
    [[ "$input" == /?* && "$input" != *[[:space:]]* && "$input" != *'#'* ]] || fatal "$mfs_mount_invalid"
    case "$input" in
        /bin|/boot|/dev|/etc|/home|/lib|/lib64|/mnt|/opt|/proc|/root|/run|/sbin|/srv|/sys|/tmp|/usr|/var|/boot/*|/etc/*|/proc/*|/sys/*|/usr/*|/dev/*)
            fatal "$mfs_mount_invalid" ;;
    esac
    for dir in "${MFS_DIRS[@]}"; do
        if [[ "$input" == "$dir" || "$input" == "$dir"/* || "$dir" == "$input"/* ]]; then
            fatal "$mfs_mount_invalid"
        fi
    done
    if [ -e "$input" ]; then
        [ -d "$input" ] || fatal "$mfs_mount_invalid"
        [ -z "$(ls -A "$input" 2>/dev/null)" ] || fatal "$mfs_mount_invalid"
    fi
    # an active mount would be shadowed by the pool on top of it
    if mountpoint -q "$input"; then
        fatal "$mfs_mount_invalid"
    fi
    if awk -v m="$input" '$1 !~ /^#/ && $2 == m { found=1 } END { exit !found }' /etc/fstab; then
        fatal "$mfs_mount_used"
    fi
    MFS_MOUNT="$input"
}

mfs_ask_options () {
    local input
    input=$(userinput --title "$mfs_title" --text "$mfs_options_text" --default "$MFS_DEFAULT_OPTIONS") || exit 100
    input=$(mfs_trim "$input")
    input="${input:-$MFS_DEFAULT_OPTIONS}"
    [[ "$input" != *[[:space:]]* && "$input" != *'#'* ]] || fatal "$mfs_options_invalid"
    MFS_OPTIONS="$input"
}

mfs_fstab_line () {
    local dir opts="$MFS_OPTIONS" fstype="mergerfs" ver
    # mergerfs < 2.41 has no own mount helper and rejects nofail/x-systemd.*;
    # mounting through mount.fuse3 (fuse.mergerfs) filters them out
    ver=$(mergerfs --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -n1)
    # some distro builds report "vunknown"; ask the package manager instead
    [ -n "$ver" ] || ver=$({ dpkg-query -W -f='${Version}' mergerfs || rpm -q --qf '%{VERSION}' mergerfs || pacman -Q mergerfs; } 2>/dev/null \
        | grep -oE '[0-9]+\.[0-9]+' | head -n1)
    if [ -z "$ver" ] || (( ${ver%%.*} < 2 )) || { (( ${ver%%.*} == 2 )) && (( 10#${ver#*.} < 41 )); }; then
        fstype="fuse.mergerfs"
    fi
    # do not block boot if a drive is missing; order the pool after every
    # branch that a fstab entry mounts (a no-op for plain directories)
    [[ ",$opts," == *,nofail,* ]] || opts+=",nofail"
    for dir in "${MFS_DIRS[@]}"; do
        opts+=",x-systemd.requires-mounts-for=$dir"
    done
    MFS_LINE="$MFS_BRANCHES $MFS_MOUNT $fstype $opts 0 0"
}

mfs_install
mfs_ask_branches
mfs_ask_mount
mfs_ask_options
mfs_fstab_line
question "$mfs_title" "$mfs_confirm\n\n$MFS_LINE" 480 300 || exit 100

prep_dir "$MFS_MOUNT"
prep_edit /etc/fstab
printf '%s\n' "$MFS_LINE" | sudo_ tee -a /etc/fstab >/dev/null || fatal "$mfs_fstab_failed"
is_systemd && sudo_ systemctl daemon-reload
if ! sudo_ mount "$MFS_MOUNT"; then
    sudo_ cp -f /etc/fstab.bak /etc/fstab
    is_systemd && sudo_ systemctl daemon-reload
    fatal "$mfs_mount_failed"
fi
zeninf "$mfs_done $MFS_MOUNT"
