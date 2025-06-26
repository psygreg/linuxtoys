pkgname='linuxtoys'
pkgver='3.1'
pkgrel=1
arch=('x86_64')
depends=(bash curl wget libnewt base-devel git)
makedepends=()
conflicts=(linuxtoys)
provides=("linuxtoys=$pkgver")
install=linuxtoys.install
source=("https://github.com/psygreg/linuxtoys/releases/download/${pkgver}/linuxtoys-${pkgver}.tar.xz")
sha256sums=('295a365ba08cd5a96f1c059c7c18917be2d27a1df60d160e0226e9bade565752')

package() {

    mkdir -p ${pkgdir}/usr
    cp -rf ${srcdir}/linuxtoys-${pkgver}/{bin,share} ${pkgdir}/usr
    chmod +x "${pkgdir}/usr/bin/linuxtoys.sh"

}
