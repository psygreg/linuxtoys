# Contributing

Thank you for your interest in contributing to LinuxToys! This project aims to provide a collection of tools for Linux in a user-friendly way, making powerful functionality accessible to all users.

## Development Priorities

When contributing to LinuxToys, please keep these core priorities in mind, listed in order of importance:

### 1. Safety and Privacy First
- **User safety and privacy must always be the top priority**
- All scripts and tools should be thoroughly tested and reviewed
- Never implement features that could compromise user data or system security
- Clearly document any potential risks or system changes
- Follow secure coding practices and validate all user inputs

### 2. User Friendliness and Accessibility
- Design with the average computer user in mind
- Provide clear, intuitive interfaces
- Include helpful descriptions and guidance for all features, while keeping it straight to the point
- Ensure accessibility for users with different technical skill levels
- Use plain language in user-facing text and error messages
- Choose installation methods based upon their functionality and reliability above all

### 3. Reliability and Self-Sufficiency
- **All features must work as intended without requiring additional workarounds from the user**
- Tools should handle edge cases gracefully
- Provide clear error messages when something goes wrong
- Test across supported distributions and versions
- Ensure dependencies are properly managed and documented

### 4. CLI Tool Restrictions
- **Command-line interfaces should be restricted to developer and sysadmin use cases**
- The average computer user doesn't know or want to deal with terminal emulators
- CLI-only features should be restricted to Developer and System Administration menus

## Contribution Guidelines

- All Pull Requests will be manually reviewed before approval
- Ensure your contributions align with the development priorities listed above
- Test your changes across different Linux distributions when possible
- Follow the existing code style and structure
- Document any new features or significant changes

## Getting Started

