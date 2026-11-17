#!/bin/bash
# name: DaVinci Resolve
# version: 1.0
# description: davinci_desc
# icon: resolve.svg
# hybridgpu: !ostree, !solus
# gpu: nvidia, rocm, rusticl, xe
# compat: !steamos

# functions
davincinatd () {
    { is_rhel && dv_rhel; } || true

    # opencl check for AMD/Intel GPUs
    if is_intel || is_amd; then
        if ! clinfo_chk; then
            fatal "$nocl"
        fi
    fi
    if is_debian || is_ubuntu; then
        curl -L -o autoresolvedeb.sh "https://raw.githubusercontent.com/psygreg/autoresolvedeb/main/linuxtoys/autoresolvedeb.sh"
        chmod +x autoresolvedeb.sh
        ./autoresolvedeb.sh
        rm autoresolvedeb.sh
    elif is_arch || is_cachy; then
        curl -L -o autoresolvepkg.sh "https://raw.githubusercontent.com/psygreg/autoresolvedeb/main/linuxtoys/autoresolvepkg.sh"
        chmod +x autoresolvepkg.sh
        ./autoresolvepkg.sh
        rm autoresolvepkg.sh
    elif is_fedora; then
        curl -L -o autoresolverpm.sh "https://raw.githubusercontent.com/psygreg/autoresolvedeb/main/linuxtoys/autoresolverpm.sh"
        chmod +x autoresolverpm.sh
        ./autoresolverpm.sh
        rm autoresolverpm.sh
    elif is_suse; then
        curl -L -o autoresolverpm.sh "https://raw.githubusercontent.com/psygreg/autoresolvedeb/main/linuxtoys/autoresolverpm.sh"
        chmod +x autoresolverpm.sh
        ./autoresolverpm.sh
        rm autoresolverpm.sh
    fi
}

# Rusticl must be installed in the container, not only on its host.
dv_rusticl_container() {
    if is_rusticl_capable && ! is_rocm_capable; then
        RUSTICL_CONTAINER=davincibox call_script rusticl || fatal "Failed to install Rusticl in DaVinciBox"
        local desktop_file="$HOME/.local/share/applications/DaVinciResolve.desktop"
        if [[ -f "$desktop_file" ]]; then
            prep_edit "$desktop_file"
            sed -i 's|^Exec=.*|Exec=distrobox-enter -n davincibox -- env RUSTICL_ENABLE=radeonsi /opt/resolve/bin/resolve|' "$desktop_file" || return 1
        fi
    fi
}

davinciboxd () {
    curl -L -o autodavincibox.sh "https://raw.githubusercontent.com/psygreg/autoresolvedeb/main/linuxtoys/autodavincibox.sh"
    chmod +x autodavincibox.sh
    ./autodavincibox.sh
    rm autodavincibox.sh
}

dv_rhel () {
    dv_rhel_in () {
        check_disk_space "$_upkgname"
        sudo_rq
        rpmfusion_chk # needs EPEL

        # dependencies -- compile python2
        sudo dnf groupinstall -y "Development Tools"
        pkg_install fuse gcc openssl-devel bzip2-devel libffi-devel wget tar curl
        prep_tmp_noram
        wget "https://www.python.org/ftp/python/2.7.18/Python-2.7.18.tgz" || fatal "unable to get dependency python2"
        tar xzf Python-2.7.18.tgz && cd Python-2.7.18
        export CFLAGS="-std=c11"
        ./configure --with-system-ffi --with-computed-gotos --enable-optimizations --enable-unicode=ucs4
        make -j$(nproc) build_all
        sudo make altinstall
        sudo ln -s /usr/local/bin/python2.7 /usr/local/bin/python2
        { which python2 &>/dev/null && echo "Python2 installation successful. Proceeding to Resolve installation."; } || fatal "Dependency python2 installation failed."

        # resolve dependencies
        pkg_install qt5-qtbase-gui libxcb glib2 apr-util mesa-libGLU libxcrypt-compat zlib-ng zlib-ng-compat
        if is_rusticl_capable && ! is_rocm_capable; then
            call_script rusticl || fatal "Failed to install Rusticl"
        fi
        { is_rocm_capable && pkg_install rocm-comgr rocm-runtime rccl rocalution rocblas rocfft rocm-smi rocsolver rocsparse rocm-device-libs rocminfo rocm-hip hiprand rocm-opencl clinfo && sudo usermod -aG render,video "$USER"; } || true
        { is_icr_capable && pkg_install intel-compute-runtime; } || true
        {( is_nvidia && ( rpm -qi "cuda" &>/dev/null || rpm -qi "cuda-drivers" &>/dev/null )) || fatal "Missing cuda drivers. Please install them from the Drivers menu according to your GPU."; } || true

        # install resolve
        getresolve
        unzip "$_archive_name.zip"
        prep_dir /opt/resolve
        chmod +x ${_archive_run_name}.run
        export SKIP_PACKAGE_CHECK=1
        ./${_archive_run_name}.run || fatal "Failed to install Resolve"
        # libs patch
        sudo_rq
        sudo mkdir -p /opt/resolve/libs/disabled
        move_ /opt/resolve/libs/libglib* /opt/resolve/libs/disabled/
        move_ /opt/resolve/libs/libgio* /opt/resolve/libs/disabled/
        move_ /opt/resolve/libs/libgmodule* /opt/resolve/libs/disabled/

        if [ "$_upkgname" = "davinci-resolve-studio" ]; then
            export AUTO_DVNAT=1
            # call_script resolveaac
            call_script resolvehw
        fi

        info "$finishmsg"
    }

    while true; do
		CHOICE=$(radioselect --no-default --title "DaVinci Resolve installer for RHEL" --text "Which version do you want to install?" "Free" "Studio" "$msg070") || break

		case $CHOICE in
			"Free") _upkgname='davinci-resolve'
    			dv_rhel_in
				break ;;
			"Studio") _upkgname='davinci-resolve-studio'
	  			dv_rhel_in
    			break ;;
			"$msg070") exit 100;;
			*) echo "Invalid Option" ;;
		esac
	done
}

