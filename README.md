# LinuxToys
A collection of tools for Linux in a user-friendly way. For Fedora-based and Universal Blue immutable systems, see [LinuxToys Atom](https://github.com/psygreg/linuxtoys-atom). To check all its features, pay the [Wiki](https://github.com/psygreg/linuxtoys/wiki) a visit!

![LinuxToys](https://github.com/psygreg/linuxtoys/blob/dc32bbe9a5f6bd40fd30f409f13f33b3be3695ad/src/screenshot3.png)

## Compatibility
### AppImage
- **Debian 13 onwards** or **Sid** and derivatives
- **Fedora 42** and derivatives (non-atomic)
- **OpenSUSE Slowroll/Tumbleweed** and derivatives
### Packages or direct terminal usage
- **Ubuntu** and derivatives
- **Debian >12** and derivatives
- **Arch Linux** and derivatives
- **Fedora** and derivatives (non-atomic)
- **OpenSUSE** (any) and derivatives

### Limitations
- The **CachyOS systemd configurations** and **linux-psycachy** kernel may not work as intended on systems with package bases older than ***Debian Trixie***. This also applies for the **Optimized Defaults**.
- **Shader Booster** only works in systems using the `bash` or `zsh` shells as default. 
- **GRUB-btrfs**, besides its obvious requirements, depends on `systemd-init` to enable boot snapshots and cleanup.
- **Lucidglyph** is only confirmed to work on **Gnome** and **Plasma** desktops. With all others, your mileage may vary.
- The **linux-cachyos** kernel port to Debian/Ubuntu-based systems may require its **LTO** setting changed to 'Full' or 'None' to work in some systems. *ThinLTO is only known to work in the standard Ubuntu-Gnome flavour and in Debian Testing, so far, although it is the optimal setting if it works for your system.*
- **LACT** is an overclocking tool. Use with caution.
- **PyEnv** only supports running in `bash` or `zsh` shells.
- **Godot 4 .NET** a.k.a. *GodotSharp* is not compatible with Arch-based operating systems, as there isn't a .NET SDK available from Microsoft officially for those.
- **Unity Hub** only supports **Debian**, **Ubuntu** and **Red Hat Enterprise Linux**, so its installer will only work on these systems.

## Official Repositories
### [Fedora COPR](https://copr.fedorainfracloud.org/coprs/psygreg/linuxtoys/)
Available packages: **AlmaLinux 10**, **Fedora 41** and **42**, **OpenSUSE Leap** and **Tumbleweed**, **RHEL 9** and **10**.

`dnf copr enable psygreg/linuxtoys ` 

### [Arch User Repository - AUR](https://aur.archlinux.org/packages/linuxtoys-bin)
You may use the AUR helper of your choice to install it, with the package name `linuxtoys-bin`.

## Usage
- Download and install the package for your distribution; or
- Download and run the **AppImage** package from [Releases](https://github.com/psygreg/linuxtoys/releases) - now also available on **[AM Application Manager](https://github.com/ivan-hc/AM)!**
- Alternatively, run it directly from source with the direct terminal command.

### Direct command
Install dependencies then paste the command into your terminal to get the script from the source.
#### Dependencies
`bash curl git wget zenity jq`
#### Stable branch
```bash
curl -fsSL https://raw.githubusercontent.com/psygreg/linuxtoys/main/src/linuxtoys.sh | bash
```

## Contributing

To contribute with translations, you can fork this repo, add a new language file to the `resources/lang` folder and send a Pull Request. I can make the necessary adjustments to the program's code myself to accomodate new languages.

Other contributions can be made by forking, adding your changes to the scripts in the `src` folder and sending a Pull Request as well.

**All Pull Requests will be manually checked before approval.**

## Credits

- [Lucidglyph](https://github.com/maximilionus/lucidglyph/tree/v0.11.0) by **Maximilionus**
- [GRUB-btrfs](https://github.com/Antynea/grub-btrfs) by **Antynea**
- [Pipewire Audio Capture plugin for OBS Studio](https://github.com/dimtpap/obs-pipewire-audio-capture) by **Dimitris Papaioanou**
- [LACT](https://github.com/ilya-zlobintsev/LACT) by **Ilya Zlobintsev**
- [Easy Effects](https://github.com/wwmm/easyeffects) by **Wellington Wallace**
- [Mission Center](https://missioncenter.io)
- [StreamController](https://github.com/StreamController/StreamController) by **'Core447'**
- [PhotoGIMP](https://github.com/Diolinux/PhotoGIMP) by **'Diolinux'**
- [GPU Screen Recorder](https://git.dec05eba.com/?p=about) by **'dec05eba'**
- [MakeResolveDeb](https://www.danieltufvesson.com/makeresolvedeb) by **Daniel Tufvesson**
- [DaVinciBox](https://github.com/zelikos/davincibox) by **Patrick Csikos**
- [Darktable](https://www.darktable.org)
- [Foliate](https://johnfactotum.github.io/foliate) by **John Factotum**
- [Custom Wine Builds](https://github.com/NelloKudo/WineBuilder) by **'NelloKudo'**
- [LSFG-VK](https://github.com/PancakeTAS/lsfg-vk) by **'PancakeTAS'**
- [auto-cpufreq](https://github.com/AdnanHodzic/auto-cpufreq) by **Adnan Hodzic**
- [Touchégg](https://github.com/JoseExposito/touchegg) by **José Expósito**
- [Vinegar](https://vinegarhq.org/Home/index.html) by **the VinegarHQ team**
- [Chaotic AUR](https://aur.chaotic.cx/)
- [The CachyOS Team](https://github.com/CachyOS/linux-cachyos)
- [Pyenv](https://github.com/pyenv)
- [NVM-sh](https://github.com/nvm-sh)
- [WiVRn](https://github.com/WiVRn)
- [Oversteer](https://github.com/berarma/oversteer) by **Bernat**
- [WinApps](https://github.com/winapps-org/winapps)
- And the Linux Community
