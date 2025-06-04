# linuxtoys
A collection of tools for Linux in a user-friendly way.

## Usage
- Install the proper package for your operating system from [Releases](https://github.com/psygreg/linuxtoys/releases) and run it from the applications menu.

### Arch Linux
- Download the PKGBUILD and `.install` files from [Releases](https://github.com/psygreg/linuxtoys/releases)
- Run `makepkg -si` on the folder you downloaded the file to install.

## Limitations
- **Shader Booster** only works in systems using the `bash` or `zsh` shells as default. 
- **GRUB-btrfs**, besides its obvious requirements, depends on `systemd-init` to enable boot snapshots and cleanup.
- **Lucidglyph** is only confirmed to work on **Gnome** and **Plasma** desktops. With all others, your mileage may vary.
- The **linux-cachyos** kernel port to Debian/Ubuntu-based systems may require its **LTO** setting changed to 'Full' or 'None' to work in some systems. *ThinLTO is only known to work in the standard Ubuntu-Gnome flavour and in Debian Testing, so far, although it is the optimal setting if it works for your system.*
- **LACT** is an overclocking tool. Use with caution.
- **PyEnv** only supports running in `bash` or `zsh` shells.
- **Godot 4 .NET** a.k.a. *GodotSharp* is not compatible with Arch-based operating systems, as there isn't a .NET SDK available from Microsoft officially for those.
- **Unity Hub** only supports **Debian**, **Ubuntu** and **Red Hat Enterprise Linux**, so its installer will only work on these systems.

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

## Contributing

To contribute with translations, you can fork this repo, add a new language file to the `resources/lang` folder and send a Pull Request. I can make the necessary adjustments to the program's code myself to accomodate new languages.

Other contributions can be made by forking, adding your changes and sending a Pull Request as well.

**All Pull Requests will be manually checked before approval.**

## Credits

- [Lucidglyph](https://github.com/maximilionus/lucidglyph/tree/v0.11.0) by **Maximilionus**
- [GRUB-btrfs](https://github.com/Antynea/grub-btrfs) by **Antynea**
- [Pipewire Audio Capture plugin for OBS Studio](https://github.com/dimtpap/obs-pipewire-audio-capture) by **Dimitris Papaioanou**
- [LACT](https://github.com/ilya-zlobintsev/LACT) by **Ilya Zlobintsev**
- [Easy Effects](https://github.com/wwmm/easyeffects) by **Wellington Wallace**
- [MakeResolveDeb](https://www.danieltufvesson.com/makeresolvedeb) by **Daniel Tufvesson**
- [Darktable](https://www.darktable.org)
- [Chaotic AUR](https://aur.chaotic.cx/)
- [The CachyOS Team](https://github.com/CachyOS/linux-cachyos)
- [Pyenv](https://github.com/pyenv)
- [NVM-sh](https://github.com/nvm-sh)
- [WiVRn](https://github.com/WiVRn)
- [Oversteer](https://github.com/berarma/oversteer) by **Bernat**
- And the Linux Community
