#!/bin/sh

rpmbuild --define "_topdir `pwd`" --define "debug_package %{nil}" -ba SPECS/linuxtoys.spec
rpmbuild --define "_topdir `pwd`" --define "debug_package %{nil}" -bb SPECS/linuxtoys.spec

