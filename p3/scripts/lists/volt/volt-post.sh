#!/usr/bin/env bash
# The external make target installs Flatpak bundles without a read-only native
# payload preflight. Refuse until that build route is qualified; never record
# guessed x86 branches or silently substitute a different remote/build.
die "Volt Flatpak extension builds are not yet architecture-qualified"
