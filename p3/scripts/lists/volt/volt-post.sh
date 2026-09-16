#!/usr/bin/env bash

cd "$LINUXTOYS_MAKE_DIR" || die "failed to enter make directory"
make flatpak
make flatpak-install-user
pkg_fromfile build/bundles/org.freedesktop.Platform.VulkanLayer.volt-23.08.flatpak
pkg_fromfile build/bundles/org.freedesktop.Platform.VulkanLayer.volt-24.08.flatpak
pkg_fromfile build/bundles/org.freedesktop.Platform.VulkanLayer.volt-25.08.flatpak
