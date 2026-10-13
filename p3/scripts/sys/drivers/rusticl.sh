#!/bin/bash
# name: RustiCL
# description: rusticl_desc
# icon: device.svg
# reboot: yes
# gpu: Amd, Intel, Rusticl, !rocm
# compat: !steamos

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

# Resolve's DaVinciBox workflow installs the runtime inside the Fedora container.
if [[ -n "${RUSTICL_CONTAINER:-}" ]]; then
    [[ "$RUSTICL_CONTAINER" == davincibox ]] || exit 1
    distrobox enter "$RUSTICL_CONTAINER" -- bash -c '
        sudo dnf install -y mesa-libOpenCL clinfo || exit 1
        icd=$(find /etc/OpenCL/vendors /usr/share/OpenCL/vendors -name "*rusticl*.icd" -print -quit 2>/dev/null)
        [[ -n "$icd" && -r "$icd" ]] || exit 1
        printf "%s\n" "export RUSTICL_ENABLE=radeonsi" | sudo tee /etc/profile.d/linuxtoys-rusticl.sh >/dev/null || exit 1
        devices=$(RUSTICL_ENABLE=radeonsi OCL_ICD_VENDORS="$icd" clinfo -l) || exit 1
        printf "%s\n" "$devices"
        grep -q "Device #" <<< "$devices" || exit 1
    ' || exit 1
    exit 0
fi

rusticl_in() {
    if is_debian || is_ubuntu; then
        pkg_install mesa-opencl-icd clinfo
    elif is_fedora || is_rhel || is_ostree; then
        pkg_install mesa-libOpenCL clinfo
    elif is_suse; then
        pkg_install Mesa-libRusticlOpenCL clinfo
    elif is_arch || is_cachy; then
        pkg_install opencl-mesa clinfo
    elif is_solus; then
        # Solus builds Rusticl as part of mesalib; ocl-icd alone is only a loader.
        pkg_install mesalib ocl-icd clinfo
    else
        nonfatal "$msg077"
        return 1
    fi
}

# Enable both backends on hybrid AMD/Intel systems.
backends=""
if is_amd; then
    backends=radeonsi
fi
if is_intel; then
    backends="${backends:+$backends,}iris"
fi
if [[ -z "$backends" ]]; then
    nonfatal "$msg077"
    exit 1
fi
sudo_rq
rusticl_in || exit 1

# Some distros install ICDs under /usr/share rather than /etc.
icd=$(find /etc/OpenCL/vendors /usr/share/OpenCL/vendors -name '*rusticl*.icd' -print -quit 2>/dev/null)
if [[ -z "$icd" || ! -r "$icd" ]]; then
    nonfatal "The installed Mesa package does not provide a Rusticl OpenCL ICD."
    exit 1
fi

# Replace our setting on repeated runs; preserve unrelated environment settings.
# Remove the Rusticl-only loader override used by older LinuxToys installers,
# so other OpenCL implementations remain available on hybrid systems.
prep_edit /etc/environment
sudo sed -i -E '/^[[:space:]]*(export[[:space:]]+)?RUSTICL_ENABLE[[:space:]]*=/d; /^[[:space:]]*OCL_ICD_VENDORS=["\x27]?\/etc\/OpenCL\/vendors\/rusticl\.icd["\x27]?[[:space:]]*$/d' /etc/environment || exit 1
printf 'RUSTICL_ENABLE=%s\n' "$backends" | sudo tee -a /etc/environment >/dev/null || exit 1
# Use the new setting immediately for verification; desktop sessions pick it up at login.
export RUSTICL_ENABLE="$backends"
if [[ "${OCL_ICD_VENDORS:-}" == /etc/OpenCL/vendors/rusticl.icd ]]; then
    unset OCL_ICD_VENDORS
fi
devices=$(OCL_ICD_VENDORS="$icd" clinfo -l) || exit 1
printf '%s\n' "$devices"
if ! grep -q "Device #" <<< "$devices"; then
    nonfatal "Rusticl is installed but does not expose an OpenCL device. Check the Mesa version and GPU permissions."
    exit 1
fi
if ! clinfo_chk; then
    fatal "$nocl"
fi
zeninf "$msg036"
