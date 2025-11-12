# [LinuxToys](https://linux.toys)
A collection of tools for Linux in a user-friendly way. To check all its features, pay the [Wiki](https://linux.toys/knowledgebase.html) a visit!

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="src/dark-lt.png">
  <img alt="LinuxToys Screenshot" src="src/light-lt.png">
</picture>

## Compatibility
As long as you're running their up-to-date stable versions:
- **Ubuntu** and derivatives
- **Debian** and derivatives
- **Arch Linux** and derivatives
- **Fedora** and derivatives
- **OpenSUSE** and derivatives
- **Atomic Fedora** and derivatives
- **Universal Blue** images like **Bazzite**, **Bluefin** and **Aurora**

## Usage
#### Install
1. Automatic installation:
```
curl -fsSL https://linux.toys/install.sh | bash
```

2. Manually run `install.sh` script:
```
curl -fsSLJO https://linux.toys/install.sh
chmod +x install.sh
./install.sh
```

3. Clone this repository <sup>*\*(recommended for developers)*</sup>

- First, make sure you have all necessary dependencies. Most of those should be already present in your system.
	- **Debian/Ubuntu**: `bash git curl wget zenity python3 python3-gi python3-requests libgtk-3-0 gir1.2-gtk-3.0 gir1.2-vte-2.91`
	- **Fedora/RHEL**: `bash git curl wget zenity python3 python3-gobject python3-requests gtk3 vte291`
	- **Arch Linux**: `bash git curl wget zenity python python-gobject python-requests gtk3 vte3`
	- **OpenSUSE**: `bash git curl wget zenity python3 python3-gobject python3-requests gtk3 libvte-2_91-0`

- Then, clone the repository with
```
git clone --depth=1 https://github.com/psygreg/linuxtoys.git
```

- Run
```
linuxtoys/p3/run.py
```

- Updating the app through this method is a simple
```
git pull
```

## Official Repositories
### [Ubuntu Launchpad](https://launchpad.net/~psygreg/+archive/ubuntu/linuxtoys) (PPA)
Can be added with:

```
sudo add-apt-repository ppa:psygreg/linuxtoys
sudo apt update
sudo apt install linuxtoys
```

### [Fedora COPR](https://copr.fedorainfracloud.org/coprs/psygreg/linuxtoys/)
Available packages: **AlmaLinux 10**, **Fedora 41** and **42**, **OpenSUSE Leap** and **Tumbleweed**, **RHEL 9** and **10**.

#### For non-immutable systems:
```
sudo dnf copr enable psygreg/linuxtoys
sudo dnf install linuxtoys
```

#### For Fedora atomic, the following commands are required to install the repository:
```
curl -fsSL https://copr.fedorainfracloud.org/coprs/psygreg/linuxtoys/repo/fedora-$(rpm -E %fedora)/psygreg-linuxtoys-fedora-$(rpm -E %fedora).repo | sudo tee /etc/yum.repos.d/psygreg-linuxtoys-fedora-$(rpm -E %fedora).repo
```
```
sudo rpm-ostree install linuxtoys
```

### [Arch User Repository - AUR](https://aur.archlinux.org/packages/linuxtoys-bin)
```
git clone --branch linuxtoys-bin --single-branch https://github.com/archlinux/aur.git /tmp/linuxtoys-bin
makepkg -fcCd OPTIONS=-debug -D /tmp/linuxtoys-bin
sudo pacman --noconfirm -U /tmp/linuxtoys-bin/linuxtoys-bin-*.tar.zst
```

## [Credits](https://linux.toys/credits.html)