davinciboxatom () {

    dv_atom_deps () {
        pkg_install --ostreecheck toolbox podman lshw
        if is_nvidia; then
            pkg_install curl
			curl -s -L -k https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
  				sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo
            pkg_install --ostreecheck nvidia-container-toolkit nvidia-container-toolkit-base libnvidia-container-tools libnvidia-container1
        fi
    }

    # installation
    dv_atom_in () {
        check_disk_space "$_upkgname"
        sudo_rq
        dv_atom_deps
        git clone https://github.com/zelikos/davincibox.git
        sleep 1
        cd davincibox
        getresolve
        unzip "$_archive_name.zip"
        chmod +x setup.sh
        if ./setup.sh "$_archive_run_name.run"; then
            distrobox_created davincibox
        else
            fatal "Failed to create DaVinciBox container."
        fi
	    zenity --info --title "AutoDaVinciBox" --text "Installation successful." --height=300 --width=300
        # set up ROCm inside davincibox for a sizable performance increase for AMD GPUs
        if is_rocm_capable; then
            distrobox enter davincibox -- bash -c "sudo dnf install -y rocm-comgr rocm-runtime rccl rocalution rocblas rocfft rocm-smi rocsolver rocsparse rocm-device-libs rocminfo rocm-hip hiprand rocm-opencl clinfo && sudo usermod -aG render,video \$USER"
            # stop to ensure usermod takes effect before usage of the software
            distrobox stop davincibox
        fi
        dv_rusticl_container
        cd $HOME
        sudo rm -rf davincibox #cleanup

        if [ "$_upkgname" = "davinci-resolve-studio" ]; then
            export AUTO_DVBOX=1
            # call_script resolveaac
            call_script resolvehw
        fi

        zeninf "$finishmsg"
    }

	while true; do
		CHOICE=$(radioselect --no-default --title "AutoDaVinciBox" --text "Which version do you want to install?" "Free" "Studio" "$msg070") || break

		case $CHOICE in
			"Free") _upkgname='davinci-resolve'
    			dv_atom_in
				break ;;
			"Studio") _upkgname='davinci-resolve-studio'
	  			dv_atom_in
    			break ;;
			"$msg070") exit 100;;
			*) echo "Invalid Option" ;;
		esac
	done
}
# if on atomic distros, go straight to davincibox
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
# warn about just installing Resolve, and still requiring a purchase from BMD to use Studio
zenwrn "$msg034"
prep_tmp
export SCRIPT_DIR
if is_ostree; then
    { ! is_hybridgpu && davinciboxatom; } || die "$incompatmsg"
elif is_solus; then
    { ! is_hybridgpu && davinciboxd; } || die "$incompatmsg"
elif is_hybridgpu || is_zorin; then
    davincinatd
else
    # menu
    while true; do

        CHOICE=$(radioselect --no-default --title "DaVinci Resolve" "$msg231" "$msg232" "$msg070") || break

        case $CHOICE in
        "$msg231") davinciboxd && break ;;
        "$msg232") davincinatd && break ;;
        "$msg070") exit 100;;
        *) echo "Invalid Option" ;;
        esac

    done
fi
