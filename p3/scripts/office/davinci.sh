#!/bin/bash
# name: DaVinci Resolve
# version: 1.0
# description: davinci_desc
# icon: resolve.svg

# functions
#create JSON, user agent and download Resolve
getresolve () {
  	local pkgname="$_upkgname"
  	local _product=""
  	local _referid=""
  	local _siteurl=""
  	_archive_name=""
  	_archive_run_name=""

  	if [ "$pkgname" == "davinci-resolve" ]; then
    		_product="DaVinci Resolve"
    		_referid='dfd43085ef224766b06b579ce8a6d097'
    		_siteurl="https://www.blackmagicdesign.com/api/support/latest-stable-version/davinci-resolve/linux"
            local _useragent="User-Agent: Mozilla/5.0 (X11; Linux ${CARCH}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Safari/537.36"
  	        local _releaseinfo
  	        _releaseinfo=$(curl -Ls "$_siteurl")
            _pkgver=$(printf "%s" "$_releaseinfo" | awk -F'[,:]' '{for(i=1;i<=NF;i++){if($i~/"major"/){print $(i+1)} if($i~/"minor"/){print $(i+1)} if($i~/"releaseNum"/){print $(i+1)}}}' | sed 'N;s/\n/./;N;s/\n/./')
            _releaseNum=$(printf "%s" "$_releaseinfo" | awk -F'[,:]' '{for(i=1;i<=NF;i++){if($i~/"releaseNum"/){print $(i+1)}}}')
            if [ "$_releaseNum" == "0" ]; then
                _filever=$(printf "%s" "$_releaseinfo" | awk -F'[,:]' '{for(i=1;i<=NF;i++){if($i~/"major"/){print $(i+1)} if($i~/"minor"/){print $(i+1)}}' | sed 'N;s/\n/./')
            else
                _filever="${_pkgver}"
            fi
    		_archive_name="DaVinci_Resolve_${_filever}_Linux"
    		_archive_run_name="DaVinci_Resolve_${_filever}_Linux"
  	elif [ "$pkgname" == "davinci-resolve-studio" ]; then
    		_product="DaVinci Resolve Studio"
    		_referid='0978e9d6e191491da9f4e6eeeb722351'
    		_siteurl="https://www.blackmagicdesign.com/api/support/latest-stable-version/davinci-resolve-studio/linux"
            local _useragent="User-Agent: Mozilla/5.0 (X11; Linux ${CARCH}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Safari/537.36"
  	        local _releaseinfo
  	        _releaseinfo=$(curl -Ls "$_siteurl")
            _pkgver=$(printf "%s" "$_releaseinfo" | awk -F'[,:]' '{for(i=1;i<=NF;i++){if($i~/"major"/){print $(i+1)} if($i~/"minor"/){print $(i+1)} if($i~/"releaseNum"/){print $(i+1)}}}' | sed 'N;s/\n/./;N;s/\n/./')
            _releaseNum=$(printf "%s" "$_releaseinfo" | awk -F'[,:]' '{for(i=1;i<=NF;i++){if($i~/"releaseNum"/){print $(i+1)}}}')
            if [ "$_releaseNum" == "0" ]; then
                _filever=$(printf "%s" "$_releaseinfo" | awk -F'[,:]' '{for(i=1;i<=NF;i++){if($i~/"major"/){print $(i+1)} if($i~/"minor"/){print $(i+1)}}}' | sed 'N;s/\n/./')
            else
                _filever="${_pkgver}"
            fi
    		_archive_name="DaVinci_Resolve_Studio_${_filever}_Linux"
    		_archive_run_name="DaVinci_Resolve_Studio_${_filever}_Linux"
  	fi

  	local _downloadId
  	_downloadId=$(printf "%s" "$_releaseinfo" | sed -n 's/.*"downloadId":"\([^"]*\).*/\1/p')

  	# Optional version check - uncomment if needed
  	# if [[ $_expected_pkgver != "$_pkgver" ]]; then
    	# 	echo "Version mismatch"
    	# 	return 1
  	# fi

  	local _reqjson
  	_reqjson="{\"firstname\": \"Arch\", \"lastname\": \"Linux\", \"email\": \"someone@archlinux.org\", \"phone\": \"202-555-0194\", \"country\": \"us\", \"street\": \"Bowery 146\", \"state\": \"New York\", \"city\": \"AUR\", \"product\": \"$_product\"}"
  	_reqjson=$(printf '%s' "$_reqjson" | sed 's/[[:space:]]\+/ /g')
  	_useragent=$(printf '%s' "$_useragent" | sed 's/[[:space:]]\+/ /g')
  	local _useragent_escaped="${_useragent// /\\ }"

  	_siteurl="https://www.blackmagicdesign.com/api/register/us/download/${_downloadId}"
  	local _srcurl
  	_srcurl=$(curl -s \
    		-H 'Host: www.blackmagicdesign.com' \
    		-H 'Accept: application/json, text/plain, */*' \
    		-H 'Origin: https://www.blackmagicdesign.com' \
    		-H "$_useragent" \
    		-H 'Content-Type: application/json;charset=UTF-8' \
    		-H "Referer: https://www.blackmagicdesign.com/support/download/${_referid}/Linux" \
    		-H 'Accept-Encoding: gzip, deflate, br' \
    		-H 'Accept-Language: en-US,en;q=0.9' \
    		-H 'Authority: www.blackmagicdesign.com' \
    		-H 'Cookie: _ga=GA1.2.1849503966.1518103294; _gid=GA1.2.953840595.1518103294' \
    		--data-ascii "$_reqjson" \
    		--compressed \
    		"$_siteurl")

  	curl -L -o "${_archive_name}.zip" "$_srcurl"
}

