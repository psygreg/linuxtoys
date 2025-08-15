# LinuxToys
A collection of tools for Linux in a user-friendly way. To check all its features, pay the [Wiki](https://github.com/psygreg/linuxtoys/wiki) a visit!

![LinuxToys](https://github.com/psygreg/linuxtoys/blob/dc32bbe9a5f6bd40fd30f409f13f33b3be3695ad/src/screenshot3.png)

## Compatibility
As long as you're running their up-to-date stable versions:
- **Ubuntu** and derivatives
- **Debian** and derivatives
- **Arch Linux** and derivatives
- **Fedora** and derivatives
- **OpenSUSE** and derivatives
- **Atomic Fedora** and derivatives
- **Universal Blue** images like **Bazzite**, **Bluefin** and **Aurora**

### Limitations & Warnings
- **Shader Booster** only works in systems using the `bash`, `zsh` or `fish` shells as default. 
- **GRUB-btrfs**, besides its obvious requirements, depends on `systemd-init` to enable boot snapshots and cleanup.
- **LACT** is an overclocking tool. Use with caution.
- **PyEnv** only supports running in `bash` or `zsh` shells.
- **Godot 4 .NET** a.k.a. *GodotSharp* is not compatible with Arch-based operating systems, as there isn't a .NET SDK available from Microsoft officially for those. The same is applicable to **Unity Hub**.

## Official Repositories
### [Fedora COPR](https://copr.fedorainfracloud.org/coprs/psygreg/linuxtoys/)
Available packages: **AlmaLinux 10**, **Fedora 41** and **42**, **OpenSUSE Leap** and **Tumbleweed**, **RHEL 9** and **10**.

`dnf copr enable psygreg/linuxtoys ` 

### [Arch User Repository - AUR](https://aur.archlinux.org/packages/linuxtoys-bin)
You may use the AUR helper of your choice to install it, with the package name `linuxtoys-bin`.

## Usage
- Download and install the package for your distribution; or
- Download and run the **AppImage** package from [Releases](https://github.com/psygreg/linuxtoys/releases) - now also available on **[AM Application Manager](https://github.com/ivan-hc/AM)!**
- Alternatively, run it directly from the method below.

### Git cloning
First, make sure you have all necessary dependencies. Most of those should be already present in your system.

- **Debian/Ubuntu**: `bash git curl wget zenity python3 python3-gi python3-gi-cairo libgtk-3-0 gir1.2-gtk-3.0 jq`
- **Fedora/RHEL**: `bash git curl wget zenity python3 python3-gobject python3-cairo-devel gtk3 jq`
- **Arch Linux**: `bash git curl wget zenity python python-gobject python-cairo gtk3`
- **OpenSUSE**: `bash git curl wget zenity python3 python3-gobject python3-gobject-cairo gtk3`

Then, clone the repository with `git clone --single-branch --branch indev-5 https://github.com/psygreg/linuxtoys.git`

To run the app, give `p3/run.py` execution permissions with `chmod +x p3/run.py` from the cloned folder, then run it with `./p3/run.py`.

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
- [xpadneo](https://github.com/atar-axis/xpadneo) by **Florian Dollinger**
- [Chaotic AUR](https://aur.chaotic.cx/)
- [Homebrew](https://brew.sh/)
- [The CachyOS Team](https://github.com/CachyOS/linux-cachyos)
- [Pyenv](https://github.com/pyenv)
- [NVM-sh](https://github.com/nvm-sh)
- [WiVRn](https://github.com/WiVRn)
- [Oversteer](https://github.com/berarma/oversteer) by **Bernat**
- [WinApps](https://github.com/winapps-org/winapps)
- [Distrobox-Adv-Br](https://github.com/pedrohqb/distrobox-adv-br) by **'pedrohqb'**
- And the Linux Community
