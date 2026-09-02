# --- Bootloader & INITRAMFS Management ---

# bootloader update
bootloader_upd() {
    if ! is_ostree; then
        local exit_status
        if is_fedora || is_suse || is_rhel; then
            sudo grub2-mkconfig -o /boot/grub2/grub.cfg || die "Unable to update bootloader"
            _append_transmap "updated bootloader"
        elif is_arch || is_cachy; then
            if command -v limine-mkinitcpio >/dev/null 2>&1; then
                sudo limine-mkinitcpio || die "Unable to update bootloader"
            elif command -v sdboot-manage >/dev/null 2>&1 &&
                bootctl is-installed >/dev/null 2>&1; then
                sudo sdboot-manage gen || die "Unable to update bootloader"
            elif command -v grub-mkconfig >/dev/null 2>&1; then
                sudo grub-mkconfig -o /boot/grub/grub.cfg || die "Unable to update bootloader"
            elif command -v bootctl >/dev/null 2>&1 && bootctl is-installed >/dev/null 2>&1; then
                sudo bootctl update || die "Unable to update bootloader"
            else
                die "Unable to determine installed bootloader"
            fi
            _append_transmap "updated bootloader"
        elif is_ubuntu; then
            sudo update-grub || fatal "Unable to update bootloader"
            _append_transmap "updated bootloader"
        elif is_debian; then 
            {
                sudo update-grub && exit_status=0 || {
                    if sudo bootctl is-installed >/dev/null 2>&1; then
                        sudo bootctl update
                        exit_status=0
                    else
                        exit_status=1
                    fi
                }
            } 
            [ "$exit_status" -eq 0 ] || fatal "Unable to update bootloader"
            _append_transmap "updated bootloader"
        elif is_solus; then
            { sudo clr-boot-manager update || sudo grub-mkconfig -o /boot/grub/grub.cfg; } || fatal "Unable to update bootloader"
            _append_transmap "updated bootloader"
        fi
    else
        return 0
    fi
}

initramfs_upd() {
    if is_debian || is_ubuntu; then
        sudo update-initramfs -u -k all || die "Failed to update initramfs"
    elif is_arch || is_cachy; then
        if command -v dracut &> /dev/null; then
            sudo dracut -f --regenerate-all || die "Failed to update dracut"
        else
            sudo mkinitcpio -P || die "Failed to update mkinitcpio"
        fi
    elif is_fedora || is_suse || is_rhel ; then
        sudo dracut -f --regenerate-all || die "Failed to update dracut"
    fi
    _append_transmap "updated initramfs"
}

kargs_upd() {
    for arg in "$@"; do
        sudo rpm-ostree kargs --append="$arg" || fatal "Failed to update rpm-ostree kargs"
        _append_transmap "updated kargs $arg"
    done
}

grubbyargs_upd () {
    if ! which grubby &> /dev/null; then
        pkg_install grubby
    fi
    for arg in "$@"; do
        sudo grubby --args="$arg" --update-kernel ALL || fatal "Failed to update grubby kargs"
        _append_transmap "updated grubby kargs $arg"
    done
}

secureboot_check() {
    local _ubuntumok=0
    for arg in "$@"; do
        if [[ "$arg" == "--ubuntumok" ]]; then
            _ubuntumok=1
        fi
    done
    sudo mokutil --sb-state | grep -q "SecureBoot enabled" || return 0
    if is_fedora || is_rhel || is_ostree; then
        call_script modsign
    elif is_ubuntu; then
        { sudo mokutil --test-key /var/lib/shim-signed/mok/MOK.der | grep -q "not enrolled" && \
            { sudo update-secureboot-policy --enroll-key || die "Failed to update secure boot policy"; }; } || true
    elif is_debian; then
        if [ "$_ubuntumok" -eq 1 ] && [ ! -f /var/lib/shim-signed/mok/MOK.der ]; then
            prep_dir /var/lib/shim-signed/mok/
            openssl req -nodes -new -x509 -newkey rsa:2048 -keyout MOK.priv -outform DER -out MOK.der -days 36500 -subj "/CN=LinuxToys/"
            openssl x509 -inform der -in MOK.der -out MOK.pem
            sudo mokutil --import /var/lib/shim-signed/mok/MOK.der || die "Failed to create ubuntu-like key"
        else
            { sudo mokutil --test-key /var/lib/dkms/mok.pub | grep -q "not enrolled" && \
                { sudo mokutil --import /var/lib/dkms/mok.pub || die "Failed to update secure boot policy"; }; } || true
        fi
    fi
}