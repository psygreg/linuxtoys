#!/bin/sh
# LINUXTOYS QUICK-INSTALLER (POSIX /bin/sh)

echo "================== LINUXTOYS QUICK-INSTALLER ===================="
printf "Do you wish to install or update LinuxToys? (y/n)\n"
# shellcheck disable=SC2162
read -r answer
answer=$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')
if [ "$answer" != "y" ]; then
    echo "===== CANCELLED ====="
    echo "Installation aborted."
    sleep 3
    exit 100
fi

# Garante HOME e sai com erro claro se falhar
cd "$HOME" || {
    echo "============ ERROR ============="
    echo "Fatal error: cannot change directory"
    exit 2
}

# Descobre a última tag via GitHub API (sem bashisms)
tag=$(
    curl -fsSL "https://api.github.com/repos/psygreg/linuxtoys/releases/latest" \
    | grep -o '"tag_name": *"[^"]*"' \
    | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/'
)
if [ -z "$tag" ]; then
    echo "============ ERROR ============="
    echo "Could not determine latest release tag from GitHub."
    exit 3
fi

# Helper de download: tenta wget silencioso; se falhar, usa curl -O
dl_file() {
    # $1 = URL
    # $2 = filename esperado
    if command -v wget >/dev/null 2>&1; then
        wget -q "$1" -O "$2" || {
            if command -v curl >/dev/null 2>&1; then
                curl -fsSL "$1" -o "$2" || return 1
            else
                return 1
            fi
        }
    elif command -v curl >/dev/null 2>&1; then
        curl -fsSL "$1" -o "$2" || return 1
    else
        return 1
    fi
    return 0
}

# Caminhos de artefatos por família
deb_pkg="linuxtoys_${tag}-1_amd64.deb"
deb_url="https://github.com/psygreg/linuxtoys/releases/download/${tag}/${deb_pkg}"

rpm_pkg="linuxtoys-${tag}-1.x86_64.rpm"
rpm_url="https://github.com/psygreg/linuxtoys/releases/download/${tag}/${rpm_pkg}"

arch_pkg="PKGBUILD"
arch_post_inst="linuxtoys.install"
arch_url="https://github.com/psygreg/linuxtoys/releases/download/${tag}/${arch_pkg}"
arch_url_post="https://github.com/psygreg/linuxtoys/releases/download/${tag}/${arch_post_inst}"

# Caso rpm-ostree (ex.: Silverblue/ Kinoite)
if command -v rpm-ostree >/dev/null 2>&1; then
    echo "Detected rpm-ostree system."
    echo "Downloading: $rpm_pkg"
    if ! dl_file "$rpm_url" "$rpm_pkg"; then
        echo "============ ERROR ============="
        echo "Failed to download: $rpm_url"
        exit 4
    fi

    if rpm -qi linuxtoys >/dev/null 2>&1; then
        sudo rpm-ostree remove linuxtoys || {
            echo "Failed to remove existing linuxtoys."
            rm -f "$rpm_pkg"
            exit 5
        }
    fi
    sudo rpm-ostree install "./$rpm_pkg" || {
        echo "Installation failed (rpm-ostree)."
        rm -f "$rpm_pkg"
        exit 6
    }
    rm -f "$rpm_pkg"
    echo "================== SUCCESS ===================="
    echo "LinuxToys installed or updated! Reboot to apply."
    sleep 3
    exit 0
fi

# Demais distros via /etc/os-release
if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
else
    echo "========== ERROR ============"
    echo "Unsupported operating system (no /etc/os-release)."
    sleep 3
    exit 1
fi

installed=false

