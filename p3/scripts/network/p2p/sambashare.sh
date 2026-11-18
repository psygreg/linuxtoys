#!/bin/bash
# name: Samba Share
# version: 1.0
# description: sambashare_desc
# icon: p2p.svg
# compat: debian, ubuntu, fedora, rhel, arch, cachy, suse
# nocontainer
# systemd: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

: "${smb_title:=Samba Share}"
: "${smb_name_text:=Name of the network share (letters, numbers, '-' and '_' only):}"
: "${smb_name_invalid:=Invalid share name. Use up to 32 letters, numbers, '-' or '_'.}"
: "${smb_name_taken:=A share with this name already exists in /etc/samba/smb.conf.}"
: "${smb_path_text:=Full path of the folder to share:}"
: "${smb_path_invalid:=Invalid folder. Use an absolute path that is not a system directory.}"
: "${smb_mode_text:=Who can access this share?}"
: "${smb_mode_private:=Only me, with a Samba password}"
: "${smb_mode_guest_ro:=Anyone on the network, read-only}"
: "${smb_mode_guest_rw:=Anyone on the network, read and write}"
: "${smb_guest_rw_warn:=Anyone on your local network will be able to change and delete files in this folder without a password. Continue?}"
: "${smb_pass_text:=Choose a Samba password for your user. You will use it to access the share from other devices.}"
: "${smb_pass_empty:=The Samba password cannot be empty.}"
: "${smb_conf_invalid:=The new Samba configuration is invalid. The previous configuration was restored.}"
: "${smb_done:=Share created. Access it from other devices at:}"

# overridable so the flow can be exercised against a scratch config in tests
SMB_CONF="${SMB_CONF:-/etc/samba/smb.conf}"

: "${USER:=$(id -un 2>/dev/null)}"

sudo_rq

# Ask everything before touching the system, so a cancelled run leaves
# no Samba package or configuration behind.
smb_ask_name () {
    local name
    name=$(userinput --title "$smb_title" --text "$smb_name_text" --default "Share") || exit 100
    name="${name//[[:space:]]/}"
    if [[ ! "$name" =~ ^[A-Za-z0-9_-]{1,32}$ ]] || [[ "${name,,}" =~ ^(global|homes|printers)$ ]]; then
        fatal "$smb_name_invalid"
    fi
    if grep -qiE "^[[:space:]]*\[${name}\][[:space:]]*$" "$SMB_CONF" 2>/dev/null; then
        fatal "$smb_name_taken"
    fi
    SHARE_NAME="$name"
}

