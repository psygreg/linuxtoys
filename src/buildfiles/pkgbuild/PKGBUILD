pkgname='linuxtoys'
pkgver='3.2'
pkgrel=1
arch=('x86_64')
depends=(bash curl wget libnewt base-devel git)
makedepends=()
conflicts=(linuxtoys)
provides=("linuxtoys=$pkgver")
install=linuxtoys.install
source=("https://github.com/psygreg/linuxtoys/releases/download/${pkgver}/linuxtoys-${pkgver}.tar.xz")
sha256sums=('b9b82375995b24c42c64841b33d3162ffb9511653008e525086c87678a7036a2')

package() {

    mkdir -p ${pkgdir}/usr
    cp -rf ${srcdir}/linuxtoys-${pkgver}/{bin,share} ${pkgdir}/usr
    chmod +x "${pkgdir}/usr/bin/linuxtoys.sh"

}
