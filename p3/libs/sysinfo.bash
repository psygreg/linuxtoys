# --- System Information Fetching ---

sysdetect() {
    source /etc/os-release || die "Failed to fetch OS information"
}
sysdetect_once() { [[ -n ${ID:-} ]] || sysdetect; }

is_steamos() { sysdetect_once && [[ "$ID" == "steamos" ]]; }
is_arch() { sysdetect_once && [[ ("$ID" =~ arch || "$ID" == "artix" || "$ID_LIKE" =~ arch) && "$ID" != "cachyos" && "$ID" != "steamos" ]]; }
is_cachy() { sysdetect_once && [[ "$ID" == "cachyos" ]]; }
is_fedora() { sysdetect_once && [[ "$ID" == "fedora" || ("$ID_LIKE" =~ "fedora" && "$ID" != "almalinux") ]] && [ ! -f /run/ostree-booted ]; }
is_ostree() { sysdetect_once && [[ ("$ID" == "fedora" || "$ID" == "rhel" || "$ID_LIKE" =~ "fedora" || "$ID_LIKE" =~ "rhel" || "$ID_LIKE" =~ "centos") ]] && command -v rpm-ostree &>/dev/null && [ -f /run/ostree-booted ]; }
is_debian() { sysdetect_once && [[ ("$ID" == "debian" || "$ID" == "deepin" || "$ID_LIKE" =~ "debian") && ! ("$ID" == "ubuntu" || "$ID_LIKE" =~ "ubuntu") ]]; }
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
# GCN/Polaris/Vega PCI IDs from Linux amdgpu_drv.c (2026-10-09).
# https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/amd/amdgpu/amdgpu_drv.c
# LinuxToys policy, not an official ROCm support matrix. Keep both lists in sync.
amd_legacy_gpu() {
    local device_id="${1,,}"
    device_id="${device_id#0x}"
    case "$device_id" in
        # TAHITI
        6780|6784|6788|678a|6790|6791|6792|6798|\
        6799|679a|679b|679e|679f)
            return 0 ;;
        # PITCAIRN
        6800|6801|6802|6806|6808|6809|6810|6811|\
        6816|6817|6818|6819)
            return 0 ;;
        # OLAND
        6600|6601|6602|6603|6604|6605|6606|6607|\
        6608|6610|6611|6613|6617|6620|6621|6623|\
        6631)
            return 0 ;;
        # VERDE
        6820|6821|6822|6823|6824|6825|6826|6827|\
        6828|6829|682a|682b|682c|682d|682f|6830|\
        6831|6835|6837|6838|6839|683b|683d|683f)
            return 0 ;;
        # HAINAN
        6660|6663|6664|6665|6667|666f)
            return 0 ;;
        # KAVERI
        1304|1305|1306|1307|1309|130a|130b|130c|\
        130d|130e|130f|1310|1311|1312|1313|1315|\
        1316|1317|1318|131b|131c|131d)
            return 0 ;;
        # BONAIRE
        6640|6641|6646|6647|6649|664d|6650|6651|\
        6658|665c|665d|665f)
            return 0 ;;
        # HAWAII
        67a0|67a1|67a2|67a8|67a9|67aa|67b0|67b1|\
        67b8|67b9|67ba|67be)
            return 0 ;;
        # KABINI
        9830|9831|9832|9833|9834|9835|9836|9837|\
        9838|9839|983a|983b|983c|983d|983e|983f)
            return 0 ;;
        # MULLINS
        9850|9851|9852|9853|9854|9855|9856|9857|\
        9858|9859|985a|985b|985c|985d|985e|985f)
            return 0 ;;
        # TOPAZ
        6900|6901|6902|6903|6907)
            return 0 ;;
        # TONGA
        6920|6921|6928|6929|692b|692f|6930|6938|\
        6939|693b)
            return 0 ;;
        # FIJI
        7300|730f)
            return 0 ;;
        # CARRIZO
        9870|9874|9875|9876|9877)
            return 0 ;;
        # STONEY
        98e4)
            return 0 ;;
        # POLARIS11
        67e0|67e3|67e8|67eb|67ef|67ff|67e1|67e7|\
        67e9)
            return 0 ;;
        # POLARIS10
        67c0|67c1|67c2|67c4|67c7|67d0|67d4|67df|\
        67c8|67c9|67ca|67cc|67cf|6fdf)
            return 0 ;;
        # POLARIS12
        6980|6981|6985|6986|6987|698f|6995|6997|\
        699f)
            return 0 ;;
        # VEGAM
        694c|694e|694f)
            return 0 ;;
        # VEGA10
        6860|6861|6862|6863|6864|6867|6868|6869|\
        686a|686b|686c|686d|686e|686f|687f)
            return 0 ;;
        # VEGA12
        69a0|69a1|69a2|69a3|69af)
            return 0 ;;
        # VEGA20
        66a0|66a1|66a2|66a3|66a4|66a7|66af)
            return 0 ;;
        # RAVEN
        15dd|15d8)
            return 0 ;;
        # RENOIR
        15e7|1636|1638|164c)
            return 0 ;;
    esac
    return 1
}

