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