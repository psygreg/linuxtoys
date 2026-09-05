#!/bin/bash
# name: Marmalade
# description: marmalade_desc
# icon: marmalade.svg
# repo: https://github.com/RanAwaySuccessfully/marmalade
# compat: !suse, !solus

# dependencies
askpass
if is_fedora || is_rhel || is_ostree; then
    call_script codecfix
    pkg_install --ostreecheck libv4l gtk4
elif is_ubuntu || is_debian; then
    pkg_install ffmpeg libgtk-4 libv4l-0t64
elif is_arch || is_cachy; then
    pkg_install v4l-utils ffmpeg gtk4
fi
pkg_install xdg-utils pciutils

ASSETS=("marmalade.zip" "kalidokit.zip")
FFMPEG_VER=$(ffmpeg -version | awk '/^ffmpeg version/ {print $3}' | cut -d'.' -f1)
case $FFMPEG_VER in
    4|5|6|7|8) ASSETS+=(ffmpeg"$FFMPEG_VER"_plugin.so) ;;
    *) warn "Unsupported ffmpeg version. Marmalade may not work with webcams that use certain video codec outputs." ;;
esac
DEST="$HOME/.local/linuxtoys/marmalade"
TAG=$(curl -sL "https://api.github.com/repos/RanAwaySuccessfully/marmalade/releases/latest" | grep -Po '"tag_name":\s*"\K[^"]+')
if [[ -z $TAG ]]; then
    die "Could not determine latest tag."
fi

prep_tmp_noram
for ASSET in "${ASSETS[@]}"; do
    wget "https://github.com/RanAwaySuccessfully/marmalade/releases/download/${TAG}/${ASSET}" || die "Failed to fetch file $ASSET"
done
wget https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task || \
    die "Failed to fetch face_landmarker"
wget https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task || \
    die "Failed to fetch pose_landmarker"
prep_dir "$DEST"
prep_dir "$DEST/tasks"
unzip -d "$DEST" marmalade.zip
unzip -d "$DEST" kalidokit.zip
move_ "ffmpeg${FFMPEG_VER}_plugin.so" "$DEST"
move_ face_landmarker.task "$DEST/tasks"
move_ pose_landmarker_lite.task "$DEST/tasks"
chmod +x "$DEST/marmalade"
chmod +x "$DEST/kalidokit-bin"

timeout 10 ./"$DEST/marmalade" # finish installation process following upstream

xdg-open "https://github.com/RanAwaySuccessfully/marmalade#connecting"
info "$finishmsg"
