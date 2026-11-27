#!/usr/bin/env bash
# LinuxToys: expose the host's 32-bit graphics/compute drivers to Nix
# applications at /run/opengl-driver-32.
#
# NixOS builds two driver environments, /run/opengl-driver (64-bit) and
# /run/opengl-driver-32 (32-bit). On non-NixOS systems LinuxToys uses Home
# Manager for the 64-bit side; this helper supplies the missing 32-bit side
# from the host driver stack, so 32-bit Wine/Proton applications see the same
# kernel-matched drivers as 64-bit ones.
#
# The bundle is copied and rewritten because a tree of symlinks into /usr
# disappears inside Nix buildFHSEnv wrappers (they bind /run but replace /usr).
# It is bind-mounted read-only by a systemd service, and rebuilt when the host
# driver files change.
#
# This is a standalone helper, not a sourceable library. It lives under libs/
# (like gregos.bash) because it is an internal part of the Nix subsystem, not a
# catalog entry.

set -euo pipefail

bundle_root="${LINUXTOYS_NIX_GPU32_BUNDLE:-/var/lib/linuxtoys/nix-graphics-32}"
runtime="${LINUXTOYS_NIX_GPU32_RUNTIME:-/run/opengl-driver-32}"
runtime64="${LINUXTOYS_NIX_GPU64_RUNTIME:-/run/opengl-driver}"
service_name=linuxtoys-nix-graphics.service
service_path="${LINUXTOYS_NIX_GPU32_SERVICE:-/etc/systemd/system/${service_name}}"
script_path="${LINUXTOYS_NIX_GPU32_SCRIPT:-/usr/local/lib/linuxtoys/nix-gpu32}"
environment_file="${LINUXTOYS_NIX_GPU32_ENVIRONMENT:-/etc/environment}"
env_dir="${LINUXTOYS_NIX_GPU32_ENV_DIR:-/etc/environment.d}"
profile_file="${LINUXTOYS_NIX_GPU32_PROFILE:-/etc/profile.d/90-linuxtoys-nix-graphics.sh}"
vulkan_icd_dir="${LINUXTOYS_NIX_GPU32_VULKAN_ICD_DIR:-/usr/share/vulkan/icd.d}"

case "${runtime}" in
    /run/?*|/tmp/?*) ;;
    *)
        printf 'refusing unsafe runtime path: %s\n' "${runtime}" >&2
        exit 1
        ;;
esac

say() {
    printf '%s\n' "$*"
}

warn() {
    printf '%s\n' "$*" >&2
}

require_root() {
    if [ "${LINUXTOYS_NIX_GPU32_ALLOW_UNPRIVILEGED:-0}" = "1" ]; then
        return 0
    fi
    if [ "$(id -u)" -ne 0 ]; then
        warn "This helper must run as root (LinuxToys uses sudo for it)."
        exit 1
    fi
}

