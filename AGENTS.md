# AGENTS.md — LinuxToys

## Project Overview

LinuxToys is a Python/Tkinter GUI app that installs Linux tools via bash scripts. Original repo: `psygreg/linuxtoys`. Our fork: `pdl-clay/linuxtoys`.

## Run from Source

```bash
p3/linuxtoys.py          # GUI mode (requires display server)
EASY_CLI=1 p3/linuxtoys.py  # CLI mode
```

System deps (Fedora): `python3 python3-gobject python3-requests gtk3 vte291 zenity`

## Architecture

```
p3/
├── linuxtoys.py          # Entry point — sets SCRIPT_DIR env, checks display, launches GUI
├── app/                  # Python GUI (GTK/Tkinter)
│   ├── main.py           # App launch
│   ├── window.py         # Main window
│   ├── term_view.py      # Terminal emulator widget
│   └── updater/          # Auto-update logic
├── libs/                 # Bash libraries sourced by scripts
│   ├── helpers.lib       # Core helper functions
│   ├── optimizers.lib    # System optimization libs
│   └── lang/             # Translation JSON files
├── scripts/              # Bash install scripts organized by category
│   ├── devs/             # Development tools (docker, IDEs, SDKs)
│   ├── drivers/          # GPU drivers (Nvidia, etc.)
│   ├── office/           # Office/creative apps
│   ├── repos/            # Package repos (RPMFusion, AUR helpers, etc.)
│   ├── sysadm/           # System admin tools
│   ├── extra/            # Misc tools and fixes
│   ├── game/             # Gaming tools
│   ├── edu/              # Education
│   └── chat/             # Chat/communication
├── helpers/              # Helper scripts (update_self.sh)
└── requirements.txt      # Python deps
dev/
├── libs/
│   ├── utils.lib         # _msg() logging function — source this in all scripts
│   └── install_all_packages.lib  # Dep installer (TEST MODE — unstable)
├── build/                # Package build scripts
│   ├── build_all.sh      # Builds all formats (needs 3 distrobox containers)
│   ├── copr/build.sh     # RPM/COPR
│   ├── deb/build.sh      # DEB
│   ├── pkg/build.sh      # Arch PKGBUILD
│   ├── nuitka/build.sh   # Standalone binary
│   └── solus/build.sh    # Solus .eopkg
```

## Critical Conventions

### Bash Scripts

- **Always use `ROOT_DIR`** — never `cd ./` or `../`. The build system and utils.lib depend on it.
- **Log with `_msg`** — `source "$ROOT_DIR/dev/libs/utils.lib"` then `_msg info "message"` / `_msg error "message"`.
- **Script headers** are structured metadata parsed by the app:
  ```bash
  #!/bin/bash
  # name: scriptname
  # version: 1.0
  # description: description_key
  # icon: icon.svg
  # compat: ubuntu, fedora, arch, ...
  # reboot: yes/no
  # noconfirm: yes/no
  # nocontainer          # optional: skip container testing
  # systemd: yes/no
  ```
- Script source libs from `p3/libs/` via `$SCRIPT_DIR` env var (set by `linuxtoys.py`).

### Python Code

- Entry point: `p3/linuxtoys.py`
- GUI code lives in `p3/app/`
- Uses GTK3 via PyGObject

## Fork Maintenance

When syncing with upstream (`psygreg/linuxtoys`):

```bash
git fetch upstream
git checkout master
git merge upstream/master
git push origin master
```

**Always remove upstream-only workflows** from fork:
- `.github/workflows/sync-scripts.yml` — uses `SCR_TOKEN`
- `.github/workflows/update-tools.yml` — uses `PAT_TOKEN`

If merge conflicts occur, prefer upstream version unless user specifies otherwise.

## Testing

**NEVER test scripts on the host system.** Use containers.

```bash
# Single script
docker run --rm -it -v "$(pwd)":/workspace fedora:44 bash -c \
  "cd /workspace && bash p3/scripts/SCRIPTNAME.sh"

# Full install
docker run --rm -it -v "$(pwd)":/workspace fedora:44 bash -c \
  "cd /workspace && chmod +x install.sh && ./install.sh"

# Syntax check
bash -n p3/scripts/SCRIPTNAME.sh
```

Multi-distro: `fedora:44`, `ubuntu:24.04`, `archlinux:latest`

### Consistency Testing Methodology

Quando o usuário pedir "teste tudo" ou "teste em várias distros", seguir esta metodologia obrigatoriamente:

1. **Criar script de teste unificado** (`/tmp/test_multidistro.sh` ou similar) que rode em qualquer distro sem modificação
2. **Testar SEM `DEV_MODE=1` primeiro** (regressão) para garantir que alterações não quebram o funcionamento normal:
   - `SCRIPTS_DIR` deve apontar para `~/.cache/linuxtoys/scripts` (cache git)
   - `is_using_git_scripts()` deve retornar `True`
   - Scripts novos da fork **não devem aparecer** (pois não estão no repo oficial)
3. **Testar COM `DEV_MODE=1` depois** (nova funcionalidade):
   - `SCRIPTS_DIR` deve apontar para `p3/scripts/` (bundled local)
   - `is_using_git_scripts()` deve retornar `False`
   - Scripts novos da fork **devem aparecer**
4. **Testar em 3 containers em paralelo:** `fedora:44`, `ubuntu:24.04`, `archlinux:latest`
5. **Verificações obrigatórias em cada distro:**
   - Sintaxe bash (`bash -n`)
   - Ícone existe e é carregado (`get_icon_path()`)
   - Traduções carregam corretamente (sem chaves cruas na UI)
   - `is_containerized()` + `script_is_container_compatible()` funcionam
   - Categorias e subcategorias são descobertas corretamente
6. **Committar correções antes de prosseguir** — não deixar testes falhando
7. **Documentar resultados na memória** (`notes/`) antes de abrir PR

```bash
# Template de execução por container
docker run --rm -v "$(pwd)":/workspace:ro <distro> bash -c \
  "apt-get/pacman/dnf install -y python3 git && bash /workspace/test_multidistro.sh"
```

## Build

Build requires **3 Distrobox containers** (Arch, Debian, Fedora):

```bash
cd dev/build
./build_all.sh              # All formats
./copr/build.sh <ver> <out> # RPM only
```

## Development Priorities (from CONTRIBUTING.md)

1. Safety & Privacy first
2. User friendliness & accessibility
3. Reliability & self-sufficiency
4. CLI restricted to dev/sysadmin menus

## Reference Docs

- `dev/README.md` — Developer setup and build instructions
- `dev/libs/README.md` — Library conventions
- `dev/build/README.md` — Build system details
- `CONTRIBUTING.md` — Contribution guidelines
- [Knowledge Base](https://github.com/psygreg/linuxtoys/wiki/Knowledge-Base)
