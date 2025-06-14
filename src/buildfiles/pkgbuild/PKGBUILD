pkgname='linuxtoys'
pkgver='3.0'
pkgrel=1
arch=('x86_64')
depends=(bash curl wget libnewt base-devel git)
makedepends=()
conflicts=(linuxtoys)
provides=("linuxtoys=$pkgver")
install=linuxtoys.install
source=("https://github.com/psygreg/linuxtoys/releases/download/${pkgver}/linuxtoys-${pkgver}.tar.xz")
sha256sums=('61818e476b8787162b53d2a903f9ba142790e17eb29f0878b3550e789988c571')

package() {

    mkdir -p ${pkgdir}/usr
    cp -rf ${srcdir}/linuxtoys-${pkgver}/{bin,share} ${pkgdir}/usr
    chmod +x "${pkgdir}/usr/bin/linuxtoys.sh"

}
