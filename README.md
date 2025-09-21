# [LinuxToys](https://linuxtoys.luminhost.xyz)
A collection of tools for Linux in a user-friendly way. To check all its features, pay the [Wiki](https://linuxtoys.luminhost.xyz/knowledgebase.html) a visit!

![LinuxToys](src/screenshot.png)

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
#### Use the `install.sh` script available in the latest of [Releases](https://github.com/psygreg/linuxtoys/releases).

Give it permission to run as a program through whichever file manager you choose, or with `chmod +x install.sh` through terminal, then run it and it will figure out the installation procedure for your operating system.

or automatic installation:

```shell
yes | sh -c "$(curl -fsSL https://raw.githubusercontent.com/psygreg/linuxtoys/master/install.sh)"
```

#### Download and install the **package for your distribution** from [Releases](https://github.com/psygreg/linuxtoys/releases):

For Arch Linux and derivatives, the terminal is required for this: `sudo pacman -U linuxtoys-<version>-1-x86_64.pacman`.

For `rpm-ostree`-based systems, it will also be needed: `rpm-ostree install linuxtoys-<version>-1.x86_64.rpm`. You may need to run `rpm-ostree remove linuxtoys` before using the install command to update the app due to limitations on how locally layered packages work - so it's recommended to use the COPR repository on those systems for your convenience.

#### Alternatively, run it directly from the method below.

### Git cloning
First, make sure you have all necessary dependencies. Most of those should be already present in your system.

- **Debian/Ubuntu**: `bash git curl wget zenity python3 python3-gi python3-requests libgtk-3-0 gir1.2-gtk-3.0 jq ssh-askpass`
- **Fedora/RHEL**: `bash git curl wget zenity python3 python3-gobject python3-requests gtk3 jq openssh-askpass`
- **Arch Linux**: `bash git curl wget zenity python python-gobject python-requests gtk3 x11-ssh-askpass`
- **OpenSUSE**: `bash git curl wget zenity python3 python3-gobject python3-requests gtk3 openssh-askpass`

Then, clone the repository with `git clone https://github.com/psygreg/linuxtoys.git`

To run the app, give `p3/run.py` execution permissions with `chmod +x p3/run.py` from the cloned folder, then run it with `./p3/run.py`.

Updating the app through this method is a simple `git pull` away.

## CLI Mode
LinuxToys has a CLI mode option for sysadmins and the like, which need something that can be automated quickly. To operate in this mode, all you have to do is getting the application through git cloning as mentioned above, then alter the `manifest.txt` file with the names of the scripts you wish to execute. After that, run LinuxToys with the CLI mode flag, like this: `LT_MANIFEST=1 ./p3/run.py` and it will pick up and execute the scripts of your choice. 

You may want to save your modified `manifest.txt` file separately for later use.

## Official Repositories
### [Ubuntu Launchpad](https://launchpad.net/~psygreg/+archive/ubuntu/linuxtoys) (PPA)
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

## [Credits](https://linuxtoys.luminhost.xyz/credits.html)
