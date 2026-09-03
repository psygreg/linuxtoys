## LinuxToys optimizers library
source "$SCRIPT_DIR/libs/helpers.lib"

nvidia_ctkpatch () {
    if ! nvidia-smi >/dev/null 2>&1; then
        die "NVIDIA GPU is unavailable to the NVIDIA driver."
    fi
    local VAR_OUTPUT="/var/run/cdi/nvidia.yaml"
    local ETC_OUTPUT="/etc/cdi/nvidia.yaml"
    prep_create "$VAR_OUTPUT"
    prep_create "$ETC_OUTPUT"
    # ensure files can be created cleanly after adding to transmap
    sudo rm "$VAR_OUTPUT"
    sudo rm "$ETC_OUTPUT"
    sudo nvidia-ctk cdi generate --output="$VAR_OUTPUT" || die "failed to generate CDI spec on /var"
    sudo nvidia-ctk cdi generate --output="$ETC_OUTPUT" || die "failed to generate CDI spec on /etc"
    if systemctl list-unit-files | grep -q nvidia-cdi; then
        sysd_enable nvidia-cdi-refresh.path nvidia-cdi-refresh.service
        sysd_start nvidia-cdi-refresh.path nvidia-cdi-refresh.service
    fi
    sudo chmod a+r "$VAR_OUTPUT"
    sudo chmod a+r "$ETC_OUTPUT"
    if ! nvidia-ctk cdi list 2>/dev/null | grep -q '^nvidia.com/gpu=all$'; then
        die "NVIDIA CDI device nvidia.com/gpu=all is unavailable."
    fi
}

# legacy function call support - kept here so older code and local user scripts won't break

cachyos_sysd_lib () {
    call_script cachyconfs
}

sboost_lib () {
    call_script sboost
}

preempt_lib () {
    call_script preemptfedora
}

dsplitm_lib () {
    call_script dsplitm
}

psave_lib () {
    call_script psaver
}

earlyoom_lib () {
    call_script earlyoom
}

zswap_lib () {
    call_script zram
}

wayland_proton_lib () {
    call_script wayproton
}

intel_xe_lib () {
    call_script intelxe
}

free_mem_fix () {
    call_script minfreefix
}

dnsmasq_lib () {
    call_script dnsmasq
}

fix_intel_gtk () {
    call_script gtk-bmg-fix
}

pp_ondemand () {
    call_script ondemand
}