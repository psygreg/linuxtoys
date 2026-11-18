# LinuxToys CI image for the aarch64 Arch packaging legs (arch-pkg, appimage).
#
# The official Arch Linux images (Docker Hub, ghcr.io, quay.io) publish
# linux/amd64 only, so GitHub's ubuntu-24.04-arm runners cannot pull them.
# This image is built from the signature-verified Arch Linux ARM aarch64
# rootfs instead; the release workflow builds, pushes and pins it by digest
# on every run (job `ci-image` in .github/workflows/release.yml).
#
# The build context must contain ArchLinuxARM-aarch64-latest.tar.gz.
FROM scratch

ADD ArchLinuxARM-aarch64-latest.tar.gz /

# The rootfs ships ALARM's trusted key lists but no initialized pacman
# keyring; without this the packaging jobs' `pacman -Syu` fails signature
# verification (ALARM's pacman.conf sets SigLevel = Required).
RUN pacman-key --init && pacman-key --populate archlinuxarm

LABEL org.opencontainers.image.title="linuxtoys-ci-archlinux-aarch64" \
      org.opencontainers.image.description="Arch Linux ARM aarch64 rootfs for the LinuxToys release packaging jobs" \
      org.opencontainers.image.source="https://github.com/psygreg/linuxtoys"

CMD ["/bin/bash"]
