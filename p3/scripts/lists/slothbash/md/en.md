Sloth-Bash introduces a series of upgrades on top of standard `bash`. Some of those may be familiar if you previously used `zsh`.

- **Intuitive response:** just the file name will run it if executable; load a venv if there's any and wrap it in `python3` if it's a *.py* file; or trigger `xdg-open` for other cases.
- **Flatpak redirection:** simplifies running flatpak applications from terminal by making `flatpak run` obsolete through smart command handling. No more `io.github.kolunmi.Bazaar`, just `bazaar` will do the trick!
- **Easily open apps from terminal automatically detaching them** with `detach appname`. Perfect for usage with something like Quake Terminal for Gnome or `yakuake` Also works with *flatpak redirection*, local executables, and *distrobox passthrough*. 
- **`cp` and `mv` redirection to `rsync`:** make your file operations more efficient with `rsync`'s delta copies, while also getting it to smartly display progress on larger tasks.
- **Simple file management in your shell:** automatic `ls` after `cd` so you never get lost in your files, and enabled *autocd* shell option so you can navigate your subdirectories more intuitively.
- **Most used zsh shortcuts**: `md`, `rd`, `mkcd`, `take`, `~` and `..` work exactly like zsh, while you can use `cd ...`, `cd ....` and `cd .....` for the other upwards navigation commands. 
- **`all`**: selects all files and subdirectories at its location as targets for `rd`, `rm`, `cp` and `mv`.
- **Better autocompletion** with *Tab* key cycling through all options instead of just displaying them.
- **FZF shell bindings:** if *fzf* is installed, `sloth-bash` enables the standard Bash integration, including fuzzy history search on `Ctrl+R`.
- **Basic command colors:** enables colored output for `ls`, `dir`, `vdir` and `grep`, plus familiar aliases like `ll`, `la` and `l`.
- **Case-insensitive command parsing:**, `ls`, `Ls`, `lS` or `LS`, your command will always work.
- **Distrobox passthrough:** enter your distrobox shell with `distroboxname` and pass commands to your distroboxes running `distroboxname command` (and any additional arguments if needed after). As distroboxes follow the user's *`~/.bashrc`* file, sloth-bash also works from within them!