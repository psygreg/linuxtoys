#!/bin/bash
# name: RPM Fusion
# version: 1.0
# description: rpmfusion_desc
# icon: rpmfusion.svg
# compat: fedora, ostree, rhel
# repo: https://rpmfusion.org

# --- Start of the script code ---
askpass
if is_rhel; then
    if ! rhel_version=$(rpm -E %rhel 2>/dev/null) || [ "$rhel_version" = %rhel ]; then
        die "Could not determine RHEL version"
    fi
    # requirements
    { is_rhel && [ "$ID" = "rhel" ] && sudo subscription-manager repos --enable codeready-builder-for-rhel-$(rpm -E %rhel)-$(arch)-rpms; } || sudo dnf config-manager --set-enabled crb && sudo /usr/bin/crb enable
    { is_rhel && [ "$ID" = "rhel" ] && sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-$(rpm -E %rhel).noarch.rpm; } || pkg_install epel-release distribution-gpg-keys

    if ! rpm -qi "rpmfusion-free-release" &>/dev/null; then
        echo "Installing RPMFusion Free repository, please wait..."
        if ! sudo dnf install -y --nogpgcheck --setopt=timeout=5 "https://mirrors.rpmfusion.org/free/el/rpmfusion-free-release-$(rpm -E %rhel).noarch.rpm" &>/dev/null; then
            sudo dnf install -y --nogpgcheck --setopt=timeout=5 "https://download1.rpmfusion.org/free/el/rpmfusion-free-release-$(rpm -E %rhel).noarch.rpm" || fatal "Failed to install RPMFusion Free repository"
        fi
        _append_transmap "pkg file rpmfusion-free-release-$(rpm -E %rhel).noarch.rpm"
        echo "RPMFusion Free repository installed successfully"
    else
        echo "RPMFusion Free repository is already installed"
    fi
    if ! rpm -qi "rpmfusion-nonfree-release" &>/dev/null; then
        echo "Installing RPMFusion Non-Free repository, please wait..."
        if ! sudo dnf install -y --nogpgcheck --setopt=timeout=5 "https://mirrors.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-$(rpm -E %rhel).noarch.rpm" &>/dev/null; then
            sudo dnf install -y --nogpgcheck --setopt=timeout=5 "https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-$(rpm -E %rhel).noarch.rpm" || fatal "Failed to install RPMFusion Free repository"
        fi
        _append_transmap "pkg file rpmfusion-nonfree-release-$(rpm -E %rhel).noarch.rpm"
        echo "RPMFusion Non-Free repository installed successfully"
    else
        echo "RPMFusion Non-Free repository is already installed"
    fi
else
    is_ostree && { _package_manager_cmd="sudo rpm-ostree install"; } || _package_manager_cmd="sudo dnf install -y --setopt=timeout=5"
    if ! fedora_version=$(rpm -E %fedora 2>/dev/null) || [ "$fedora_version" = "%fedora" ]; then
        die "Could not determine Fedora version"
    fi

    if ! rpm -qi "rpmfusion-free-release" &>/dev/null; then
        echo "Installing RPMFusion Free repository, please wait..."
        if ! eval "$_package_manager_cmd" "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-${fedora_version}.noarch.rpm" &>/dev/null; then
            eval "$_package_manager_cmd" "https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-${fedora_version}.noarch.rpm" || fatal "Failed to install RPMFusion Free repository"
        fi
        echo "RPMFusion Free repository installed successfully"
    else
        echo "RPMFusion Free repository is already installed"
    fi
    if ! rpm -qi "rpmfusion-nonfree-release" &>/dev/null; then
        echo "Installing RPMFusion Non-Free repository, please wait..."
        if ! eval "$_package_manager_cmd" "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-${fedora_version}.noarch.rpm" &>/dev/null; then
            eval "$_package_manager_cmd" "https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-${fedora_version}.noarch.rpm" || fatal "Failed to install RPMFusion Non-Free repository"
        fi
        echo "RPMFusion Non-Free repository installed successfully"
    else
        echo "RPMFusion Non-Free repository is already installed"
    fi
    is_ostree && { rpm-ostree status --json | grep -q '"state":"staged"' && zenwrn "$msgostreepending" && exit 100; } || true
fi
info "$msg018"