# 1) Detecta por ID exato
case "${ID:-}" in
    debian|ubuntu)
        echo "Detected Debian/Ubuntu."
        echo "Downloading: $deb_pkg"
        if ! dl_file "$deb_url" "$deb_pkg"; then
            echo "============ ERROR ============="
            echo "Failed to download: $deb_url"
            exit 4
        fi
        sudo apt update || true
        sudo apt install -y "./$deb_pkg" || {
            echo "Installation failed (apt)."
            rm -f "$deb_pkg"
            exit 6
        }
        rm -f "$deb_pkg"
        installed=true
        ;;
    fedora|rhel|centos|rocky|almalinux)
            echo "Detected RHEL/Fedora-like by ID."
            echo "Downloading: $rpm_pkg"
            if ! dl_file "$rpm_url" "$rpm_pkg"; then
                echo "============ ERROR ============="
                echo "Failed to download: $rpm_url"
                exit 4
            fi
            if command -v dnf >/dev/null 2>&1; then
                sudo dnf install -y "./$rpm_pkg" || {
                    echo "Installation failed (dnf)."
                    rm -f "$rpm_pkg"
                    exit 6
                }
            else
                sudo yum install -y "./$rpm_pkg" || {
                    echo "Installation failed (yum)."
                    rm -f "$rpm_pkg"
                    exit 6
                }
            fi
            rm -f "$rpm_pkg"
            installed=true
            ;;
    suse|opensuse)
        echo "Detected SUSE/OpenSUSE by ID."
        echo "Downloading: $rpm_pkg"
        if ! dl_file "$rpm_url" "$rpm_pkg"; then
            echo "============ ERROR ============="
            echo "Failed to download: $rpm_url"
            exit 4
        fi
        sudo zypper install -y "./$rpm_pkg" || {
            echo "Installation failed (zypper)."
            rm -f "$rpm_pkg"
            exit 6
        }
        rm -f "$rpm_pkg"
        installed=true
        ;;
    arch|cachyos)
        echo "Detected Arch-like by ID."
        echo "Downloading: $arch_pkg"
        if ! dl_file "$arch_url" "$arch_pkg"; then
            echo "============ ERROR ============="
            echo "Failed to download: $arch_url"
            exit 4
        fi
        if ! dl_file "$arch_url_post" "$arch_post_inst"; then
            echo "============ ERROR ============="
            echo "Failed to download: $arch_url_post"
            exit 4
        fi
        makepkg -i || {
            echo "Installation failed (pacman)."
            rm -f "$arch_pkg"
            rm -f "$arch_post_inst"
            exit 6
        }
        rm -f "$arch_pkg"
        rm -f "$arch_post_inst"
        installed=true
        ;;
esac

# 2) Se não decidiu pelo ID, tenta por ID_LIKE
if [ "$installed" != "true" ]; then
    case "${ID_LIKE:-}" in
        *debian*|*ubuntu*)
            echo "Detected Debian/Ubuntu-like by ID_LIKE."
            echo "Downloading: $deb_pkg"
            if ! dl_file "$deb_url" "$deb_pkg"; then
                echo "============ ERROR ============="
                echo "Failed to download: $deb_url"
                exit 4
            fi
            sudo apt update || true
            sudo apt install -y "./$deb_pkg" || {
                echo "Installation failed (apt)."
                rm -f "$deb_pkg"
                exit 6
            }
            rm -f "$deb_pkg"
            installed=true
            ;;
        *rhel*|*fedora*)
            echo "Detected RHEL/Fedora-like by ID_LIKE."
            echo "Downloading: $rpm_pkg"
            if ! dl_file "$rpm_url" "$rpm_pkg"; then
                echo "============ ERROR ============="
                echo "Failed to download: $rpm_url"
                exit 4
            fi
            if command -v dnf >/dev/null 2>&1; then
                sudo dnf install -y "./$rpm_pkg" || {
                    echo "Installation failed (dnf)."
                    rm -f "$rpm_pkg"
                    exit 6
                }
            else
                sudo yum install -y "./$rpm_pkg" || {
                    echo "Installation failed (yum)."
                    rm -f "$rpm_pkg"
                    exit 6
                }
            fi
            rm -f "$rpm_pkg"
            installed=true
            ;;
        *suse*)
            echo "Detected SUSE/OpenSUSE by ID_LIKE."
            echo "Downloading: $rpm_pkg"
            if ! dl_file "$rpm_url" "$rpm_pkg"; then
                echo "============ ERROR ============="
                echo "Failed to download: $rpm_url"
                exit 4
            fi
            sudo zypper install -y "./$rpm_pkg" || {
                echo "Installation failed (zypper)."
                rm -f "$rpm_pkg"
                exit 6
            }
            rm -f "$rpm_pkg"
            installed=true
            ;;
        *arch*)
            echo "Detected Arch-like by ID_LIKE."
            echo "Downloading: $arch_pkg"
            if ! dl_file "$arch_url" "$arch_pkg"; then
                echo "============ ERROR ============="
                echo "Failed to download: $arch_url"
                exit 4
            fi
            sudo pacman -U --noconfirm "./$arch_pkg" || {
                echo "Installation failed (pacman)."
                rm -f "$arch_pkg"
                exit 6
            }
            rm -f "$arch_pkg"
            installed=true
            ;;
    esac
fi

if [ "$installed" = "true" ]; then
    echo "========== SUCCESS ============"
    echo "LinuxToys installed or updated!"
    sleep 3
    exit 0
fi

echo "========== ERROR ============"
echo "Unsupported operating system."
sleep 3
exit 1
