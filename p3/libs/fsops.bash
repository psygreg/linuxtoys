# --- Filesystem Operations ---

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

copy_() {
    local -a flags=()
    local -a args=()
    for arg in "$@"; do
        if [[ "$arg" == -* ]]; then
            flags+=("$arg")
        else
            args+=("$arg")
        fi
    done
    
    local dest="${args[-1]}"
    local -a sources=("${args[@]:0:${#args[@]}-1}")
    for src in "${sources[@]}"; do
        [ -e "$src" ] || fatal "Source $src not found"
        { cp "${flags[@]}" "$src" "$dest" 2>/dev/null || sudo_ cp "${flags[@]}" "$src" "$dest"; } || fatal "Failed to copy $src to $dest"
    done
}

move_() {
    local -a flags=()
    local -a args=()
    for arg in "$@"; do
        if [[ "$arg" == -* ]]; then
            flags+=("$arg")
        else
            args+=("$arg")
        fi
    done
    
    local dest="${args[-1]}"
    local -a sources=("${args[@]:0:${#args[@]}-1}")
    for src in "${sources[@]}"; do
        [ -e "$src" ] || fatal "Source $src not found"
        { mv "${flags[@]}" "$src" "$dest" 2>/dev/null || sudo_ mv "${flags[@]}" "$src" "$dest"; } || fatal "Failed to move $src to $dest"
    done
}

# --- Distrobox Filesystem Operations ---

_distrobox_fs_record() {
    local action="$1"
    local container="$2"
    local path="$3"
    local container64 path64

    container64=$(printf '%s' "$container" | base64 -w0) || fatal "Failed to encode Distrobox container name"
    path64=$(printf '%s' "$path" | base64 -w0) || fatal "Failed to encode Distrobox path"
    _append_transmap "distrobox-fs $action $container64 $path64"
}

distrobox_prep_create() {
    local container="$1"
    shift

    for target in "$@"; do
        if distrobox enter "$container" -- test -f "$target"; then
            _append_transmap "WARN: unexpected $target already exists in Distrobox $container"
            distrobox_prep_edit "$container" "$target"
            continue
        fi

        distrobox enter "$container" -- sh -c 'mkdir -p "$(dirname "$1")" && touch "$1"' sh "$target" 2>/dev/null \
            || distrobox enter "$container" -- sudo sh -c 'mkdir -p "$(dirname "$1")" && touch "$1"' sh "$target" \
            || fatal "Failed to create $target in Distrobox $container"
        _distrobox_fs_record created "$container" "$target"
    done
}

distrobox_prep_edit() {
    local container="$1"
    shift

    for target in "$@"; do
        if ! distrobox enter "$container" -- test -f "$target"; then
            _append_transmap "WARN: expected $target not found in Distrobox $container"
            distrobox_prep_create "$container" "$target"
            continue
        fi

        distrobox_copy_ "$container" -a "$target" "$target.bak"
        _distrobox_fs_record edited "$container" "$target"
    done
}

distrobox_prep_rm() {
    local container="$1"
    shift

    for target in "$@"; do
        if ! distrobox enter "$container" -- test -e "$target" && \
           ! distrobox enter "$container" -- test -d "$target"; then
            _append_transmap "WARN: expected $target not found in Distrobox $container"
            continue
        fi

        distrobox_move_ "$container" "$target" "$target.bak"
        _distrobox_fs_record removed "$container" "$target"
    done
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

distrobox_copy_() {
    local container="$1"
    shift
    local -a flags=()
    local -a args=()
    local arg

    for arg in "$@"; do
        if [[ "$arg" == -* ]]; then
            flags+=("$arg")
        else
            args+=("$arg")
        fi
    done

    (( ${#args[@]} >= 2 )) || fatal "distrobox_copy_: source and destination required"
    local dest="${args[-1]}"
    local -a sources=("${args[@]:0:${#args[@]}-1}")
    local src

    for src in "${sources[@]}"; do
        distrobox enter "$container" -- test -e "$src" \
            || fatal "Source $src not found in Distrobox $container"
        distrobox enter "$container" -- cp "${flags[@]}" "$src" "$dest" 2>/dev/null \
            || distrobox enter "$container" -- sudo cp "${flags[@]}" "$src" "$dest" \
            || fatal "Failed to copy $src to $dest in Distrobox $container"
    done
}

distrobox_move_() {
    local container="$1"
    shift
    local -a flags=()
    local -a args=()
    local arg

    for arg in "$@"; do
        if [[ "$arg" == -* ]]; then
            flags+=("$arg")
        else
            args+=("$arg")
        fi
    done

    (( ${#args[@]} >= 2 )) || fatal "distrobox_move_: source and destination required"
    local dest="${args[-1]}"
    local -a sources=("${args[@]:0:${#args[@]}-1}")
    local src

    for src in "${sources[@]}"; do
        distrobox enter "$container" -- test -e "$src" \
            || fatal "Source $src not found in Distrobox $container"
        distrobox enter "$container" -- mv "${flags[@]}" "$src" "$dest" 2>/dev/null \
            || distrobox enter "$container" -- sudo mv "${flags[@]}" "$src" "$dest" \
            || fatal "Failed to move $src to $dest in Distrobox $container"
    done
}
