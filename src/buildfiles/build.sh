#!/bin/sh

# CORE VARIABLES (DO NOT MODIFY) #

SCRIPT=()
RSCRIPT=""

# USER VARIABLES #

GITHUB_RUN=0
LINUXTOYS_VERSION=$(cat ../ver)
SUPPORTED_PACKAGE_MANAGERS=("dpkg" "pacman" "rpm")
ROOT_RUN="su -c '%s'"
ROOT_RUNNERS=("doas" "sudo")

# Check if the USER is a workflow builder.
if [ "$(whoami)" = "runner" ]; then
  GITHUB_RUN=1
fi

# Apply the root runner, otherwise it will fallback to `su -c ''`.
for root_runner in ${ROOT_RUNNERS[@]}; do
  if which ${root_runner} >/dev/null 2>&1; then ROOT_RUN="${root_runner} %s"; fi
done

# TOOL #

root_script()
{
  local c="$1"

  RSCRIPT=$(printf "${ROOT_RUN}" "${c}")

  return 0
}

script_constructor()
{
  local i=${#SCRIPT[@]}

  for arg in "$@"; do
    SCRIPT[$i]=${arg}
    i=$((i+1))
  done

  return 0
}

# DEB #

deb_prepare()
{
  local packages="build-essential devscripts"

  root_script "apt-get update" && script_constructor "${RSCRIPT}"
  root_script "apt-get install -y ${packages}" && script_constructor "${RSCRIPT}"

  return 0
}

deb_build()
{
  script_constructor "mkdir -p deb/linuxtoys/DEBIAN/opt/linuxtoys"
  script_constructor "mkdir -p deb/linuxtoys/DEBIAN/usr/share/applications"
  script_constructor "cp ../linuxtoys.sh deb/linuxtoys/DEBIAN/opt/linuxtoys"
  script_constructor "cp ../linuxtoys.png deb/linuxtoys/DEBIAN/opt/linuxtoys"
  script_constructor "cp ../LinuxToys.desktop deb/linuxtoys/DEBIAN/usr/share/applications"
  script_constructor "cp deb/control.dpkg deb/linuxtoys/DEBIAN/control"
  script_constructor "chmod 755 deb/linuxtoys/DEBIAN/postinst"
  script_constructor "dpkg-deb --build --root-owner-group deb/linuxtoys"
  script_constructor "cp deb/*.deb ./linuxtoys-${LINUXTOYS_VERSION}-1_amd64.deb"
}

# PKGBUILD #

pacman_prepare()
{
  local packages="bash curl wget libnewt base-devel git"

  if [ $GITHUB_RUN -eq 1 ]; then
    ROOT_RUN="%s"
    root_script "pacman -Syu --noconfirm" && script_constructor "${RSCRIPT}"
    root_script "useradd -m builder" && script_constructor "${RSCRIPT}"
    root_script "chown -R builder ." && script_constructor "${RSCRIPT}"
  fi

  root_script "pacman -S --needed --noconfirm ${packages}" && script_constructor "${RSCRIPT}"

  return 0
}

pacman_build()
{
  if [ $GITHUB_RUN -eq 1 ]; then
    script_constructor "su builder -c 'cd pkgbuild && makepkg -s --noconfirm'"
  else
    script_constructor "cd pkgbuild"
    script_constructor "makepkg -s --noconfirm"
    script_constructor "cd -"
  fi

  script_constructor "cp pkgbuild/*.pkg.tar.* ./"

  return 0
}

# RPM #

rpm_prepare()
{
  if [ $GITHUB_RUN -eq 1 ]; then
    local packages="rpm desktop-file-utils"
    root_script "apt-get update" && script_constructor "${RSCRIPT}"
    root_script "apt-get install -y ${packages}" && script_constructor "${RSCRIPT}"
  else
    printf "Insert rpm install\n"
  fi

  return 0
}

rpm_build()
{
  script_constructor "mkdir -p rpm/rpmbuild/BUILD"
  script_constructor "mkdir -p rpm/rpmbuild/RPMS"
  script_constructor "mkdir -p rpm/rpmbuild/SOURCES"
  script_constructor "mkdir -p rpm/rpmbuild/SRPMS"
  script_constructor "mkdir -p rpm/linuxtoys-${LINUXTOYS_VERSION}/usr/bin"
  script_constructor "mkdir -p rpm/linuxtoys-${LINUXTOYS_VERSION}/usr/share/applications"
  script_constructor "mkdir -p rpm/linuxtoys-${LINUXTOYS_VERSION}/usr/share/icons/hicolor/scalable/apps"
  script_constructor "cp ../linuxtoys.sh rpm/linuxtoys-${LINUXTOYS_VERSION}/usr/bin"
  script_constructor "cp ../linuxtoys.png rpm/linuxtoys-${LINUXTOYS_VERSION}/usr/share/icons/hicolor/scalable/apps"
  script_constructor "cp ../LinuxToys.desktop rpm/linuxtoys-${LINUXTOYS_VERSION}/usr/share/applications"
  script_constructor "pushd rpm"
  script_constructor "tar -cJf rpmbuild/SOURCES/linuxtoys-${LINUXTOYS_VERSION}.tar.xz linuxtoys-${LINUXTOYS_VERSION}"
  script_constructor "pushd rpmbuild"
  script_constructor "sh ./build.sh"
  script_constructor "popd"
  script_constructor "popd"
  script_constructor "cp rpm/rpmbuild/RPMS/x86_64/*.rpm ./linuxtoys-${LINUXTOYS_VERSION}-1_amd64.rpm"
  script_constructor "cp rpm/rpmbuild/SRPMS/*.src.rpm ./linuxtoys-${LINUXTOYS_VERSION}-1_amd64.src.rpm"
}

# RUN #

for package_manager in ${SUPPORTED_PACKAGE_MANAGERS[@]}; do
  if which ${package_manager[@]} >/dev/null 2>&1; then
    case ${package_manager} in
    dpkg)
      printf "Preparing DEB package...\n"
      if [ ! -f *.deb ]; then
        deb_prepare
        deb_build
      fi
      ;;
    pacman)
      printf "Preparing PKGBUILD package...\n"
      if [ ! -f *.pkg.tar.* ]; then
        pacman_prepare
        pacman_build
      fi
      ;;
    rpm)
      printf "Preparing RPM package...\n"
      if [ ! -f *.rpm ]; then
        rpm_prepare
        rpm_build
      fi
      ;;
    esac

  for c in "${SCRIPT[@]}"; do
    #echo "${c}"
    ${c}
  done
  SCRIPT=()
  printf "\n"

  fi
done

