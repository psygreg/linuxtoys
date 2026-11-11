# library of helpers and repository checkers
#
# Helper function to fetch from multiple sources with fallback
fetch_from_mirror () {
    local filename="$1"
    local github_url="$2"
    local gitea_url="$3"

    if wget "$github_url" -O "$filename"; then
        return 0
    fi
    if wget "$gitea_url" -O "$filename"; then
        return 0
    fi
    return 1
}

# Download DaVinci Resolve (Free or Studio, per $_upkgname) from Blackmagic Design.
# Sets _archive_name and _archive_run_name; the archive is left as ${_archive_name}.zip.
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
            _filever=$(printf "%s" "$_releaseinfo" | awk -F'[,:]' '{for(i=1;i<=NF;i++){if($i~/"major"/){print $(i+1)} if($i~/"minor"/){print $(i+1)}}}' | sed 'N;s/\n/./')
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
    #     echo "Version mismatch"
    #     return 1
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

    curl -L -o "${_archive_name}.zip" "$_srcurl" || die "Failed to download DaVinci Resolve"
}

# --- CLInfo Test ---
clinfo_chk () {
    if ! command -v clinfo &>/dev/null; then
        _msg info "clinfo not found, installing..."
        pkg_install clinfo
    fi
    # Check if OpenCL acceleration is available
    local platform_count
    platform_count=$(clinfo 2>&1 | grep -m1 "Number of platforms" | grep -oE "[0-9]+$")

    if [ -n "$platform_count" ] && [ "$platform_count" -ge 1 ]; then
        _msg info "OpenCL acceleration is available ($platform_count platform(s) found)"
        return 0
    else
        _msg error "OpenCL acceleration is not available"
        return 1
    fi
}

# enable non-free and contrib repos on debian
enable_debian_nonfree () {
    if is_debian; then
        local updated=0
        if ! grep -qE "contrib" /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources 2>/dev/null; then
            if [ -f /etc/apt/sources.list ]; then
                prep_edit /etc/apt/sources.list
                sudo_ sed -i 's/main$/main contrib/' /etc/apt/sources.list
                updated=1
            fi
            if [ -f /etc/apt/sources.list.d/debian.sources ]; then
                prep_edit /etc/apt/sources.list.d/debian.sources
                sudo_ sed -i 's/^Components: \(.*\)$/Components: \1 contrib/' /etc/apt/sources.list.d/debian.sources
                updated=1
            fi
        fi
        if ! grep -qE "non-free" /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources 2>/dev/null; then
            if [ -f /etc/apt/sources.list ]; then
                prep_edit /etc/apt/sources.list
                sudo_ sed -i 's/main$/main non-free/' /etc/apt/sources.list
                updated=1
            fi
            if [ -f /etc/apt/sources.list.d/debian.sources ]; then
                prep_edit /etc/apt/sources.list.d/debian.sources
                sudo_ sed -i 's/^Components: \(.*\)$/Components: \1 non-free/' /etc/apt/sources.list.d/debian.sources
                updated=1
            fi
        fi
        if [ $updated -eq 1 ]; then
            sudo_ apt update
        fi
    fi
}

# enable backports repos on debian
enable_debian_backports() {
    is_debian || return 1

    local codename="${VERSION_CODENAME:-}"
    case "$codename" in
    trixie|forky|bookworm|bullseye)
        ;;
    sid|unstable|testing)
        echo "Debian Backports is not applicable to the '$codename' suite." >&2
        return 1
        ;;
    *)
        codename="trixie"
        ;;
    esac

    # Do nothing when the correct Backports repository is already configured.
    if grep -RqsE \
        "^(Suites:[[:space:]]*|deb[[:space:]]+.*[[:space:]])${codename}-backports([[:space:]]|$)" \
        /etc/apt/sources.list \
        /etc/apt/sources.list.d/*.list \
        /etc/apt/sources.list.d/*.sources 2>/dev/null
    then
        return 0
    fi

    local source_file="/etc/apt/sources.list.d/debian-backports.sources"
    if [[ -e "$source_file" ]]; then
        prep_edit "$source_file"
    else
        prep_create "$source_file"
    fi
    sudo_ tee "$source_file" >/dev/null <<EOF
Types: deb
URIs: https://deb.debian.org/debian
Suites: ${codename}-backports
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF

    sudo_ apt update
}

# legacy function call support - kept here so older code and local user scripts won't break

multilib_chk() {
    call_script multilib
}

chaotic_aur_lib() {
    call_script chaotic
}

rpmfusion_chk() {
    call_script rpmfusion
}

pip_lib() {
    call_script pip
}

flatpak_in_lib() {
    call_script flathub
}