1. Review the [Cheat Sheet](https://github.com/psygreg/linuxtoys/?tab=contributing-ov-file#cheat-sheet)
2. Fork the repository and create a feature branch
3. Make your changes following the development priorities
4. Test thoroughly across supported systems
5. Submit a Pull Request with a clear description of your changes

We appreciate your contributions to making Linux more accessible and user-friendly for everyone!

# Cheat Sheet

This is a quick and easy guide to LinuxToys' libraries and features meant for general use, made to streamline scripts and make them work with the app's features more tightly, like the **Action Registry** and atomic transactions. You can always come back for a refresher if you need!

## Sourcing bash libraries

```
source "$SCRIPT_DIR/libs/linuxtoys.lib"
```
Replace `linuxtoys.lib` with `helpers.lib` if you need a function from it. `helpers.lib` automatically sources `linuxtoys.lib`.

### `linuxtoys.lib`

#### Dialogs 
- `zeninf "$message"`: informational dialog, displaying a message to the user through zenity if in GUI mode or echoing on terminal.
- `zenask "$title" "$message"`: question dialog, displaying a message and requiring a *Yes/No* user response with zenity if in GUI mode or `read` on terminal. Returns 0 if response is *Yes* or 1 if response is *No*.
- `zenwrn "$message"`: warning dialog, displaying a message to the user through zenity if in GUI mode or echoing on terminal.
- `nonfatal "$message"`: warning dialog, displaying a message to the user through zenity if in GUI mode or echoing on terminal and returning code 1.
- `fatal "$message"`: fatal error dialog, displaying a message to the user through zenity if in GUI mode or echoing on terminal and terminating the script with code 1, triggering an automatic reversion of any changes made.
- `sudo_rq`: requests privilege elevation, after which all commands called with `sudo` will properly authenticate. This should only be used when this is needed, and `sudo` should only be called in commands that need it. Has error handling calling `fatal`.

#### System and Hardware Detection
All the following functions return 0 when positive or 1 when negative.

- `is_debian`: detects *Debian* and its derivatives that are not related to *Ubuntu*. 
- `is_ubuntu`: detects *Ubuntu* and its derivatives.
- `is_zorin`: detects *ZorinOS*. Created due to this distro often demanding workarounds not applicable to upstream *Ubuntu*.
- `is_arch`: detects *Arch Linux* and its derivatives, except for *CachyOS*.
- `is_cachy`: detects *CachyOS*. Created due to this distro often not demanding as many steps to certain tasks as *Arch Linux* would.
- `is_fedora`: detects **non-atomic** *Fedora* and its derivatives.
- `is_ostree`: detects **atomic** *Fedora* and its derivatives.
- `is_rhel`: detects *Red Hat Enterprise Linux* and similars.
- `is_solus`: detects *Solus*.

- `is_systemd`: detects if the host OS init system is *SystemD*. Created due to some features not being applicable to systems with other init systems.

- `is_amd`: detects *AMD* graphics cards. Will also detect iGPUs.
- `is_intel`: detects *Intel* graphics cards. Will also detect iGPUs, and sets the `intel_arc` variable if any of the GPUs detected is *Alchemist* or *Battlemage*-series.
- `is_nvidia`: detects *Nvidia* graphics cards. Will also detect iGPUs.

#### File and Directory Operations
All the following functions have error handling calling `fatal`.

- `prep_create`: creates a placeholder file on target. Should be used before any new files that will be created to register the file creation to the transaction map, and parses multiple arguments.
- `prep_edit`: copies the target to be edited to a `.bak` file. Should be used before any modifications to files to register the occurrence to the transaction map, and parses multiple arguments.
- `prep_dir`: creates a directory on target. Should be used before any new directories that will be needed to register their creation to the transaction map, and parses multiple arguments.
- `prep_dir_edit`: copies the target directory to be edited to a `.bak` directory. Should be used before any larger modifications to several files within directories to register the occurrence to the transaction map, and parses multiple arguments.
- `prep_tmp`: prepares a temporary directory in `/tmp` and `cd` to it. Adequate for small files (<100MB) and tasks. This directory will be automatically deleted if created after reboot, as it lives in RAM.
- `prep_tmp_noram`: prepares a temporary directory in `$HOME/.cache/linuxtoys/tmp`. Adequate for larger temporary file operations. This directory will be automatically deleted if created when the script finishes running (either succesfully or failed).
- `prep_rm`: moves the targeted file or directory to a `.bak` file, making a 'reversible removal' and registering such to the transaction map, and parses multiple arguments.
- `copy_`: equivalent to `cp`, and admits its flags. Will attempt to perform its task with elevated privileges if failed in user mode.
- `move_`: equivalent to `mv`, and admits its flags. Will attempt to perform its task with elevated privileges if failed in user mode.

#### Package Management
All the following functions parse the arguments that follow them and have error handling calling `fatal`.

- `pkg_install`: installs native packages from the distribution repositories, engaging each distribution's package manager accordingly. The package names still vary distribution-wise. Can source packages from the AUR in Arch Linux, but packages from that source must be verified manually to ensure their security and legitimacy. Can parse multiple packages at once, and has an optional `--ostreecheck` flag to check if there is a pending deployment of `rpm-ostree` after running in `is_ostree` systems, prompting the user to reboot to apply it before running the script again to resume installation.
- `pkg_flat`: installs flatpaks from Flathub. Also calls `flatpak_in_lib` from `helpers.lib` if the user doesn't yet have the Flatpak capability to install it. Any scripts calling this function will not be displayed for non-systemd operating systems, as system is currently a soft dependency - and in the future will be a hard dependency - of Flatpak. Can parse multiple packages at once, and has an optional `--skip-user` flag to force system-level installation when needed.
- `pkg_appimage`: installs AppImages, properly integrating them with the OS through a special interaction with *Gear Lever* - which is also installed if not available when this function is called.
- `pkg_npm`: installs packages from Node Package Manager, globally. Should only be used after manual checks to the package's GitHub repository to ensure their security and legitimacy.
- `pkg_fromfile`: installs native packages or flatpaks from files. Has an optional `--ostreecheck` flag to check if there is a pending deployment of `rpm-ostree` after running in `is_ostree` systems, prompting the user to reboot to apply it before running the script again to resume installation.
- `pkg_exists`: checks if a packages are already installed, following the same logic as `pkg_install`. Sets the arrays `pkg_found` with packages that are already installed and `pkg_notfound` with packages not already installed.
- `pkg_remove`: removes packages following the same logic as `pkg_install`. Ideal to solve potential dependency conflicts. Will also remove any orphaned dependencies from those.

#### SystemD Service Operations
All the following functions parse the arguments that follow them and have error handling calling `fatal`.

- `sysd_enable`: enables a system-level service for next boot.
- `sysd_start`: starts a system-level service.
- `sysd_disable`: disables a system-level service for next boot.
- `sysd_stop`: stops a system-level service.

- `sysd_enable_usr`: enables a user-level service for next boot.
- `sysd_start_usr`: starts a user-level service.
- `sysd_disable_usr`: disables a user-level service for next boot.
- `sysd_stop_usr`: stops a user-level service.

#### Boot-related Operations
All the following functions have error handling calling `fatal`.

- `bootloader_upd`: updates GRUB settings.
- `initramfs_upd`: updates initramfs settings - useful for driver module installations.
- `kargs_upd`: adds arguments to the kernel CMDLINE in `is_ostree` systems through `rpm-ostree kargs`. Parses multiple arguments.
- `grubbyargs_upd`: adds arguments to the kernel CMDLINE in `is_fedora` and `is_rhel` systems through `grubby`. Parses multiple arguments.

#### Miscellaneous
- `shell_change`: changes the user's default shell. Should only be called for shell installations, as it is presume the user wishes to utilize their new shell of choice.
- `distrobox_created`: registers a distrobox name and its creation event to the transaction map.
- `rclone_mount`: creates a `rclone` mountpoint from a remote to a target through its daemon, registering this to the transaction map.

### `helpers.lib`
Used to call instalations of repositories and auxiliary features that are not called by default and may have other features depending on those.

- `multilib_chk`: checks if `is_arch` systems have the multilib repository enabled, and enables it if not already enabled.
- `rpmfusion_chk`: checks if `is_fedora` or `is_ostree` systems have *RPMFusion* - both free and non-free repositories - installed, and installs them if not present. Additionally, performs the same task for *EPEL* and *CRB* on `is_rhel` systems.
- `pip_lib`: checks if `pip`, package manager for PyPI, and `pipx` are installed, and installs those if not present.
