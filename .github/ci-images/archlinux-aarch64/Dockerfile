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

# pacman 7.x downloads run inside a sandbox: a Landlock filesystem
# restriction, a syscall filter and a privilege drop to the `alpm` user.
# All three fail in restricted container environments - on GitHub's arm64
# runners as "the Landlock ruleset could not be applied: Operation not
# permitted" followed by "switching to sandbox user 'alpm' failed!". Arch's
# own official Docker images ship the same mitigation (their pacman.conf
# enables DisableSandboxFilesystem). Disable every sandbox component here
# and comment DownloadUser so no setuid is attempted either: downloads run
# as root and package signature verification (SigLevel = Required, against
# the keyring initialized below) is unaffected.
RUN sed -i -E \
      -e 's/^[[:space:]]*#?[[:space:]]*DisableSandbox[[:space:]]*$/DisableSandbox/' \
      -e 's/^[[:space:]]*#?[[:space:]]*DisableSandboxFilesystem[[:space:]]*$/DisableSandboxFilesystem/' \
      -e 's/^[[:space:]]*#?[[:space:]]*DisableSandboxSyscalls[[:space:]]*$/DisableSandboxSyscalls/' \
      -e 's/^[[:space:]]*DownloadUser[[:space:]]*=.*$/#&/' \
      /etc/pacman.conf && \
    pacman-key --init && pacman-key --populate archlinuxarm

# ALARM's makepkg.conf keeps the pre-zstd PKGEXT='.pkg.tar.xz', so makepkg
# would emit linuxtoys-<v>-1-aarch64.pkg.tar.xz while the release pipeline
# (and Arch's own x86_64 package naming) expects .pkg.tar.zst; the
# zstd binary is already in the rootfs. Normalize to Arch's standard.
RUN sed -i "s|^PKGEXT=.*|PKGEXT='.pkg.tar.zst'|" /etc/makepkg.conf

LABEL org.opencontainers.image.title="linuxtoys-ci-archlinux-aarch64" \
      org.opencontainers.image.description="Arch Linux ARM aarch64 rootfs for the LinuxToys release packaging jobs" \
      org.opencontainers.image.source="https://github.com/psygreg/linuxtoys"

CMD ["/bin/bash"]