smb_ask_path () {
    local path
    path=$(userinput --title "$smb_title" --text "$smb_path_text" --default "$HOME/Public") || exit 100
    # trim surrounding whitespace and trailing slashes
    path="${path#"${path%%[![:space:]]*}"}"
    path="${path%"${path##*[![:space:]]}"}"
    while [[ "$path" != "/" && "$path" == */ ]]; do
        path="${path%/}"
    done
    if [[ "$path" != /* ]] || [[ "$path" == *$'\n'* ]] || [[ "$path" =~ (^|/)\.\.?(/|$) ]]; then
        fatal "$smb_path_invalid"
    fi
    # resolve symlinks so a folder link cannot smuggle a system directory in
    path=$(realpath -m -- "$path" 2>/dev/null) || fatal "$smb_path_invalid"
    # home locations differ per distro layout (/home is a symlink to /var/home
    # on immutable systems, systemd-homed lives under /var/home): accept the
    # user's own home under either form and keep other users' homes off limits
    local home_resolved
    home_resolved=$(realpath -m -- "$HOME" 2>/dev/null) || home_resolved="$HOME"
    case "$path" in
        /|/bin|/bin/*|/boot|/boot/*|/dev|/dev/*|/etc|/etc/*|/efi|/efi/*|/lib|/lib/*|/lib32|/lib32/*|/lib64|/lib64/*|/libx32|/libx32/*|/proc|/proc/*|/root|/root/*|/run|/run/*|/sbin|/sbin/*|/sys|/sys/*|/tmp|/tmp/*|/usr|/usr/*|/var|/var/tmp|/var/tmp/*|/var/log|/var/log/*|/var/lib|/var/lib/*|/var/cache|/var/cache/*|/var/spool|/var/spool/*|/var/backups|/var/backups/*|/var/roothome|/var/roothome/*)
            fatal "$smb_path_invalid" ;;
    esac
    case "$path" in
        # other users' homes are off limits; the user's own home is fine,
        # either as typed or through the distro layout that resolves to it
        "$HOME"/*|"$home_resolved"/*) ;;
        "$HOME"|"$home_resolved") fatal "$smb_path_invalid" ;;
        /home|/home/*|/var/home|/var/home/*) fatal "$smb_path_invalid" ;;
    esac
    if [ ! -d "$path" ]; then
        if [[ "$path" == "$HOME"/* || "$path" == "$home_resolved"/* ]]; then
            mkdir -p "$path" || fatal "Failed to create $path"
            _append_transmap "created $path"
        else
            prep_dir "$path"
            sudo_ chown "$USER": "$path" || fatal "Failed to set ownership of $path"
        fi
    fi
    SHARE_PATH="$path"
}

smb_ask_mode () {
    local mode
    mode=$(radioselect --title "$smb_title" --text "$smb_mode_text" \
        "$smb_mode_private" "$smb_mode_guest_ro" "$smb_mode_guest_rw") || exit 100
    case "$mode" in
        "$smb_mode_private") SHARE_MODE="private" ;;
        "$smb_mode_guest_ro") SHARE_MODE="guest_ro" ;;
        "$smb_mode_guest_rw")
            question "$smb_title" "$smb_guest_rw_warn" || exit 100
            SHARE_MODE="guest_rw" ;;
        *) exit 100 ;;
    esac
}

smb_conf_ensure () {
    [ -f "$SMB_CONF" ] && return 0
    # Arch ships no default smb.conf; give it a minimal one
    prep_create "$SMB_CONF"
    sudo_ tee "$SMB_CONF" >/dev/null <<'EOF'
[global]
   workgroup = WORKGROUP
   server string = %h
   server role = standalone server
   map to guest = Bad User
   log file = /var/log/samba/%m.log
   max log size = 1000
EOF
}

# add the user to the Samba password database if not there yet
smb_user_ensure () {
    sudo_ pdbedit -L 2>/dev/null | cut -d: -f1 | grep -qx "$USER" && return 0
    local pass
    if _zenity_can_run; then
        pass=$(_zenity_run --password --title "$smb_title" --text "$smb_pass_text") || exit 100
    else
        printf '%s\n' "$smb_pass_text" >&2
        pass=$(askpass password "$smb_title") || exit 100
    fi
    [ -n "$pass" ] || fatal "$smb_pass_empty"
    printf '%s\n%s\n' "$pass" "$pass" | sudo_ smbpasswd -s -a "$USER" >/dev/null || fatal "Failed to set the Samba password"
    unset pass
    _append_transmap "smbpasswd added $USER"
}

# guest shares need unknown users mapped to the guest account
smb_guest_ensure () {
    sudo_ testparm -s "$SMB_CONF" --parameter-name="map to guest" 2>/dev/null | grep -qi "bad user" && return 0
    if grep -qiE '^[[:space:]]*map to guest' "$SMB_CONF"; then
        sudo_ sed -i -E 's/^([[:space:]]*)map to guest.*/\1map to guest = Bad User/I' "$SMB_CONF"
    else
        # a [global] section may also appear after shares; Samba merges them
        printf '[global]\n   map to guest = Bad User\n' | sudo_ tee -a "$SMB_CONF" >/dev/null
    fi
    sudo_ testparm -s "$SMB_CONF" --parameter-name="map to guest" 2>/dev/null | grep -qi "bad user" \
        || nonfatal "Failed to enable guest access in $SMB_CONF"
}

smb_write_share () {
    local section
    section="
[$SHARE_NAME]
   path = $SHARE_PATH
   browseable = yes
   create mask = 0644
   directory mask = 0755"
    case "$SHARE_MODE" in
        private)
            section+="
   valid users = $USER
   read only = no" ;;
        guest_ro)
            section+="
   guest ok = yes
   read only = yes
   force user = $USER" ;;
        guest_rw)
            section+="
   guest ok = yes
   read only = no
   force user = $USER" ;;
    esac
    printf '%s\n' "$section" | sudo_ tee -a "$SMB_CONF" >/dev/null || fatal "Failed to write $SMB_CONF"
    if ! sudo_ testparm -s "$SMB_CONF" >/dev/null 2>&1; then
        sudo_ cp -f "$SMB_CONF.bak" "$SMB_CONF"
        fatal "$smb_conf_invalid"
    fi
}

