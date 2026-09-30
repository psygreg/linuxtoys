#!/usr/bin/env bash

prep_tmp_noram
askpass

curl -sL https://github.com/utajum/g-helper-linux/releases/download/v1.0.93/90-ghelper.rules -o 90-ghelper.rules
prep_create /etc/udev/rules.d/90-ghelper.rules
copy_ -f 90-ghelper.rules /etc/udev/rules.d/
sudo_ udevadm control --reload-rules && sudo_ udevadm trigger
