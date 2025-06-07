# LinuxToys
A collection of tools for Linux in a user-friendly way.

![LinuxToys](https://github.com/psygreg/linuxtoys/blob/42463f6539d54f710ec2a915aa85ee1a68b7413a/src/scrnshot.png)

## Usage
- Install the proper package for your operating system from [Releases](https://github.com/psygreg/linuxtoys/releases) and run it from the applications menu.

### Arch Linux
- Download the PKGBUILD and `.install` files from [Releases](https://github.com/psygreg/linuxtoys/releases)
- Run `makepkg -si` on the folder you downloaded the file to install.

## Dependencies

Requires `curl`, `wget`, `git`, `bash` and `alacritty`. Alacritty should be available in most distros, but for the ones that it isn't, you can either install it following the [instructions](https://github.com/alacritty/alacritty/blob/master/INSTALL.md) or force-install ignoring dependencies through terminal, as it is only required for the internet updater to work.

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
- Open terminal on `src/buildfiles/deb/linuxtoys*`
- Run `debuild -S` for .changes file or `debuild -us -uc` for a .deb package.

### .rpm package
Requires `rpmbuild`.

- Clone the repo.
- Open terminal on the `src/buildfiles/rpm/rpmbuild` subdirectory.
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
- [StreamController](https://github.com/StreamController/StreamController) by **'Core447'**
- [MakeResolveDeb](https://www.danieltufvesson.com/makeresolvedeb) by **Daniel Tufvesson**
- [Darktable](https://www.darktable.org)
- [Foliate](https://johnfactotum.github.io/foliate) by **John Factotum**
- [Custom Wine Builds](https://github.com/NelloKudo/WineBuilder) by **'NelloKudo'**
- [Chaotic AUR](https://aur.chaotic.cx/)
- [The CachyOS Team](https://github.com/CachyOS/linux-cachyos)
- [Pyenv](https://github.com/pyenv)
- [NVM-sh](https://github.com/nvm-sh)
- [WiVRn](https://github.com/WiVRn)
- [Oversteer](https://github.com/berarma/oversteer) by **Bernat**
- And the Linux Community
