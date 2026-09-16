#!/usr/bin/env bash

cd "$LINUXTOYS_MAKE_DIR" || die "failed to enter make directory"
make flatpak-install-user
_append_transmap "flatpak org.freedesktop.Platform.VulkanLayer.volt/x86_64/23.08"
_append_transmap "flatpak org.freedesktop.Platform.VulkanLayer.volt/x86_64/24.08"
_append_transmap "flatpak org.freedesktop.Platform.VulkanLayer.volt/x86_64/25.08"
