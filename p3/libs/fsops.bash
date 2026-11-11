
prep_edit() {
    for target in "$@"; do
        [ -f "$target" ] || { _append_transmap "WARN: expected $target not found"; prep_create "$target"; continue; }
        copy_ -r "$target" "$target".bak
        _append_transmap "edited $target"
    done
}
prep_create() {
    for target in "$@"; do
        [ ! -f "$target" ] || { _append_transmap "WARN: unexpected $target already exists"; prep_edit "$target"; continue; }
        { mkdir -p "$(dirname "$target")" && touch "$target"; } 2>/dev/null \
        || { sudo_ mkdir -p "$(dirname "$target")" && sudo_ touch "$target"; } \
        || fatal "Failed to create: $target"
        _append_transmap "created $target"
    done
}

prep_rm() {
    for target in "$@"; do
        { [ -f "$target" ] || [ -d "$target" ]; } || { _append_transmap "WARN: expected $target not found"; continue; }
        move_ "$target" "$target".bak
        _append_transmap "removed $target"
    done
}

prep_tmp() {
    [ -d "$TEMPDIR" ] && [ -w "$TEMPDIR" ] && cd "$TEMPDIR" || \
        { mkdir -p /tmp/linuxtoys && [ -w /tmp/linuxtoys ] && cd /tmp/linuxtoys && TEMPDIR="/tmp/linuxtoys"; } || \
        { TEMPDIR="$HOME/.cache/linuxtoys/tmp" && { [ -n "$TRANSMAP_PATH" ] || TRANSMAP_PATH="$TEMPDIR/transmap"; } && prep_tmp_noram; }
}
prep_tmp_noram () {
    { mkdir -p "$HOME/.cache/linuxtoys/tmp" && cd "$HOME/.cache/linuxtoys/tmp"; } || fatal "Failed to create tempdir"
    [ -z "$TRANSMAP_CALL" ] && _append_transmap "tmpdir_noram $HOME/.cache/linuxtoys/tmp"
}

prep_dir() {
    for dir in "$@"; do
        if [ ! -d "$dir" ]; then
            { mkdir -p "$dir" 2>/dev/null || sudo_ mkdir -p "$dir"; } || fatal "Failed to create $dir"
            _append_transmap "created $dir"
        fi
    done
}
prep_dir_edit() {
    for dir in "$@"; do
        [ -d "$dir" ] || { _append_transmap "WARN: unexpected $dir doesnt exist"; prep_dir "$dir"; continue; }
        copy_ -r "$dir" "$dir.bak"
        _append_transmap "edited $dir"
    done
}

# Shared plumbing for the reversible copy_/move_ transfers (native hosts and
# Distrobox containers): splits leading option flags from positional args, then
# runs the per-source fallback chain. Only the tool (cp/mv), the execution
# scope and the failure labels differ per public wrapper.
_transfer_split_args() {
    _TRANSFER_FLAGS=()
    _TRANSFER_ARGS=()
    local arg
    for arg in "$@"; do
        if [[ "$arg" == -* ]]; then
            _TRANSFER_FLAGS+=("$arg")
        else
            _TRANSFER_ARGS+=("$arg")
        fi
    done
}

_transfer() {
    local tool="$1" label="$2"
    shift 2
    _transfer_split_args "$@"

    local dest="${_TRANSFER_ARGS[-1]}"
    local -a sources=("${_TRANSFER_ARGS[@]:0:${#_TRANSFER_ARGS[@]}-1}")
    local src
    for src in "${sources[@]}"; do
        [ -e "$src" ] || fatal "Source $src not found"
        { "$tool" "${_TRANSFER_FLAGS[@]}" "$src" "$dest" 2>/dev/null || sudo_ "$tool" "${_TRANSFER_FLAGS[@]}" "$src" "$dest"; } || fatal "Failed to $label $src to $dest"
    done
}

copy_() {
    _transfer cp copy "$@"
}

move_() {
    _transfer mv move "$@"
}


_distrobox_fs_record() {
    local action="$1"
    local container="$2"
    local path="$3"
    local container64 path64

    container64=$(printf '%s' "$container" | base64 -w0) || fatal "Failed to encode Distrobox container name"
    path64=$(printf '%s' "$path" | base64 -w0) || fatal "Failed to encode Distrobox path"
    _append_transmap "distrobox-fs $action $container64 $path64"
}

distrobox_prep_dir() {
    local container="$1"
    shift

    for dir in "$@"; do
        if ! distrobox enter "$container" -- test -d "$dir"; then
            distrobox enter "$container" -- mkdir -p "$dir" 2>/dev/null \
                || distrobox enter "$container" -- sudo mkdir -p "$dir" \
                || fatal "Failed to create $dir in Distrobox $container"
            _distrobox_fs_record created "$container" "$dir"
        fi
    done
}

distrobox_prep_dir_edit() {
    local container="$1"
    shift

    for dir in "$@"; do
        if ! distrobox enter "$container" -- test -d "$dir"; then
            _append_transmap "WARN: unexpected $dir doesnt exist in Distrobox $container"
            distrobox_prep_dir "$container" "$dir"
            continue
        fi

        distrobox_copy_ "$container" -a "$dir" "$dir.bak"
        _distrobox_fs_record edited "$container" "$dir"
    done
}

_distrobox_transfer() {
    local tool="$1" label="$2" container="$3"
    shift 3
    _transfer_split_args "$@"

    (( ${#_TRANSFER_ARGS[@]} >= 2 )) || fatal "$label: source and destination required"
    local dest="${_TRANSFER_ARGS[-1]}"
    local -a sources=("${_TRANSFER_ARGS[@]:0:${#_TRANSFER_ARGS[@]}-1}")
    local src
    for src in "${sources[@]}"; do
        distrobox enter "$container" -- test -e "$src" \
            || fatal "Source $src not found in Distrobox $container"
        distrobox enter "$container" -- "$tool" "${_TRANSFER_FLAGS[@]}" "$src" "$dest" 2>/dev/null \
            || distrobox enter "$container" -- sudo "$tool" "${_TRANSFER_FLAGS[@]}" "$src" "$dest" \
            || fatal "Failed to $label $src to $dest in Distrobox $container"
    done
}

distrobox_copy_() {
    local container="$1"
    shift
    _distrobox_transfer cp "distrobox_copy_" "$container" "$@"
}

distrobox_move_() {
    local container="$1"
    shift
    _distrobox_transfer mv "distrobox_move_" "$container" "$@"
}
