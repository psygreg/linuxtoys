#!/bin/sh

su builder -c 'cd pkgbuild && makepkg -s --noconfirm'
