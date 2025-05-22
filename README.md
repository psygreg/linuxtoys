# linuxtoys
A collection of tools for Linux in a user-friendly way.

## Usage
- Install the proper package for your operating system from [Releases](https://github.com/psygreg/linuxtoys/releases) and run it from the applications menu.

### Arch Linux
- Download the PKGBUILD and `.install` files from [Releases](https://github.com/psygreg/linuxtoys/releases)
- Run `makepkg -si` on the folder you downloaded the file to install.

## Building from source
### .deb package
This will require `debuild`, obtained from the `devscripts` package..

- Clone the repo.
- Open terminal on `linuxtoys-deb/linuxtoys-1.2`
- Run `debuild -S` for .changes file or `debuild -us -uc` for a .deb package.

### .rpm package
Requires `rpmbuild`.

- Clone the repo.
- Open terminal on the `rpmbuild` subdirectory.
- `rpmbuild -bb SPECS/linuxtoys.spec`
