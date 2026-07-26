#!/bin/bash
# name: Java OpenJDK
# version: 1.0
# description: java_desc
# icon: java.svg

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

# functions
jdk_install() {
    local -a javas=(
        "$_jdk8"
        "$_jdk11"
        "$_jdk17"
        "$_jdk21"
        "$_jdk25"
        "$_jdk_latest"
    )
    local -a packages=()
    local jav
    for jav in "${javas[@]}"; do
        [[ -n "$jav" ]] || continue

        if is_debian || is_ubuntu; then
            packages+=(
                "openjdk-${jav}-jdk"
                "openjdk-${jav}-jre"
            )

        elif is_fedora || is_rhel; then
            case "$jav" in
                21|25)
                    packages+=(
                        "java-${jav}-openjdk"
                        "java-${jav}-openjdk-devel"
                    )
                    ;;
                latest)
                    packages+=(
                        java-latest-openjdk
                        java-latest-openjdk-devel
                    )
                    ;;
                *)
                    warn "Java version ${jav} is not available in Fedora/RHEL repositories. Skipping."
                    ;;
            esac

        elif is_suse; then
            packages+=(
                "java-${jav}-openjdk"
                "java-${jav}-openjdk-devel"
            )

        elif is_solus; then
            case "$jav" in
                21|25)
                    packages+=("openjdk-${jav}")
                    ;;
                *)
                    warn "Java version ${jav} is not available in Solus repositories. Skipping."
                    ;;
            esac

        elif is_arch || is_cachy; then
            case "$jav" in
                8)
                    packages+=(jdk8-openjdk jre8-openjdk)
                    ;;
                11)
                    packages+=(jdk11-openjdk jre11-openjdk)
                    ;;
                17)
                    packages+=(jdk17-openjdk jre17-openjdk)
                    ;;
                21)
                    packages+=(jdk21-openjdk jre21-openjdk)
                    ;;
                24)
                    packages+=(jdk-openjdk jre-openjdk)
                    ;;
            esac
        fi
    done

    if (( ${#packages[@]} == 0 )); then
        die "No valid Java packages were selected."
    fi

    askpass
    pkg_install "${packages[@]}"
    info "$finishmsg"
}

java_in() {
    local chosen_javas
    local chosen_jav
    local -a javas=()
    local distro_group="other"

    if is_fedora || is_rhel; then
        distro_group="fedora_rhel"
    elif is_solus; then
        distro_group="solus"
    fi

    while true; do
        case "$distro_group" in
            fedora_rhel)
                chosen_javas=$(zenity --list --checklist \
                    --title="Java JDK" \
                    --column="" \
                    --column="$msg277" \
                    FALSE "Java 21 LTS" \
                    FALSE "Java 25 LTS" \
                    FALSE "Java Latest" \
                    --height=410 \
                    --width=300 \
                    --separator="|")
                ;;

            solus)
                chosen_javas=$(zenity --list --checklist \
                    --title="Java JDK" \
                    --column="" \
                    --column="$msg277" \
                    FALSE "Java 21 LTS" \
                    FALSE "Java 25 LTS" \
                    --height=410 \
                    --width=300 \
                    --separator="|")
                ;;

            *)
                chosen_javas=$(zenity --list --checklist \
                    --title="Java JDK" \
                    --column="" \
                    --column="$msg277" \
                    FALSE "Java 8 LTS" \
                    FALSE "Java 11 LTS" \
                    FALSE "Java 17 LTS" \
                    FALSE "Java 21 LTS" \
                    FALSE "Java Latest" \
                    --height=410 \
                    --width=300 \
                    --separator="|")
                ;;
        esac

        if (( $? != 0 )); then
            exit 100
        fi
        if [[ -z "$chosen_javas" ]]; then
            warn "Please select at least one Java version."
            continue
        fi
        IFS='|' read -ra javas <<< "$chosen_javas"

        for chosen_jav in "${javas[@]}"; do
            case "$chosen_jav" in
                "Java 8 LTS")
                    _jdk8="8"
                    ;;
                "Java 11 LTS")
                    _jdk11="11"
                    ;;
                "Java 17 LTS")
                    _jdk17="17"
                    ;;
                "Java 21 LTS")
                    _jdk21="21"
                    ;;
                "Java 25 LTS")
                    _jdk25="25"
                    ;;
                "Java Latest")
                    if [[ "$distro_group" == "fedora_rhel" ]]; then
                        _jdk_latest="latest"
                    else
                        _jdk25="25"
                    fi
                    ;;
            esac
        done
        jdk_install
        break
    done
}

java_in