amd_rocm_dgpu() {
    local dev drm vram device_id
    for dev in /sys/bus/pci/devices/*; do
        [[ -r "$dev/vendor" && -r "$dev/class" && -r "$dev/device" ]] || continue
        [[ "$(<"$dev/vendor")" == "0x1002" ]] || continue
        [[ "$(<"$dev/class")" == 0x03* ]] || continue
        device_id=$(<"$dev/device")
        amd_legacy_gpu "$device_id" && continue
        for drm in "$dev"/drm/card*; do
            [[ -r "$drm/device/mem_info_vram_total" ]] || continue
            vram=$(<"$drm/device/mem_info_vram_total")
            [[ "$vram" =~ ^[0-9]+$ ]] || continue
            if (( vram >= 2073741824 )); then
                return 0
            fi
        done
    done
    return 1
}

# Require an unblocked AMD GPU before applying the existing CPU-name APU heuristic.
amd_rocm_apu() {
    local dev device_id
    rocm_apu || return 1
    for dev in /sys/bus/pci/devices/*; do
        [[ -r "$dev/vendor" && -r "$dev/class" && -r "$dev/device" ]] || continue
        [[ "$(<"$dev/vendor")" == "0x1002" ]] || continue
        [[ "$(<"$dev/class")" == 0x03* ]] || continue
        device_id=$(<"$dev/device")
        amd_legacy_gpu "$device_id" || return 0
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
    { amd_rocm_dgpu || amd_rocm_apu; }
}

# Polaris 10/11/12/22, Vega 10 (56/64), Vega 20 (Radeon VII); mirror compat.py.
amd_rusticl_gpu() {
    local device_id="${1,,}"
    case "$device_id" in
        0x67e0|0x67e3|0x67e8|0x67eb|0x67ef|0x67ff|0x67e1|0x67e7|\
        0x67e9|0x67c0|0x67c1|0x67c2|0x67c4|0x67c7|0x67d0|0x67d4|\
        0x67df|0x67c8|0x67c9|0x67ca|0x67cc|0x67cf|0x6fdf|0x6980|\
        0x6981|0x6985|0x6986|0x6987|0x698f|0x6995|0x6997|0x699f|\
        0x694c|0x694e|0x694f|0x6860|0x6861|0x6862|0x6863|0x6864|\
        0x6867|0x6868|0x6869|0x686a|0x686b|0x686c|0x686d|0x686e|\
        0x686f|0x687f|0x66a0|0x66a1|0x66a2|0x66a3|0x66a4|0x66a7|\
        0x66af)
            return 0 ;;
    esac
    return 1
}
is_rusticl_capable() {
    local dev device_id
    for dev in /sys/bus/pci/devices/*; do
        [[ -r "$dev/vendor" && -r "$dev/class" && -r "$dev/device" ]] || continue
        [[ "$(<"$dev/vendor")" == "0x1002" ]] || continue
        [[ "$(<"$dev/class")" == 0x03* ]] || continue
        device_id=$(<"$dev/device")
        amd_rusticl_gpu "$device_id" && return 0
    done
    return 1
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
            sudo_ lspci -vv -s "$pci" 2>/dev/null |
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
