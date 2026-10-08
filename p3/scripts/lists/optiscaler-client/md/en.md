**OptiScaler Client** is a modern, high-performance desktop utility designed to simplify the installation, management, and update of the OptiScaler mod across your entire game library. Built with C# and Avalonia UI.

**Game Discovery**

- **Multi-Platform Auto-Scanner** — Scans *Steam* and *Heroic* (*Epic Games, GOG*) automatically.
- Custom Folder Scanning — Add any folder as a scan source for DRM-free or standalone games.
- Manual Game Addition — Add games by selecting the executable directly.
- Drive Root Filtering — Limit scanning to specific drives.
- Smart Exclusions — Pre-configured exclusions for non-game entries (e.g., *Wallpaper Engine*, *Steamworks Redistributables*).
- Cover Art Fetching — Automatically fetches game cover art from *Steam API* and *SteamGridDB* with local caching.

**Installation & Uninstallation**

- Quick Install / Uninstall — One-click toggle per game directly from the main view. Automatically downloads components if not cached.
- Auto Install — Detects game directory structure automatically, including *UE5/Phoenix* game layouts.
- Manual Install — Select the target executable manually for non-standard game structures.
- Bulk Install — Install OptiScaler across multiple games at once with platform filtering, component selection, and profile application.
- Injection Method Selection — Choose the DLL injection method: `dxgi.dll`, `winmm.dll`, `d3d12.dll`, `dbghelp.dll`, `version.dll`, `wininet.dll`, winhttp.dll`.
- Backup & Restore — Original game files are backed up before installation and restored on uninstall.

**Component Management**

- **OptiScaler** — Core upscaling mod with stable, beta, and nightly version channels.
- *Fakenvapi* — Compatibility layer for AMD/Intel GPUs, installed alongside OptiScaler when needed.
- *Nukem's DLSSG-to-FSR3* — Frame generation bridge that converts DLSS Frame Gen to FSR3.
- *FSR 4 DLL (Swap)* — Switch between INT8 and FP8 FSR 4 builds, or just swap the game's FSR 4 files directly without installing OptiScaler. Supports importing custom FSR 4 DLL versions.
- *OptiPatcher* — ASI plugin loader, automatically configured with LoadAsiPlugins=true in OptiScaler.ini.
- *DLSS Enabler* — Optional Frame Generation / Multi Frame Generation support, downloaded from an unofficial mirror since official builds are Nexus Mods-only.

**Profiles**

- **OptiScaler Profiles** — Create, edit, clone, and manage INI-based configuration profiles.
- Easy Mode Editor — Simple toggle-based interface for common settings.
- Advanced Mode Editor — Full section-based settings editor with search and sidebar navigation.
- Default Profile — Set a default profile that is applied automatically during Quick Install and Bulk Install.
- Built-in Default — "OptiScaler Standard" profile ships out-of-the-box with sensible defaults.
- Recommended Configuration — Per-game recommended settings pulled from the OptiScaler compatibility page and the Luma Unreal Engine list, with automatic injection method selection based on community data.
- **Update Without Reinstalling** — Changing a single simple setting offers a lightweight config update instead of a full reinstall.
