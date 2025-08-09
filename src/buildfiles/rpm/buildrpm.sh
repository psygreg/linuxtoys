#!/bin/bash
# ask version to package
read -p "Version number: " lt_version
# set up directory and tarball it
mv linuxtoys-* linuxtoys-${lt_version}
tar -cJf linuxtoys-${lt_version}.tar.xz linuxtoys-${lt_version}/
# set up rpmbuild
cp linuxtoys-${lt_version}.tar.xz rpmbuild/SOURCES
day=$(date +%d)
day_abbr=$(LC_TIME=C date +%a)  # This will always be in English
month=$(LC_TIME=C date +%b)
year=$(date +%Y)
specfile_line="Version:        ${lt_version}"
specfile_line2="* ${day_abbr} ${month} ${day} ${year} Victor Gregory <psygreg@pm.me> - ${lt_version}"
sed -i "2c\\$specfile_line" rpmbuild/SPECS/linuxtoys.spec
sed -i "57c\\$specfile_line2" rpmbuild/SPECS/linuxtoys.spec
# build
cp -r rpmbuild $HOME # only works with this setup on Silverblue, which is what I use
cd $HOME/rpmbuild
rpmbuild -ba SPECS/linuxtoys.spec
echo "All done" && sleep 3 && exit 0