tools_ready() {
    local missing=() tool
    for tool in patchelf readelf jq; do
        command -v "${tool}" >/dev/null 2>&1 || missing+=("${tool}")
    done
    if ((${#missing[@]})); then
        warn "Missing graphics bundle tools: ${missing[*]}"
        warn "Install patchelf, binutils and jq, then retry."
        return 1
    fi
}

lib_dirs32() {
    local dir
    for dir in \
        /usr/lib/i386-linux-gnu /lib/i386-linux-gnu \
        /usr/lib32 /lib32 \
        /usr/lib /lib; do
        [ -d "${dir}" ] && printf '%s\n' "${dir}"
    done
}

dri_dirs32() {
    local dir
    for dir in \
        /usr/lib/i386-linux-gnu/dri /lib/i386-linux-gnu/dri \
        /usr/lib32/dri /lib32/dri \
        /usr/lib/dri /lib/dri; do
        [ -d "${dir}" ] && printf '%s\n' "${dir}"
    done
}

elf_bits() {
    local path="$1" class
    class="$(LC_ALL=C readelf -h "${path}" 2>/dev/null \
        | awk -F: '/Class:/ { gsub(/ /, "", $2); print $2; exit }')"
    case "${class}" in
        ELF64) printf '%s\n' 64 ;;
        ELF32) printf '%s\n' 32 ;;
    esac
}

has_host_32bit_driver() {
    local dir file
    while IFS= read -r dir; do
        for file in "${dir}"/libvulkan_*.so* "${dir}"/libGLX_*.so* "${dir}"/libEGL_*.so*; do
            [ -e "${file}" ] || continue
            [ "$(elf_bits "${file}")" = "32" ] && return 0
        done
    done < <(lib_dirs32)
    for file in /usr/share/vulkan/icd.d/*.i686.json /usr/share/vulkan/icd.d/*.x86.json; do
        [ -e "${file}" ] && return 0
    done
    return 1
}

supported() {
    [ "$(uname -m)" = "x86_64" ] || return 1
    has_host_32bit_driver
}

host_fingerprint() {
    local dir file
    {
        while IFS= read -r dir; do
            [ -d "${dir}" ] || continue
            find "${dir}" -maxdepth 1 \( -type f -o -type l \) \
                \( -name 'libGLX_*' -o -name 'libEGL_*' -o -name 'libGLESv1_CM_*' \
                   -o -name 'libGLESv2_*' -o -name 'libglapi.so*' -o -name 'libvulkan_*' \
                   -o -name 'libva*' -o -name 'libvdpau*' -o -name 'libVkLayer_*' \
                   -o -name 'libnvidia-*' -o -name 'libcuda*' -o -name 'libnvcuvid*' \
                   -o -name 'libnvoptix*' -o -name 'libcudadebugger*' -o -name 'libnvEncode*' \
                   -o -name 'libhsa-runtime64*' -o -name 'libamdhip64*' -o -name 'libroc*' \
                   -o -name 'libmiopen*' -o -name 'libhip*' -o -name 'libze_*' \
                   -o -name 'libRusticlOpenCL*' -o -name 'libigdrcl*' -o -name 'libnvidia-opencl*' \) \
                2>/dev/null | sort | while IFS= read -r file; do
                    [ -e "${file}" ] || continue
                    stat -Lc '%n %s %Y' "${file}" 2>/dev/null || true
                done
        done < <(lib_dirs32)
        while IFS= read -r dir; do
            [ -d "${dir}" ] || continue
            find "${dir}" -maxdepth 1 \( -type f -o -type l \) -name '*.so' 2>/dev/null | sort \
                | while IFS= read -r file; do
                    [ -e "${file}" ] || continue
                    stat -Lc '%n %s %Y' "${file}" 2>/dev/null || true
                done
        done < <(dri_dirs32)
        for dir in \
            /usr/share/vulkan/icd.d \
            /usr/share/glvnd/egl_vendor.d \
            /usr/share/egl/egl_external_platform.d \
            /etc/OpenCL/vendors /usr/share/OpenCL/vendors; do
            [ -d "${dir}" ] || continue
            find "${dir}" -maxdepth 1 -type f 2>/dev/null | sort \
                | while IFS= read -r file; do
                    stat -Lc '%n %s %Y' "${file}" 2>/dev/null || true
                done
        done
    } | sha256sum | awk '{print $1}'
}

build_bundle() {
    local fingerprint="$1"
    local -a lib_dirs=()
    local -a dri_dirs=()
    local lib_dir dri_dir src base lib resolved real first rel
    local -A added=()
    local -A canonical=()
    local -a libs=()
    local -a missing=()
    local -a queue=()
    local rpath="${runtime}/lib:${runtime}/lib/dri:\$ORIGIN"
    local core_lib_re loader_lib_re image_glibc host_glibc newest
    local vulkan_icds egl_vendors egl_platforms opencl_vendors vdpau_dir
    local required arch

    mapfile -t lib_dirs < <(lib_dirs32)
    mapfile -t dri_dirs < <(dri_dirs32)
    ((${#lib_dirs[@]})) || {
        warn "No 32-bit library directory found."
        return 1
    }

    core_lib_re='^(libc|libm|libpthread|libdl|librt|libutil|libresolv|libanl|libnsl|libmvec|libnss_|ld-linux).*\.so'
    loader_lib_re='^(libGL|libEGL|libGLESv1_CM|libGLESv2|libGLX|libGLdispatch|libOpenCL|libvulkan)\.so'
    image_glibc="$(getconf GNU_LIBC_VERSION 2>/dev/null | awk '{print $2}' || true)"

    rm -rf "${bundle_root}"
    install -d "${bundle_root}/lib" "${bundle_root}/lib/dri" "${bundle_root}/share"

    resolve_host_lib() {
        local name="$1" dir found
        if [[ "${name}" = /* ]]; then
            if [ -e "${name}" ] && [ "$(elf_bits "${name}")" = "32" ]; then
                printf '%s\n' "${name}"
                return 0
            fi
            name="$(basename "${name}")"
        fi
        for dir in "${lib_dirs[@]}"; do
            if [ -e "${dir}/${name}" ] && [ "$(elf_bits "${dir}/${name}")" = "32" ]; then
                printf '%s\n' "${dir}/${name}"
                return 0
            fi
        done
        while IFS= read -r found; do
            if [ -e "${found}" ] && [ "$(elf_bits "${found}")" = "32" ]; then
                printf '%s\n' "${found}"
                return 0
            fi
        done < <(ldconfig -p 2>/dev/null | awk -v name="${name}" '$1 == name { print $NF }')
        return 1
    }

    add_lib() {
        local source="$1" destdir="${2:-lib}"
        if [ -L "${source}" ] && [ ! -e "${source}" ]; then
            return 0
        fi
        [ -e "${source}" ] || [ -L "${source}" ] || return 0
        [ "$(elf_bits "${source}")" = "32" ] || return 0
        base="$(basename "${source}")"
        rel="${destdir}/${base}"
        case "${base}" in
            libnvidia-container*) return 0 ;;
        esac
        [ -n "${added[${rel}]:-}" ] && return 0
        added["${rel}"]=1
        libs+=("${rel}")
        install -d "$(dirname "${bundle_root}/${rel}")"
        real="$(readlink -f "${source}")"
        first="${canonical[${real}]:-}"
        if [ -n "${first}" ] && [ -e "${bundle_root}/${first}" ]; then
            ln -f "${bundle_root}/${first}" "${bundle_root}/${rel}"
            return 0
        fi
        canonical["${real}"]="${rel}"
        cp -L --preserve=mode,timestamps "${source}" "${bundle_root}/${rel}"
        patchelf --set-rpath "${rpath}" "${bundle_root}/${rel}"
    }

    add_glob() {
        local dir="$1" destdir="$2" pattern file
        shift 2
        [ -d "${dir}" ] || return 0
        for pattern in "$@"; do
            for file in "${dir}"/${pattern}; do
                [ -e "${file}" ] || [ -L "${file}" ] || continue
                add_lib "${file}" "${destdir}"
            done
        done
    }

    for lib_dir in "${lib_dirs[@]}"; do
        add_glob "${lib_dir}" lib \
            'libGLX_*.so*' 'libEGL_*.so*' 'libGLESv1_CM_*.so*' 'libGLESv2_*.so*' \
            'libglapi.so*' 'libvulkan_*.so*' 'libva*.so*' 'libvdpau*.so*'
        add_glob "${lib_dir}" lib 'libVkLayer_*.so*'
        add_glob "${lib_dir}" lib \
            'libnvidia-*.so*' 'libcuda*.so*' 'libnvcuvid*.so*' 'libnvoptix*.so*' \
            'libcudadebugger*.so*' 'libnvEncode*.so*'
        add_glob "${lib_dir}" lib \
            'libhsa-runtime64.so*' 'libamdhip64.so*' 'librocblas*.so*' \
            'librocsolver*.so*' 'librocfft*.so*' 'libmiopen*.so*' 'libhip*.so*' \
            'libze_*.so*' 'libRusticlOpenCL.so*' 'libigdrcl.so*' 'libnvidia-opencl.so*'
    done
    for dri_dir in "${dri_dirs[@]}"; do
        add_glob "${dri_dir}" lib/dri '*.so'
    done
    add_glob /usr/lib/vdpau lib/vdpau '*.so*'
    add_glob /usr/lib32/vdpau lib/vdpau '*.so*'
    add_glob /usr/lib/i386-linux-gnu/vdpau lib/vdpau '*.so*'
    [ -d /opt/rocm/lib ] && add_glob /opt/rocm/lib lib 'lib*.so*'

    rewrite_json() {
        local source="$1" output="$2" field="$3" needed="$4"
        local library resolved base
        library="$(jq -r "${field} // empty" "${source}")"
        [ -n "${library}" ] && [ "${library}" != "null" ] || return 0
        library="${library//\$\{LIB\}/lib}"
        library="${library//\$LIB/lib}"
        resolved="$(resolve_host_lib "${library}" || true)"
        if [ -z "${resolved}" ]; then
            [ "${needed}" = "1" ] && missing+=("${library} (library_path in ${source})")
            return 0
        fi
        base="$(basename "${resolved}")"
        add_lib "${resolved}" lib
        install -d "$(dirname "${output}")"
        jq --arg path "${runtime}/lib/${base}" "${field} = \$path" "${source}" > "${output}"
    }

    for src in "${vulkan_icd_dir}"/*.json; do
        [ -e "${src}" ] || continue
        base="$(basename "${src}")"
        case "${base}" in
            *.i686.json|*.x86.json) arch=32 ;;
            *.x86_64.json|*.amd64.json) arch=64 ;;
            *) arch=0 ;;
        esac
        [ "${arch}" -ne 0 ] && [ "${arch}" -ne 32 ] && continue
        required=0
        [ "${arch}" -eq 32 ] && required=1
        rewrite_json "${src}" "${bundle_root}/share/vulkan/icd.d/${base}" \
            '.ICD.library_path' "${required}"
    done
    for src in /usr/share/glvnd/egl_vendor.d/*.json; do
        [ -e "${src}" ] || continue
        rewrite_json "${src}" "${bundle_root}/share/glvnd/egl_vendor.d/$(basename "${src}")" \
            '.ICD.library_path' 0
    done
    for src in /usr/share/egl/egl_external_platform.d/*.json; do
        [ -e "${src}" ] || continue
        rewrite_json "${src}" "${bundle_root}/share/egl/egl_external_platform.d/$(basename "${src}")" \
            '.ICD.library_path' 0
    done
    for icd_dir in /etc/OpenCL/vendors /usr/share/OpenCL/vendors; do
        for src in "${icd_dir}"/*.icd; do
            [ -e "${src}" ] || continue
            lib="$(head -n1 "${src}" | tr -d '[:space:]')"
            [ -n "${lib}" ] || continue
            lib="${lib//\$\{LIB\}/lib}"
            lib="${lib//\$LIB/lib}"
            resolved="$(resolve_host_lib "${lib}" || true)"
            [ -n "${resolved}" ] || continue
            base="$(basename "${resolved}")"
            add_lib "${resolved}" lib
            install -d "${bundle_root}/share/OpenCL/vendors"
            printf '%s\n' "${runtime}/lib/${base}" \
                > "${bundle_root}/share/OpenCL/vendors/$(basename "${src}")"
        done
    done

    queue=("${libs[@]}")
    while ((${#queue[@]})); do
        rel="${queue[0]}"
        queue=("${queue[@]:1}")
        while IFS= read -r needed; do
            [ -n "${needed}" ] || continue
            if [[ "${needed}" =~ ${core_lib_re} || "${needed}" =~ ${loader_lib_re} ]]; then
                continue
            fi
            resolved="$(resolve_host_lib "${needed}" || true)"
            if [ -z "${resolved}" ]; then
                missing+=("${needed} (needed by ${rel})")
                continue
            fi
            before=${#libs[@]}
            add_lib "${resolved}" lib
            if (( ${#libs[@]} > before )); then
                queue+=("lib/${resolved##*/}")
            fi
        done < <(LC_ALL=C readelf -d "${bundle_root}/${rel}" 2>/dev/null \
            | awk '/\(NEEDED\)/ { gsub(/\[|\]/, "", $NF); print $NF }')
    done

    if ((${#libs[@]} == 0)); then
        warn "No 32-bit graphics libraries were found."
        return 1
    fi
    if ((${#missing[@]})); then
        printf '32-bit host graphics dependency closure is incomplete:\n' >&2
        printf '  %s\n' "${missing[@]}" >&2
        return 1
    fi

    if [ -n "${image_glibc}" ]; then
        for rel in "${libs[@]}"; do
            host_glibc="$(LC_ALL=C readelf --version-info "${bundle_root}/${rel}" 2>/dev/null \
                | grep -o 'GLIBC_2\.[0-9]*' \
                | sed 's/^GLIBC_//' \
                | sort -V \
                | tail -n1 || true)"
            [ -n "${host_glibc}" ] || continue
            newest="$(printf '%s\n%s\n' "${image_glibc}" "${host_glibc}" | sort -V | tail -n1)"
            if [ "${newest}" != "${image_glibc}" ]; then
                warn "${rel} requires GLIBC_${host_glibc}, but the host provides ${image_glibc}"
                return 1
            fi
        done
    fi

    printf '%s\n' "${libs[@]}" | sort -u > "${bundle_root}/libs.list"
    printf '%s\n' "${fingerprint}" > "${bundle_root}/.fingerprint"

    vulkan_icds="$(find "${bundle_root}/share/vulkan/icd.d" -maxdepth 1 -type f -name '*.json' \
        -printf "${runtime}/share/vulkan/icd.d/%f\n" 2>/dev/null | paste -sd: - || true)"
    egl_vendors="$(find "${bundle_root}/share/glvnd/egl_vendor.d" -maxdepth 1 -type f -name '*.json' \
        -printf "${runtime}/share/glvnd/egl_vendor.d/%f\n" 2>/dev/null | paste -sd: - || true)"
    egl_platforms=""
    compgen -G "${bundle_root}/share/egl/egl_external_platform.d/*.json" >/dev/null \
        && egl_platforms="${runtime}/share/egl/egl_external_platform.d"
    opencl_vendors=""
    compgen -G "${bundle_root}/share/OpenCL/vendors/*.icd" >/dev/null \
        && opencl_vendors="${runtime}/share/OpenCL/vendors"
    vdpau_dir=""
    compgen -G "${bundle_root}/lib/vdpau/*.so*" >/dev/null \
        && vdpau_dir="${runtime}/lib/vdpau"

    [ -n "${vulkan_icds}" ] && printf '%s\n' "VK_DRIVER_FILES=${vulkan_icds}" \
        > "${bundle_root}/env.vars"
    [ -n "${vulkan_icds}" ] && printf '%s\n' "VK_ICD_FILENAMES=${vulkan_icds}" \
        >> "${bundle_root}/env.vars"
    [ -n "${egl_vendors}" ] && printf '%s\n' "__EGL_VENDOR_LIBRARY_FILENAMES=${egl_vendors}" \
        >> "${bundle_root}/env.vars"
    [ -n "${egl_platforms}" ] && printf '%s\n' "__EGL_EXTERNAL_PLATFORM_CONFIG_DIRS=${egl_platforms}" \
        >> "${bundle_root}/env.vars"
    [ -n "${opencl_vendors}" ] && printf '%s\n' "OCL_ICD_VENDORS=${opencl_vendors}" \
        >> "${bundle_root}/env.vars"
    [ -n "${vdpau_dir}" ] && printf '%s\n' "VDPAU_DRIVER_PATH=${vdpau_dir}" \
        >> "${bundle_root}/env.vars"
    printf '%s\n' "LD_LIBRARY_PATH=${runtime}/lib" >> "${bundle_root}/env.vars"
    printf '%s\n' "LIBGL_DRIVERS_PATH=${runtime}/lib/dri" >> "${bundle_root}/env.vars"
    printf '%s\n' "LIBVA_DRIVERS_PATH=${runtime}/lib/dri" >> "${bundle_root}/env.vars"

    say "Built 32-bit host graphics bundle: ${#libs[@]} libraries${vulkan_icds:+, Vulkan ICDs}${egl_vendors:+, EGL vendors}${opencl_vendors:+, OpenCL}"
}

mount_bundle() {
    local rel
    if [ ! -r "${bundle_root}/libs.list" ]; then
        warn "32-bit host graphics bundle is missing: ${bundle_root}/libs.list"
        return 1
    fi
    while IFS= read -r rel; do
        [ -n "${rel}" ] || continue
        if [ ! -e "${bundle_root}/${rel}" ]; then
            warn "32-bit host graphics bundle file is missing: ${bundle_root}/${rel}"
            return 1
        fi
    done < "${bundle_root}/libs.list"

    if [ ! -L "${runtime}" ] && mountpoint -q "${runtime}" 2>/dev/null; then
        umount -l "${runtime}"
    fi
    rm -rf "${runtime}"
    install -d "${runtime}"
    mount --bind "${bundle_root}" "${runtime}"
    mount -o remount,bind,ro "${runtime}" \
        || warn "warning: could not remount ${runtime} read-only"
    say "Bind-mounted ${runtime} to ${bundle_root}"
}

write_environment() {
    local lib64="" dri64="" vdpau64="" icd64="" egl64="" eglplat64="" ocl64=""
    local lib32="${runtime}/lib" dri32="${runtime}/lib/dri" vdpau32=""
    local icd32="" egl32="" eglplat32="" ocl32=""
    local python
    python="$(command -v python3)" || {
        warn "python3 is required to update the graphics environment."
        return 1
    }

    if [ -d "${runtime64}/lib" ]; then
        lib64="${runtime64}/lib"
        dri64="${runtime64}/lib/dri"
        [ -d "${runtime64}/lib/vdpau" ] && vdpau64="${runtime64}/lib/vdpau"
        icd64="$(find "${runtime64}/share/vulkan/icd.d" -maxdepth 1 -type f -name '*.json' \
            -printf "${runtime64}/share/vulkan/icd.d/%f\n" 2>/dev/null | paste -sd: - || true)"
        egl64="$(find "${runtime64}/share/glvnd/egl_vendor.d" -maxdepth 1 -type f -name '*.json' \
            -printf "${runtime64}/share/glvnd/egl_vendor.d/%f\n" 2>/dev/null | paste -sd: - || true)"
        [ -d "${runtime64}/share/egl/egl_external_platform.d" ] \
            && eglplat64="${runtime64}/share/egl/egl_external_platform.d"
        [ -d "${runtime64}/share/OpenCL/vendors" ] \
            && ocl64="${runtime64}/share/OpenCL/vendors"
    fi

    [ -d "${bundle_root}/lib/vdpau" ] && vdpau32="${runtime}/lib/vdpau"
    icd32="$(find "${bundle_root}/share/vulkan/icd.d" -maxdepth 1 -type f -name '*.json' \
        -printf "${runtime}/share/vulkan/icd.d/%f\n" 2>/dev/null | paste -sd: - || true)"
    egl32="$(find "${bundle_root}/share/glvnd/egl_vendor.d" -maxdepth 1 -type f -name '*.json' \
        -printf "${runtime}/share/glvnd/egl_vendor.d/%f\n" 2>/dev/null | paste -sd: - || true)"
    [ -d "${bundle_root}/share/egl/egl_external_platform.d" ] \
        && eglplat32="${runtime}/share/egl/egl_external_platform.d"
    [ -d "${bundle_root}/share/OpenCL/vendors" ] \
        && ocl32="${runtime}/share/OpenCL/vendors"

    "${python}" - "${environment_file}" "${env_dir}" "${profile_file}" \
        "${lib64}" "${lib32}" "${dri64}" "${dri32}" "${vdpau64}" "${vdpau32}" \
        "${icd64}" "${icd32}" "${egl64}" "${egl32}" "${eglplat64}" "${eglplat32}" \
        "${ocl64}" "${ocl32}" <<'PY'
import os
import sys
import tempfile

(environment, env_dir, profile,
 lib64, lib32, dri64, dri32, vdpau64, vdpau32,
 icd64, icd32, egl64, egl32, eglplat64, eglplat32,
 ocl64, ocl32) = sys.argv[1:]

updates = {}
for key, values in (
    ("LD_LIBRARY_PATH", (lib64, lib32)),
    ("LIBGL_DRIVERS_PATH", (dri64, dri32)),
    ("LIBVA_DRIVERS_PATH", (dri64, dri32)),
    ("VDPAU_DRIVER_PATH", (vdpau64, vdpau32)),
    ("VK_DRIVER_FILES", (icd64, icd32)),
    ("VK_ICD_FILENAMES", (icd64, icd32)),
    ("__EGL_VENDOR_LIBRARY_FILENAMES", (egl64, egl32)),
    ("__EGL_EXTERNAL_PLATFORM_CONFIG_DIRS", (eglplat64, eglplat32)),
    ("OCL_ICD_VENDORS", (ocl64, ocl32)),
):
    merged = []
    for value in values:
        for entry in value.split(":"):
            entry = entry.strip()
            if entry and entry not in merged:
                merged.append(entry)
    if merged:
        updates[key] = ":".join(merged)

def merge(existing, additions):
    merged = []
    for value in (existing, additions):
        for entry in value.split(":"):
            entry = entry.strip()
            if entry and entry not in merged:
                merged.append(entry)
    return ":".join(merged)

def atomic_write(path, text):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    try:
        mode = os.stat(path).st_mode & 0o777
    except OSError:
        mode = 0o644
    fd, temporary = tempfile.mkstemp(prefix=".linuxtoys-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise

try:
    with open(environment, encoding="utf-8") as handle:
        original = handle.read().splitlines()
except OSError:
    original = []

ordered = []
seen = set()
for line in original:
    stripped = line.lstrip()
    if stripped and not stripped.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        key = key.strip()
        if key in updates:
            if key in seen:
                continue
            updates[key] = merge(value, updates[key])
            ordered.append(f"{key}={updates[key]}")
            seen.add(key)
            continue
    ordered.append(line)
for key, value in updates.items():
    if key not in seen:
        ordered.append(f"{key}={value}")

if not os.path.exists(environment + ".linuxtoys-nix-graphics.bak"):
    try:
        with open(environment, encoding="utf-8") as source, \
             open(environment + ".linuxtoys-nix-graphics.bak", "w", encoding="utf-8") as backup:
            backup.write(source.read())
    except OSError:
        pass
atomic_write(environment, "\n".join(ordered) + "\n")

dropin = os.path.join(env_dir, "90-linuxtoys-nix-graphics.conf")
atomic_write(dropin, "# LinuxToys: Nix graphics paths (64-bit and 32-bit)\n" +
    "".join(f"{key}={value}\n" for key, value in updates.items()))

profile_text = "# LinuxToys: Nix graphics paths (64-bit and 32-bit)\n" + \
    "".join(f"export {key}='{value}'\n" for key, value in updates.items())
atomic_write(profile, profile_text)
PY
}

install_self() {
    if [ "$(readlink -f "$0")" != "$(readlink -f "${script_path}")" ]; then
        install -d "$(dirname "${script_path}")"
        install -m 0755 "$0" "${script_path}"
    fi
}

install_service() {
    install -d "$(dirname "${service_path}")"
    cat > "${service_path}" <<EOF
[Unit]
Description=LinuxToys 32-bit host graphics drivers for Nix applications
DefaultDependencies=no
After=local-fs.target systemd-tmpfiles-setup.service
Wants=systemd-tmpfiles-setup.service
Before=display-manager.service

[Service]
Type=oneshot
ExecStart=${script_path} refresh
ExecStop=-/usr/bin/umount -l ${runtime}
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
    chmod 0644 "${service_path}"
    systemctl daemon-reload 2>/dev/null || true
}

mount_ready() {
    mountpoint -q "${runtime}" 2>/dev/null \
        && [ -e "${runtime}/libs.list" ]
}

setup() {
    require_root
    if ! supported; then
        say "No 32-bit host graphics drivers found; skipping the 32-bit bundle."
        return 0
    fi
    tools_ready
    install_self
    install_service
    local fingerprint
    fingerprint="$(host_fingerprint)"
    build_bundle "${fingerprint}"
    mount_bundle
    write_environment
    if command -v systemctl >/dev/null 2>&1; then
        systemctl enable "${service_name}" >/dev/null 2>&1 || true
        systemctl restart "${service_name}" || true
    fi
    say "32-bit Nix GPU support is ready."
}

refresh() {
    require_root
    if ! supported; then
        return 0
    fi
    local fingerprint current
    if tools_ready >/dev/null 2>&1; then
        fingerprint="$(host_fingerprint)"
        current="$(cat "${bundle_root}/.fingerprint" 2>/dev/null || true)"
        if [ ! -s "${bundle_root}/libs.list" ] || [ "${fingerprint}" != "${current}" ]; then
            build_bundle "${fingerprint}"
            mount_bundle
        elif ! mount_ready; then
            mount_bundle
        fi
        write_environment
    else
        if [ -s "${bundle_root}/libs.list" ]; then
            mount_ready || mount_bundle
            write_environment
        else
            warn "32-bit graphics bundle tools are unavailable and no existing bundle exists."
            return 1
        fi
    fi
}

status() {
    [ -s "${bundle_root}/libs.list" ] \
        && [ -r "${service_path}" ] \
        && mount_ready
}

remove_environment() {
    local python
    python="$(command -v python3)" || return 0
    "${python}" - "${environment_file}" <<'PY'
import os
import sys
import tempfile

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
except OSError:
    raise SystemExit(0)

keys = {
    "LD_LIBRARY_PATH",
    "LIBGL_DRIVERS_PATH",
    "LIBVA_DRIVERS_PATH",
    "VDPAU_DRIVER_PATH",
    "VK_DRIVER_FILES",
    "VK_ICD_FILENAMES",
    "__EGL_VENDOR_LIBRARY_FILENAMES",
    "__EGL_EXTERNAL_PLATFORM_CONFIG_DIRS",
    "OCL_ICD_VENDORS",
}
marker = "/run/opengl-driver-32"
out = []
for line in lines:
    stripped = line.lstrip()
    if stripped and not stripped.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        if key.strip() in keys and marker in value:
            kept = [entry for entry in value.split(":") if entry and marker not in entry]
            if kept:
                out.append(f"{key.strip()}={':'.join(kept)}")
            continue
    out.append(line)

directory = os.path.dirname(path) or "."
try:
    mode = os.stat(path).st_mode & 0o777
except OSError:
    mode = 0o644
fd, temporary = tempfile.mkstemp(prefix=".linuxtoys-", dir=directory)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(out) + "\n")
    os.chmod(temporary, mode)
    os.replace(temporary, path)
except BaseException:
    try:
        os.unlink(temporary)
    except OSError:
        pass
    raise
PY
}

remove() {
    require_root
    if command -v systemctl >/dev/null 2>&1; then
        systemctl disable --now "${service_name}" >/dev/null 2>&1 || true
    fi
    if [ ! -L "${runtime}" ] && mountpoint -q "${runtime}" 2>/dev/null; then
        umount -l "${runtime}" || true
    fi
    rm -rf "${runtime}" "${bundle_root}"
    rm -f "${service_path}" "${script_path}"
    rm -f "${env_dir}/90-linuxtoys-nix-graphics.conf" "${profile_file}"
    remove_environment
    if command -v systemctl >/dev/null 2>&1; then
        systemctl daemon-reload || true
    fi
    say "Removed the 32-bit Nix GPU bundle and service."
}

case "${1:-setup}" in
    supported) supported ;;
    status) status ;;
    build)
        require_root
        supported || {
            say "No 32-bit host graphics drivers found; skipping the 32-bit bundle."
            exit 0
        }
        tools_ready
        build_bundle "$(host_fingerprint)"
        ;;
    mount)
        require_root
        mount_bundle
        ;;
    env)
        require_root
        write_environment
        ;;
    setup) setup ;;
    refresh) refresh ;;
    remove) remove ;;
    *)
        warn "usage: $0 {supported|status|build|mount|env|setup|refresh|remove}"
        exit 2
        ;;
esac
