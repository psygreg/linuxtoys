# --- Miscellaneous ---

# shell change
shell_change() {
    sudo chsh -s "$*" || fatal "Failed to change shell: $*"
    _append_transmap "chsh $*"
}

# distrobox container
distrobox_created() {
    _append_transmap "distrobox $*"
}

# rclone mountpoint
rclone_mount() {
    local remote="$1"
    local mount_point="$2"
    if [[ "$remote" != *:* ]]; then
        remote="${remote}:"
    fi
    rclone mount "$remote" "$mount_point" --daemon || fatal "Failed to create rclone mountpoint"
    _append_transmap "rclone mounted $remote at $mount_point" 
}

# swapfile creation
swapfile_created () {
    _append_transmap "swapfile $*"
}

# flatpak overrides
flatpak_override () {
    local scope pretype type setting target
    scope="$1"
    pretype="$2"
    setting="$3"
    target="$4"

    case "$pretype" in
        fs) type="filesystem" ;;
        name) type="talk-name" ;;
        dbus) type="talk-dbus" ;;
        share|env|runtime|device|socket|filesystem|talk-name|talk-dbus) type="$pretype" ;;
        *) die "Invalid override type" ;;
    esac

    flatpak info "$target" &>/dev/null || die "Invalid override target"

    if [ "$scope" = "system" ]; then
        askpass
        sudo -i sh -c "'flatpak override --$scope --$type=$setting $target'"
    elif [ "$scope" = "user" ]; then
        flatpak override --"$scope" --"$type"="$setting" "$target"
    else
        die "Invalid override scope"
    fi

    _append_transmap "override $scope $type $setting $target"
}