davincinatd () {
    if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
        wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolvedeb.sh
        chmod +x autoresolvedeb.sh
        ./autoresolvedeb.sh
        rm autoresolvedeb.sh
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
        wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolvepkg.sh
        chmod +x autoresolvepkg.sh
        ./autoresolvepkg.sh
        rm autoresolvepkg.sh
    elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" = "fedora" ]; then
        wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolverpm.sh
        chmod +x autoresolverpm.sh
        ./autoresolverpm.sh
        rm autoresolverpm.sh
    elif [[ "$ID_LIKE" == *suse* ]]; then
        wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolverpm.sh
        chmod +x autoresolverpm.sh
        ./autoresolverpm.sh
        rm autoresolverpm.sh
    fi
}

davinciboxd () {
    wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autodavincibox.sh
    chmod +x autodavincibox.sh
    ./autodavincibox.sh
    rm autodavincibox.sh
}

davinciboxatom () {

    dv_atom_deps () {
        _packages=(toolbox podman lshw)
        local amdGPU=$(lspci | grep -Ei 'vga|3d' | grep -Ei 'amd|ati|radeon|amdgpu')
        local nvGPU=$(lspci | grep -iE 'vga|3d' | grep -i nvidia)
        local intelGPU=$(lspci | grep -Ei 'vga|3d' | grep -Ei 'intel|iris|xe')
        if [[ -n "$nvGPU" ]]; then
        # add repository and install nvidia container toolkit
            curl -O https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo
            sudo install -o 0 -g 0 nvidia-container-toolkit.repo /etc/yum.repos.d/nvidia-container-toolkit.repo
            rm nvidia-container-toolkit.repo
            NVIDIA_CONTAINER_TOOLKIT_VERSION=1.17.8-1
           _packages+=(nvidia-container-toolkit-${NVIDIA_CONTAINER_TOOLKIT_VERSION} nvidia-container-toolkit-base-${NVIDIA_CONTAINER_TOOLKIT_VERSION} libnvidia-container-tools-${NVIDIA_CONTAINER_TOOLKIT_VERSION} libnvidia-container1-${NVIDIA_CONTAINER_TOOLKIT_VERSION})
        elif [[ -n "$amdGPU" ]]; then
            # select ROCm or Rusticl
            while true; do
                CHOICE=$(zenity --list --title="AMD Drivers" \
        		    --column="$msg006" \
            	    "ROCm - ${msg290}" \
            	    "RustiCL - ${msg256}" \
            	    --height=300 --width=360)

                if [ $? -ne 0 ]; then
        		    break
   			    fi

                case $CHOICE in
            	    "ROCm - ${msg290}") _packages+=(rocm-comgr rocm-runtime rccl rocalution rocblas rocfft rocm-smi rocsolver rocsparse rocm-device-libs rocminfo rocm-hip hiprand rocm-opencl clinfo) ;;
            	    "RustiCL - ${msg256}") _packages+=(mesa-libOpenCL clinfo) ;;
            	    *) echo "Invalid Option" ;;
                esac

			    break
            done
        elif [[ -n "$intelGPU" ]]; then
            # install intel compute runtime
            _packages+=("intel-compute-runtime")
        fi
        sudo_rq
        _install_
        if [[ $? -eq 1 ]]; then
            echo "No packages to install."
        else
            if [[ "${_to_install[*]}" =~ "rocm" ]]; then
                sudo usermod -aG render,video $USER
            elif [[ "${_to_install[*]}" =~ "mesa-libOpenCL" ]]; then
                curl -sL https://raw.githubusercontent.com/psygreg/linuxtoys-atom/main/src/patches/rusticl-amd \
                    | sudo tee -a /etc/environment > /dev/null
            fi
        fi
    }

    # installation
    dv_atom_in () {
        sudo_rq
        dv_atom_deps
        git clone https://github.com/zelikos/davincibox.git
        sleep 1
        cd davincibox
        getresolve
        unzip $_archive_name.zip
        chmod +x setup.sh
        ./setup.sh $_archive_run_name.run
	    zenity --info --title "AutoDaVinciBox" --text "Installation successful." --height=300 --width=300
        cd ..
        rm -rf davincibox
    }

    if [[ "$ID" == "bazzite" ]] || [[ "$ID" == "aurora" ]] || [[ "$ID" == "bluefin" ]]; then
	    ujust install-resolve
    else 
	    while true; do
		    CHOICE=$(zenity --list --title="AutoDaVinciBox" \
        	    --column="Which version do you want to install?" \
			    "Free" \
			    "Studio" \
			    "$msg070" \
			    --height=300 --width=300)

		    if [ $? -ne 0 ]; then
        	    break
   		    fi

		    case $CHOICE in
			    "Free") _upkgname='davinci-resolve'
    			    dv_atom_in
				    break ;;
			    "Studio") _upkgname='davinci-resolve-studio'
	  			    dv_atom_in
    			    break ;;
			    "$msg070") break && return 100;;
			    *) echo "Invalid Option" ;;
		    esac
	    done
    fi

}
# if on atomic distros, go straight to davincibox
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
# warn about just installing Resolve, and still requiring a purchase from BMD to use Studio
zenwrn "$msg034"
cd $HOME
if command -v rpm-ostree >/dev/null 2>&1; then
    davinciboxatom
else
    # menu
    while true; do

        CHOICE=$(zenity --list --title "DaVinci Resolve" \
            --column="" \
            "$msg231" \
            "$msg232" \
            "$msg070" \
            --height=330 --width=300)

        if [ $? -ne 0 ]; then
            break
        fi

        case $CHOICE in
        "$msg231") davinciboxd && break ;;
        "$msg232") davincinatd && break ;;
        "$msg070") break && exit 100;;
        *) echo "Invalid Option" ;;
        esac
        
    done
fi

