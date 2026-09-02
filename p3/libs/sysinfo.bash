# --- System Information Fetching ---

sysdetect() {
    source /etc/os-release || die "Failed to fetch OS information"
}
sysdetect_once() { [[ -n ${ID:-} ]] || sysdetect; }

is_arch() { sysdetect_once && [[ ("$ID" =~ arch || "$ID" == "artix" || "$ID_LIKE" =~ arch) && "$ID" != "cachyos" ]]; }
is_cachy() { sysdetect_once && [[ "$ID" == "cachyos" ]]; }
is_fedora() { sysdetect_once && [[ "$ID" == "fedora" || ("$ID_LIKE" =~ "fedora" && "$ID" != "almalinux") ]] && [ ! -f /run/ostree-booted ]; }
is_ostree() { sysdetect_once && [[ ("$ID" == "fedora" || "$ID" == "rhel" || "$ID_LIKE" =~ "fedora" || "$ID_LIKE" =~ "rhel" || "$ID_LIKE" =~ "centos") ]] && command -v rpm-ostree &>/dev/null && [ -f /run/ostree-booted ]; }
is_debian() { sysdetect_once && [[ ("$ID" == "debian" || "$ID" == "deepin" || "$ID_LIKE" =~ debian) && ! ($ID == ubuntu || $ID_LIKE =~ ubuntu) ]]; }
is_ubuntu() { sysdetect_once && [[ "$ID" == "ubuntu" || "$ID_LIKE" =~ "ubuntu" ]]; }
is_suse() {
    suse_leap=""
    sysdetect_once 
    if [[ "$ID" == "suse" || "$ID" == "opensuse" || "$ID_LIKE" =~ "suse" ]]; then
        { [ "$ID" = "opensuse-leap" ] || [[ "$VERSION_ID" =~ ^[0-9]+\.[0-9]+$ ]]; } && suse_leap="1"
        [ "$ID" = "opensuse-tumbleweed" ] && suse_tumbleweed="1"
        return 0
    else
        return 1
    fi
}
is_solus() { sysdetect_once && [[ "$ID" == "solus" ]]; }
is_zorin() { sysdetect_once && [[ "$ID" == "zorin" ]]; }
is_rhel() { sysdetect_once && [[ ("$ID" == "rhel" || "$ID" == "centos" || "$ID" == "almalinux" || "$ID_LIKE" =~ "rhel") ]] && [ ! -f /run/ostree-booted ] && [[ "$ID" != "nobara" ]]; }
is_deepin() { sysdetect_once && [[ "$ID" == "deepin" ]]; }
is_manjaro() { sysdetect_once && [[ "$ID" == "manjaro" || "$ID_LIKE" =~ "manjaro" ]]; }

is_systemd() { [[ $(ps -p 1 -o comm= || readlink /sbin/init) =~ "systemd" ]]; }

# GPU and compute feature detection
is_nvidia() {
    local nvidiaGPU=$(lspci | grep -i 'nvidia')
    if [[ -n "$nvidiaGPU" ]]; then
        return 0
    else
        return 1
    fi
}

is_intel() {
    local dev modalias
    unset intel_arc INTEL_XE_SYSFS
    for dev in /sys/bus/pci/devices/*; do
        [[ -r "$dev/vendor" && -r "$dev/class" && -r "$dev/modalias" ]] || continue
        [[ "$(<"$dev/vendor")" == "0x8086" ]] || continue
        [[ "$(<"$dev/class")" == 0x03* ]] || continue
        intelGPU="yes"
        modalias=$(<"$dev/modalias")
        # Check whether the currently installed kernel's xe module explicitly supports this PCI device, fixes #1069
        if modprobe -R "$modalias" 2>/dev/null | grep -qx 'xe'; then
            intel_arc="yes"
            INTEL_XE_SYSFS="$dev"
        fi
    done
    [[ -n "$intelGPU" ]]
}
is_icr_capable() {
    is_intel || return 1
    [[ -n "$intel_arc" ]] || return 1
}

is_amd() {
    local amdGPU
    amdGPU=$(lspci | grep -Ei 'vga|3d|display' | grep -Ei 'amd|radeon')
    [[ -n "$amdGPU" ]]
}
amd_dgpu() {
    local dev drm vram
    for dev in /sys/bus/pci/devices/*; do
        [[ -r "$dev/vendor" && -r "$dev/class" ]] || continue
        [[ "$(<"$dev/vendor")" == "0x1002" ]] || continue
        [[ "$(<"$dev/class")" == 0x03* ]] || continue
        for drm in "$dev"/drm/card*; do
            [[ -r "$drm/device/mem_info_vram_total" ]] || continue
            vram=$(<"$drm/device/mem_info_vram_total")
            # dGPUs have substantial dedicated VRAM.
            if (( vram >= 2073741824 )); then
                return 0
            fi
        done
    done
    return 1
}
rocm_apu() {
    local cpu model
    cpu=$(awk -F ': ' '/model name/ {print $2; exit}' /proc/cpuinfo)
    [[ "$cpu" == *"AMD Ryzen"* ]] || return 1
    if [[ "$cpu" == *"Ryzen AI "* ]]; then
        return 0
    fi
    if [[ "$cpu" =~ Ryzen[[:space:]].*([0-9]{4}) ]]; then
        model="${BASH_REMATCH[1]}"
        if (( 10#$model >= 8000 )); then
            case "$cpu" in
                *U*|*H*)
                    return 0
                    ;;
            esac
        fi
    fi
    return 1
}
is_rocm_capable() {
    is_amd || return 1
    { amd_dgpu || rocm_apu; } || return 1
}

# other features and quirks
has_rebar() {
    local pci size unit
    while read -r pci; do
        while read -r size unit; do
            case "$unit" in
                GB)
                    return 0
                    ;;
                MB)
                    (( size > 256 )) && return 0
                    ;;
            esac
        done < <(
            sudo lspci -vv -s "$pci" 2>/dev/null |
            sed -nE 's/.*current size: ([0-9]+)(MB|GB).*/\1 \2/p'
        )
    done < <(
        lspci -D |
        awk '/VGA compatible controller|3D controller/ {print $1}'
    )
    return 1
}
is_hybridgpu() {
    if is_nvidia && ( is_intel || is_amd ); then
        return 0
    else
        return 1
    fi
}