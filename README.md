# LinuxToys
A collection of tools for Linux in a user-friendly way. To check all its features, pay the [Wiki](https://github.com/psygreg/linuxtoys/wiki) a visit!

![LinuxToys](https://github.com/psygreg/linuxtoys/blob/66c0e9c3f99bcd7108a76407da84b8cba79f5387/src/screenshot.png)

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
### [Ubuntu Launchpad](https://launchpad.net/~psygreg/+archive/ubuntu/linuxtoys)
Can be added with:

`sudo add-apt-repository ppa:psygreg/linuxtoys && sudo apt update`

### [Fedora COPR](https://copr.fedorainfracloud.org/coprs/psygreg/linuxtoys/)
Available packages: **AlmaLinux 10**, **Fedora 41** and **42**, **OpenSUSE Leap** and **Tumbleweed**, **RHEL 9** and **10**.

#### For non-immutable systems:
`dnf copr enable psygreg/linuxtoys` 

#### For Fedora atomic, three commands are required to install the repository:
- `wget https://copr.fedorainfracloud.org/coprs/psygreg/linuxtoys/repo/fedora-$(rpm -E %fedora)/psygreg-linuxtoys-fedora-$(rpm -E %fedora).repo` 
- `sudo install -o 0 -g 0 psygreg-linuxtoys-fedora-$(rpm -E %fedora).repo /etc/yum.repos.d/psygreg-linuxtoys-fedora-$(rpm -E %fedora).repo` 
- `rpm-ostree refresh-md`

### [Arch User Repository - AUR](https://aur.archlinux.org/packages/linuxtoys-bin)
You may use the AUR helper of your choice to install it, with the package name `linuxtoys-bin`.

## Usage
- Download and install the package for your distribution; or
- Download and run the **AppImage** package from [Releases](https://github.com/psygreg/linuxtoys/releases) - now also available on **[AM Application Manager](https://github.com/ivan-hc/AM)!**
- Alternatively, run it directly from the method below.

### Git cloning
First, make sure you have all necessary dependencies. Most of those should be already present in your system.

- **Debian/Ubuntu**: `bash git curl wget zenity python3 python3-gi libgtk-3-0 gir1.2-gtk-3.0 jq`
- **Fedora/RHEL**: `bash git curl wget zenity python3 python3-gobject gtk3 jq`
- **Arch Linux**: `bash git curl wget zenity python python-gobject gtk3`
- **OpenSUSE**: `bash git curl wget zenity python3 python3-gobject gtk3`

Then, clone the repository with `git clone --single-branch --branch indev-5 https://github.com/psygreg/linuxtoys.git`

To run the app, give `p3/run.py` execution permissions with `chmod +x p3/run.py` from the cloned folder, then run it with `./p3/run.py`.

## Contributing

To contribute with translations, you can fork this repo, add a new language file to the `resources/lang` folder and send a Pull Request. I can make the necessary adjustments to the program's code myself to accomodate new languages.

Other contributions can be made by forking, adding your changes to the scripts in the `src` folder and sending a Pull Request as well.

**All Pull Requests will be manually checked before approval.**

## [Credits](https://github.com/psygreg/linuxtoys/wiki/Credits)
