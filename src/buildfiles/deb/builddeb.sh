#!/bin/bash
# ask version to package
lt_version=$(zenity --entry --title="Debian Builder" --text="Version number:"  --entry-text "" --height=300 --width=300)
# set up dir structure
mkdir -p linuxtoys_${lt_version}.orig/usr || echo "fatal error 1" && sleep 3 && exit 1
mv linuxtoys-* linuxtoys-${lt_version} || echo "fatal error 2" && sleep 3 && exit 2
cp -r linuxtoys-${lt_version}/debian/usr/* linuxtoys_${lt_version}.orig/usr
tar -cJf linuxtoys_${lt_version}.orig.tar.xz linuxtoys_${lt_version}.orig/
# set changelog file
day=$(date +%d)
day_abbr=$(date +%a)
month=$(date +%b)  
year=$(date +%Y)
changelog_line="linuxtoys (${lt_version}-1) noble; urgency=medium"
changelog_line2=" -- Victor Gregory <psygreg@pm.me>  ${day_abbr}, ${day} ${month} ${year} 3:00:47 -0300"
sed -i "1c\\$changelog_line" linuxtoys-${lt_version}/debian/changelog
sed -i "5c\\$changelog_line2" linuxtoys-${lt_version}/debian/changelog
# build package
cd linuxtoys-${lt_version} || echo "fatal error 3" && sleep 3 && exit 3
debuild -us -uc # this builder script requires devscripts!!