# label the folder for Samba on SELinux systems (Fedora, RHEL)
smb_selinux () {
    command -v getenforce &>/dev/null || return 0
    [ "$(getenforce 2>/dev/null)" = "Disabled" ] && return 0
    if [[ "$SHARE_PATH" == /home/* || "$SHARE_PATH" == /var/home/* ]]; then
        sudo_ setsebool -P samba_enable_home_dirs on || nonfatal "Failed to enable the samba_enable_home_dirs SELinux boolean"
    elif command -v semanage &>/dev/null; then
        sudo_ semanage fcontext -a -t samba_share_t "${SHARE_PATH}(/.*)?" 2>/dev/null \
            || sudo_ semanage fcontext -m -t samba_share_t "${SHARE_PATH}(/.*)?" 2>/dev/null
        sudo_ restorecon -R "$SHARE_PATH" || nonfatal "Failed to set the SELinux label on $SHARE_PATH"
    else
        sudo_ chcon -R -t samba_share_t "$SHARE_PATH" || nonfatal "Failed to set the SELinux label on $SHARE_PATH"
    fi
}

smb_firewall () {
    if command -v firewall-cmd &>/dev/null && sudo_ firewall-cmd --state &>/dev/null; then
        { sudo_ firewall-cmd --permanent --add-service=samba && sudo_ firewall-cmd --reload; } \
            || nonfatal "Failed to allow Samba through firewalld"
    elif command -v ufw &>/dev/null && sudo_ ufw status 2>/dev/null | grep -q "Status: active"; then
        sudo_ ufw allow samba >/dev/null 2>&1 || sudo_ ufw allow Samba >/dev/null 2>&1 \
            || nonfatal "Failed to allow Samba through ufw"
    fi
}

smb_services () {
    local smb_svc="smb" nmb_svc="nmb"
    if is_debian || is_ubuntu; then
        smb_svc="smbd"
        nmb_svc="nmbd"
    fi
    sysd_enable "$smb_svc"
    sudo_ systemctl restart "$smb_svc" || fatal "Failed to start $smb_svc"
    # NetBIOS name service is optional; do not fail if it is missing or masked
    if systemctl list-unit-files "$nmb_svc.service" &>/dev/null; then
        sudo_ systemctl enable --now "$nmb_svc" &>/dev/null && _append_transmap "sysd enabled $nmb_svc"
    fi
}

smb_ask_name
smb_ask_path
smb_ask_mode
# install samba (ships smbpasswd, pdbedit and testparm on every supported distro)
pkg_install samba
smb_conf_ensure
[ "$SHARE_MODE" = "private" ] && smb_user_ensure
prep_edit "$SMB_CONF"
[[ "$SHARE_MODE" == guest_* ]] && smb_guest_ensure
smb_write_share
smb_selinux
smb_firewall
smb_services

host="$(hostname 2>/dev/null || cat /etc/hostname)"
zeninf "$smb_done\n\nWindows: \\\\\\\\${host}\\\\${SHARE_NAME}\nLinux / macOS: smb://${host}/${SHARE_NAME}"
