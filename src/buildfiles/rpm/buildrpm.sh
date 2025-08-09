#!/bin/bash
# ask version to package
read -p "Version number: " lt_version
# set up directory and tarball it
mv linuxtoys-* linuxtoys-${lt_version} || echo "fatal error 2" && sleep 3 && exit 2
tar -cJf linuxtoys_${lt_version}.tar.xz linuxtoys_${lt_version}/
# set up rpmbuild
cp linuxtoys_${lt_version}.tar.xz rpmbuild/SOURCES
day=$(date +%d)
day_abbr=$(date +%a)
month=$(date +%b)  
year=$(date +%Y)
specfile_line="Version:        ${lt_version}"
specfile_line2="* ${day_abbr} ${month} ${day} ${year} Victor Gregory <psygreg@pm.me> - ${lt_version}"
sed -i "2c\\$specfile_line" rpmbuild/SPECS/linuxtoys.spec
sed -i "57c\\$specfile_line2" rpmbuild/SPECS/linuxtoys.spec
# build
cp -r rpmbuild $HOME # only works with this setup on Silverblue, which is what I use
cd $HOME/rpmbuild || echo "fatal error 1" && sleep 3 && exit 1
rpmbuild -ba SPECS/linuxtoys.spec
echo "All done" && sleep 3 && exit 0