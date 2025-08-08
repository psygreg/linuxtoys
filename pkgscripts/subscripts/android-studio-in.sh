#!/bin/bash

#check dependencies
depcheck () {

    if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
        local _packages=(libc6:i386 libncurses5:i386 libstdc++6:i386 lib32z1 libbz2-1.0:i386)
    elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
        local _packages=(zlib.i686 ncurses-libs.i686 bzip2-libs.i686)
    else
        nonfatal "$msg077"
        exit 1
    fi
    _install_

}

# install or update android studio
android_in () {

    if [ ! -f /opt/android-studio ]; then
        cd $HOME
        wget https://r7---sn-oxunxg8pjvn-bpbzd.gvt1.com/edgedl/android/studio/ide-zips/2024.3.2.15/android-studio-2024.3.2.15-linux.tar.gz
        tar -xvzf android-studio-2024.3.2.15-linux.tar.gz
        sudo cp -rf android-studio /opt/
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/android-studio/android-studio.desktop
        sudo cp android-studio.desktop /usr/share/applications/
        rm -rf android-studio
        rm android-studio.desktop
        rm android-studio-2024.3.2.15-linux.tar.gz
    else
        sudo rm -rf /opt/android-studio
        cd $HOME
        wget https://r7---sn-oxunxg8pjvn-bpbzd.gvt1.com/edgedl/android/studio/ide-zips/2024.3.2.15/android-studio-2024.3.2.15-linux.tar.gz
        tar -xvzf android-studio-2024.3.2.15-linux.tar.gz
        sudo cp -rf android-studio /opt/
        rm android-studio-2024.3.2.15-linux.tar.gz
        rm -rf android-studio
    fi

}

# runtime
. /etc/os-release
source /usr/bin/linuxtoys/linuxtoys.lib
_lang_
source /usr/bin/linuxtoys/${langfile}
depcheck
android_in