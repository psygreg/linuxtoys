#!/bin/bash
# ask version to package
read -p "Version number: " lt_version
# set up dir structure
mkdir -p linuxtoys_$lt_version.orig/usr
mv linuxtoys-* linuxtoys-$lt_version 
cp -rf linuxtoys-$lt_version/debian/usr/* linuxtoys_$lt_version.orig/usr
tar -cJf linuxtoys_$lt_version.orig.tar.xz linuxtoys_$lt_version.orig/
# set changelog file
day=$(date +%d)
day_abbr=$(LC_TIME=C date +%a)  # This will always be in English
month=$(LC_TIME=C date +%b)
year=$(date +%Y)
changelog_line="linuxtoys (${lt_version}-1) noble; urgency=medium"
changelog_line2=" -- Victor Gregory <psygreg@pm.me>  ${day_abbr}, ${day} ${month} ${year} 3:00:47 -0300"
sed -i "1c\\$changelog_line" linuxtoys-${lt_version}/debian/changelog
sed -i "5c\\$changelog_line2" linuxtoys-${lt_version}/debian/changelog
# build package
cd linuxtoys-${lt_version}
debuild -us -uc # this builder script requires devscripts!!
echo "All done" && sleep 3 && exit 0
