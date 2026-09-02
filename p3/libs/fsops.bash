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
        || { sudo mkdir -p "$(dirname "$target")" && sudo touch "$target"; } \
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
            { mkdir -p "$dir" 2>/dev/null || sudo mkdir -p "$dir"; } || fatal "Failed to create $dir"
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
        { cp "${flags[@]}" "$src" "$dest" 2>/dev/null || sudo cp "${flags[@]}" "$src" "$dest"; } || fatal "Failed to copy $src to $dest"
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
        { mv "${flags[@]}" "$src" "$dest" 2>/dev/null || sudo mv "${flags[@]}" "$src" "$dest"; } || fatal "Failed to move $src to $dest"
    done
}