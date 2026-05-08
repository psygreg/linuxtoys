#!/bin/bash
# name: Java OpenJDK
# version: 1.0
# description: java_desc
# icon: java.svg

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# functions
jdk_install () {
    local javas=($_jdk8 $_jdk11 $_jdk17 $_jdk21 $_jdk24)
    local packages=()
    for jav in "${javas[@]}"; do
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            packages+=(openjdk-${jav}-jdk openjdk-${jav}-jre)
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
            if [ $jav == "8" ]; then
                packages+=(java-1.8.0-openjdk java-1.8.0-openjdk-devel)
                continue
            fi
            packages+=(java-${jav}-openjdk java-${jav}-openjdk-devel)
        elif [[ "$ID_LIKE" == *suse* ]]; then
            packages+=(java-${jav}-openjdk java-${jav}-openjdk-devel)
        elif is_solus; then
            if [ "$jav" != "8" ] && [ "$jav" != "24" ]; then
                packages+=(openjdk-${jav})
            else
                zenwrn "Java version ${jav} is not available in Solus repositories. Skipping."
            fi
        fi
    done

    if [ ${#packages[@]} -eq 0 ]; then
        fatal "No valid Java packages were selected."
    fi

    sudo_rq
    pkg_install "${packages[@]}"

    if ! command -v java >/dev/null 2>&1; then
        fatal "Java installation finished but 'java' command is not available."
    fi

    zeninf "$msg018"
}
java_in () {
    local search_java
    local jav
    local chosen_javas
    local chosen_jav
    local javas
    declare -a search_java=(
        "Java 8 LTS"
        "Java 11 LTS"
        "Java 17 LTS"
        "Java 21 LTS"
        "Java 24 Latest"
    )

    while true; do
        chosen_javas=$(zenity --list --checklist --title="Java JDK" \
        	--column="" \
        	--column="$msg277" \
            FALSE "Java 8 LTS" \
            FALSE "Java 11 LTS" \
            FALSE "Java 17 LTS" \
            FALSE "Java 21 LTS" \
            FALSE "Java 24 Latest" \
            --height=410 --width=300 --separator="|")

        if [ $? -ne 0 ]; then
            exit 100
        fi

        IFS='|' read -ra javas <<< "$chosen_javas"

        if [ -z "$chosen_javas" ]; then
            zenwrn "Please select at least one Java version."
            continue
        fi

        for jav in "${search_java[@]}"; do
            for chosen_jav in "${javas[@]}"; do
                if [[ "$chosen_jav" == "$jav" ]]; then
                    case $jav in
                        "Java 8 LTS") _jdk8="8" ;;
                        "Java 11 LTS") _jdk11="11" ;;
                        "Java 17 LTS") _jdk17="17" ;;
                        "Java 21 LTS") _jdk21="21" ;;
                        "Java 24 Latest") _jdk24="24" ;;
                    esac
                fi
            done
        done

        jdk_install
        break
    done
}
java_in
