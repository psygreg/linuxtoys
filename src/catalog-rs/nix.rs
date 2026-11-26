//! Nix package catalog.
//!
//! The package snapshot comes from `nix search nixpkgs '^' --json`, which
//! already carries pname/version/description for every top-level attribute.
//! This module normalizes that snapshot once into a compact MessagePack cache,
//! filters packages that are not meaningful standalone offers, and exposes both
//! the standalone Nix category and the components merged into the shared
//! AppStream catalog.

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs;
use std::io::Write;

const NIX_CACHE_SCHEMA: u32 = 1;

fn json_to_py(py: Python<'_>, value: &Value) -> PyResult<Py<PyAny>> {
    crate::shared::json_to_py(py, value)
}

#[derive(Clone, Serialize, Deserialize)]
struct NixPackage {
    attr: String,
    pname: String,
    version: String,
    description: String,
}

/// Exact package names that are part of the Nix toolchain itself. Nix owns and
/// upgrades these; LinuxToys must never offer them as applications.
fn is_nix_internal(name: &str) -> bool {
    let lower = name.to_lowercase();
    matches!(
        lower.as_str(),
        "nix" | "nixpkgs" | "nixpkgs-review" | "home-manager" | "nix-darwin" | "cachix"
            | "nix-bundle" | "nix-direnv" | "nix-index" | "nix-tree" | "nix-diff"
            | "nix-zsh-completions" | "nix-bash-completions" | "nixos-generators"
    ) || lower.starts_with("nix-")
        || lower.starts_with("nixos-")
        || lower.starts_with("home-manager-")
        || lower.starts_with("nix_")
}

/// Drivers, kernels, firmware and out-of-tree kernel modules need a matching
/// host kernel/driver stack. Nix cannot install those usefully on a non-NixOS
/// distribution that already owns the hardware stack.
fn is_hardware_support(name: &str, description: &str) -> bool {
    let lower = name.to_lowercase();
    let desc = description.to_lowercase();
    if lower == "linux"
        || lower.starts_with("linux_")
        || lower.starts_with("linuxpackages")
        || lower.starts_with("linuxheaders")
        || lower.starts_with("linux-firmware")
        || lower.starts_with("linux_latest")
        || lower.starts_with("linux_zen")
        || lower.starts_with("linux_hardened")
        || lower.starts_with("linux_rt")
    {
        return true;
    }
    lower.starts_with("nvidia")
        || lower.starts_with("libnvidia")
        || lower.starts_with("xf86-video-")
        || lower.starts_with("xf86-input-")
        || lower.starts_with("broadcom-sta")
        || lower.starts_with("rtl8")
        || lower.starts_with("rtw8")
        || lower.starts_with("rtl88")
        || lower.starts_with("rtw88")
        || lower == "mesa"
        || lower.starts_with("mesa_")
        || lower.starts_with("mesa-")
        || lower.contains("-driver")
        || lower.ends_with("-drivers")
        || lower.contains("-firmware")
        || lower.starts_with("firmware")
        || lower.ends_with("-module")
        || lower.ends_with("-modules")
        || lower.contains("kernel-module")
        || desc.contains("kernel module")
        || desc.contains("out-of-tree kernel")
        || (desc.contains("driver ") && desc.contains("kernel"))
}

/// Desktop environments, window managers and their session infrastructure are
/// system setup, not portable applications. Installing them through a package
/// list on top of another desktop would leave an unusable configuration.
fn is_desktop_setup(name: &str) -> bool {
    let lower = name.to_lowercase();
    const EXACT: &[&str] = &[
        "gnome-shell",
        "gnome-session",
        "gnome-desktop",
        "gnome-settings-daemon",
        "gnome-control-center",
        "gdm",
        "sddm",
        "lightdm",
        "greetd",
        "ly",
        "plasma-desktop",
        "plasma-workspace",
        "plasma5",
        "kwin",
        "mutter",
        "xfce4-session",
        "xfce4-panel",
        "xfwm4",
        "mate-session-manager",
        "mate-panel",
        "marco",
        "cinnamon",
        "cinnamon-session",
        "cinnamon-desktop",
        "cinnamon-settings-daemon",
        "budgie-desktop",
        "lxqt-session",
        "lxde-common",
        "enlightenment",
        "sway",
        "sway-unwrapped",
        "hyprland",
        "wayfire",
        "wayfire-with-plugins",
        "labwc",
        "dwm",
        "awesome",
        "bspwm",
        "i3",
        "i3-gaps",
        "openbox",
        "fluxbox",
        "icewm",
        "jwm",
        "pekwm",
        "herbstluftwm",
        "xmonad",
        "niri",
        "cosmic-comp",
        "cosmic-session",
        "weston",
        "westonlite",
        "cage",
        "gamescope",
    ];
    if EXACT.contains(&lower.as_str()) {
        return true;
    }
    lower.starts_with("plasma-")
        || lower.starts_with("plasmavantage")
        || lower.starts_with("cinnamon-")
        || lower.starts_with("kde-")
        || lower.starts_with("xfce4-")
        || lower.starts_with("mate-")
        || lower.starts_with("i3-")
        || lower.starts_with("dwm-")
        || lower.starts_with("sway-")
        || lower.starts_with("hypr-")
        || lower.starts_with("gnome-shell-")
        || lower.starts_with("budgie-")
}

fn is_offerable(package: &NixPackage) -> bool {
    if package.attr.is_empty() || package.attr.contains('.') {
        return false;
    }
    // Attribute names are rendered as `pkgs.<name>` in the generated module.
    // Keep the exact Nix identifier shape; nixpkgs' top-level attributes all
    // follow it, and anything else could not be selected safely.
    let mut chars = package.attr.chars();
    let Some(first) = chars.next() else { return false };
    if !(first.is_ascii_alphabetic() || first == '_') {
        return false;
    }
    if !chars.all(|character| {
        character.is_ascii_alphanumeric() || matches!(character, '_' | '\'' | '-')
    }) {
        return false;
    }
    !is_nix_internal(&package.attr)
        && !is_hardware_support(&package.attr, &package.description)
        && !is_desktop_setup(&package.attr)
}

fn normalize_nix_package(key: &str, value: &Value) -> Option<NixPackage> {
    // Only top-level package attributes are offered. Nested namespaces such as
    // python3Packages.requests or haskellPackages.* are implementation sets,
    // not applications.
    let mut parts = key.splitn(3, '.');
    let _prefix = parts.next()?;
    let _system = parts.next()?;
    let attr = parts.next()?;
    if attr.is_empty() || attr.contains('.') {
        return None;
    }
    let item = value.as_object()?;
    let pname = item
        .get("pname")
        .and_then(Value::as_str)
        .unwrap_or(attr)
        .trim();
    let version = item
        .get("version")
        .and_then(Value::as_str)
        .unwrap_or("")
        .trim();
    let description = item
        .get("description")
        .and_then(Value::as_str)
        .unwrap_or("")
        .trim();
    let package = NixPackage {
        attr: attr.to_string(),
        pname: pname.to_string(),
        version: version.to_string(),
        description: description.to_string(),
    };
    is_offerable(&package).then_some(package)
}

fn binary_path(path: &str) -> std::path::PathBuf {
    std::path::Path::new(path).with_extension("bin")
}

#[derive(Serialize, Deserialize)]
struct CachedNixCatalog {
    schema: u32,
    key: String,
    packages: Vec<NixPackage>,
}

fn snapshot_key(source: &std::path::Path) -> Result<String, String> {
    let metadata = fs::metadata(source).map_err(|error| error.to_string())?;
    let modified = metadata
        .modified()
        .map_err(|error| error.to_string())?
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|error| error.to_string())?
        .as_nanos();
    Ok(format!("{}:{modified}", metadata.len()))
}

fn load_nix_packages(path: &str) -> Result<Vec<NixPackage>, String> {
    let source = std::path::Path::new(path);
    let key = snapshot_key(source)?;
    let binary = binary_path(path);
    if let Ok(bytes) = fs::read(&binary) {
        if let Ok(cache) = rmp_serde::from_slice::<CachedNixCatalog>(&bytes) {
            if cache.schema == NIX_CACHE_SCHEMA && cache.key == key && !cache.packages.is_empty() {
                return Ok(cache.packages);
            }
        }
    }

    let text = fs::read_to_string(source).map_err(|error| error.to_string())?;
    let values: Value = serde_json::from_str(&text).map_err(|error| error.to_string())?;
    let rows = values.as_object().ok_or("Nix catalog must be an object")?;
    let mut packages: Vec<NixPackage> = rows
        .iter()
        .filter_map(|(key, value)| normalize_nix_package(key, value))
        .collect();
    if packages.is_empty() {
        return Err("No usable Nix packages".into());
    }
    // There is no reliable per-package download counter in nixpkgs; keep the
    // category stable and predictable instead of inventing a ranking.
    packages.sort_by(|a, b| a.attr.to_lowercase().cmp(&b.attr.to_lowercase()));
    packages.dedup_by(|a, b| a.attr == b.attr);

    let cache = CachedNixCatalog {
        schema: NIX_CACHE_SCHEMA,
        key,
        packages,
    };
    let bytes = rmp_serde::to_vec_named(&cache).map_err(|error| error.to_string())?;
    static TEMP_SEQUENCE: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let sequence = TEMP_SEQUENCE.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    let temporary = binary.with_extension(format!("bin.{}.{}.tmp", std::process::id(), sequence));
    let result = (|| -> std::io::Result<()> {
        let mut file = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)?;
        file.write_all(&bytes)?;
        file.sync_all()?;
        drop(file);
        let written = fs::read(&temporary)?;
        let verified: CachedNixCatalog = rmp_serde::from_slice(&written)
            .map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error.to_string()))?;
        if written != bytes
            || verified.schema != NIX_CACHE_SCHEMA
            || verified.key != cache.key
            || verified.packages.is_empty()
        {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "Nix binary cache failed verification",
            ));
        }
        fs::rename(&temporary, &binary)
    })();
    if let Err(error) = result {
        let _ = fs::remove_file(&temporary);
        return Err(format!("Could not publish Nix binary cache: {error}"));
    }
    Ok(cache.packages)
}

fn nix_scope_key(scope: &str) -> String {
    format!("nix:{scope}")
}

fn score_package(package: &NixPackage, query: &str) -> i64 {
    let attr = package.attr.to_lowercase();
    let pname = package.pname.to_lowercase();
    let description = package.description.to_lowercase();
    let mut score = 0i64;
    if attr == query {
        score += 100;
    } else if attr.starts_with(query) {
        score += 80;
    } else if attr.contains(query) {
        score += 60;
    }
    if pname == query {
        score += 95;
    } else if pname.starts_with(query) {
        score += 75;
    } else if pname.contains(query) {
        score += 55;
    }
    if description.contains(query) {
        score += 30;
    }
    if score > 0 && attr.chars().count() < 20 {
        score += 5;
    }
    score
}

fn nix_homepage(package: &NixPackage) -> String {
    format!(
        "https://search.nixos.org/packages?channel=unstable&show={}&from=0&size=50&sort=relevance&type=packages&query={}",
        package.attr, package.attr
    )
}

fn nix_entry_value(package: &NixPackage, scopes: &[String], active_scope: &str) -> Value {
    let attr = &package.attr;
    let id = format!("nix:{attr}");
    let description = &package.description;
    let blocks = if description.is_empty() {
        Value::Array(Vec::new())
    } else {
        serde_json::json!([{"type":"paragraph","spans":[{"text":description}]}])
    };
    let mut entry = serde_json::json!({
        "id": id,
        "appstream_id": id,
        "repo_app_id": id,
        "registry_name": id,
        "name": attr,
        "appstream_canonical_name": attr,
        "description": description,
        "description_tag": "",
        "description_localized": false,
        "long_description": description,
        "long_description_blocks": blocks,
        "long_description_locale": "",
        "long_description_tag": "",
        "long_description_format": "appstream",
        "screenshots": [],
        "homepage_url": nix_homepage(package),
        "donate": "",
        "donate_url": "",
        "license": "",
        "developer": "Nixpkgs",
        "icon": "nix.svg",
        "category": "nix",
        "type": "nix",
        "package-name": attr,
        "repo": "nixpkgs",
        "revert": "yes",
        "reboot": "no",
        "is_script": true,
        "is_repo_entry": true,
        "is_appstream_entry": true,
        "is_subcategory": false,
        "appstream_launchable": "",
        "appstream_source": "nix",
        "appstream_origin": "nixpkgs",
        "flatpak_remote": "",
        "flatpak_scope": "",
        "flatpak_installation": "",
        "flatpak_ref": "",
        "flatpak_arch": "",
        "flatpak_branch": "",
        "snap_name": "",
        "snap_id": "",
        "snap_channel": "",
        "snap_confinement": "",
        "overrides": {},
        "appstream_version": package.version,
        "review_rating": Value::Null,
        "review_count": Value::Null,
        "is_new": false,
        "is_verified": false,
        "native_distro_badge": "",
        "appstream_badge": "nix.svg",
        "has_app_page": true,
        "path": format!("appstream://nix/{attr}"),
        "nix_name": attr,
        "nix_pname": package.pname,
        "nix_version": package.version,
        "nix_scope": active_scope,
        "nix_scopes": scopes,
    });
    if let Some(object) = entry.as_object_mut() {
        if !scopes.is_empty() {
            let mut first = active_scope.to_string();
            if !scopes.iter().any(|scope| scope == &first) {
                first = scopes[0].clone();
            }
            object.insert("nix_scope".into(), Value::String(first.clone()));
            if scopes.len() > 1 {
                let mut options = Vec::with_capacity(scopes.len());
                for scope in scopes {
                    let mut option = object.clone();
                    option.remove("source_options");
                    option.remove("recommended_source");
                    option.insert("nix_scope".into(), Value::String(scope.clone()));
                    options.push(Value::Object(option));
                }
                object.insert("source_options".into(), Value::Array(options));
                object.insert(
                    "recommended_source".into(),
                    Value::String(nix_scope_key(&first)),
                );
            }
        } else {
            object.insert("nix_scope".into(), Value::String(String::new()));
        }
    }
    entry
}

/// Raw components for the shared AppStream catalog pipeline. One component per
/// available scope lets source grouping expose both `Nix (home-manager)` and
/// `Nix (system)` for packages that also exist in another catalog.
pub(crate) fn nix_components(
    path: &str,
    scopes: &[String],
    api_identities: &std::collections::HashMap<String, (String, bool)>,
) -> Vec<serde_json::Map<String, Value>> {
    if path.is_empty() || scopes.is_empty() {
        return Vec::new();
    }
    let Ok(packages) = load_nix_packages(path) else {
        return Vec::new();
    };
    let mut out = Vec::with_capacity(packages.len() * scopes.len());
    for package in &packages {
        // The Nix Software API identifies which attributes are real GUI
        // applications and supplies their display names. Attributes outside
        // that set keep their raw name and never participate in the by-name
        // merge in the shared catalog: several command-line/library packages
        // share names with unrelated applications (e.g. ``ark`` is the R
        // kernel, not KDE Ark). Ambiguous display names shared by several
        // packages are excluded from merging as well.
        let (api_name, mergeable) = api_identities
            .get(&package.attr)
            .map(|(name, merge)| (name.as_str(), *merge))
            .unwrap_or(("", false));
        let display_name = if api_name.is_empty() { &package.attr } else { api_name };
        for scope in scopes {
            let description_blocks = if package.description.is_empty() {
                Value::Array(Vec::new())
            } else {
                serde_json::json!([{"type":"paragraph","spans":[{"text":package.description}]}])
            };
            let component = serde_json::json!({
                "identity": format!("nix:{}-{scope}", package.attr),
                "id": format!("nix:{}", package.attr),
                "source": "nix",
                "origin": "nixpkgs",
                "name": display_name,
                "summary": package.description,
                "description_blocks": description_blocks,
                "packages": [package.attr],
                "categories": [],
                "icon": "nix.svg",
                "screenshots": [],
                "homepage": nix_homepage(package),
                "license": "",
                "version": package.version,
                "launchable": "",
                "developer": "Nixpkgs",
                "verified": false,
                "nix_name": package.attr,
                "nix_pname": package.pname,
                "nix_api_name": if mergeable { api_name } else { "" },
                "nix_version": package.version,
                "nix_scope": scope,
            });
            if let Value::Object(map) = component {
                out.push(map);
            }
        }
    }
    out
}

#[pyclass]
pub(crate) struct NixCatalog {
    packages: Vec<NixPackage>,
    scopes: Vec<String>,
}

impl NixCatalog {
    fn entry(&self, package: &NixPackage) -> Value {
        let active = self.scopes.first().map(String::as_str).unwrap_or("");
        nix_entry_value(package, &self.scopes, active)
    }
}

#[pymethods]
impl NixCatalog {
    #[new]
    fn new(py: Python<'_>, path: &str, scopes: Vec<String>) -> PyResult<Self> {
        let path = path.to_string();
        let packages = py
            .allow_threads(move || load_nix_packages(&path))
            .map_err(pyo3::exceptions::PyValueError::new_err)?;
        Ok(Self { packages, scopes })
    }

    fn __len__(&self) -> usize {
        self.packages.len()
    }

    fn entry_slice(&self, py: Python<'_>, offset: usize, limit: usize) -> PyResult<Vec<Py<PyAny>>> {
        let start = offset.min(self.packages.len());
        let end = start.saturating_add(limit).min(self.packages.len());
        let mut out = Vec::with_capacity(end.saturating_sub(start));
        for package in &self.packages[start..end] {
            out.push(json_to_py(py, &self.entry(package))?);
        }
        Ok(out)
    }

    fn all_entries(&self, py: Python<'_>) -> PyResult<Vec<Py<PyAny>>> {
        let mut out = Vec::with_capacity(self.packages.len());
        for package in &self.packages {
            out.push(json_to_py(py, &self.entry(package))?);
        }
        Ok(out)
    }

    fn find_by_name(&self, py: Python<'_>, name: &str) -> PyResult<Option<Py<PyAny>>> {
        let target = name.trim().to_lowercase();
        if target.is_empty() {
            return Ok(None);
        }
        self.packages
            .iter()
            .find(|package| package.attr.to_lowercase() == target || package.pname.to_lowercase() == target)
            .map(|package| json_to_py(py, &self.entry(package)))
            .transpose()
    }

    fn find_by_attr(&self, py: Python<'_>, attr: &str) -> PyResult<Option<Py<PyAny>>> {
        let target = attr.trim().to_lowercase();
        if target.is_empty() {
            return Ok(None);
        }
        self.packages
            .iter()
            .find(|package| package.attr.to_lowercase() == target)
            .map(|package| json_to_py(py, &self.entry(package)))
            .transpose()
    }

    fn search(&self, py: Python<'_>, query: &str) -> PyResult<Vec<(Py<PyAny>, i64)>> {
        let query = query.trim().to_lowercase();
        if query.is_empty() {
            return Ok(Vec::new());
        }
        let mut matches = Vec::new();
        for package in &self.packages {
            let score = score_package(package, &query);
            if score > 0 {
                matches.push((package, score));
            }
        }
        matches.sort_by(|(left, left_score), (right, right_score)| {
            right_score
                .cmp(left_score)
                .then_with(|| left.attr.to_lowercase().cmp(&right.attr.to_lowercase()))
        });
        let mut out = Vec::with_capacity(matches.len());
        for (package, score) in matches {
            out.push((json_to_py(py, &self.entry(package))?, score));
        }
        Ok(out)
    }

    #[staticmethod]
    fn snapshot_valid(py: Python<'_>, path: &str, max_bytes: u64) -> bool {
        let path = path.to_string();
        py.allow_threads(move || validate_nix_snapshot(&path, max_bytes))
    }
}

fn validate_nix_snapshot(path: &str, max_bytes: u64) -> bool {
    let Ok(metadata) = fs::metadata(path) else {
        return false;
    };
    if metadata.len() == 0 || metadata.len() > max_bytes {
        return false;
    }
    let Ok(file) = fs::File::open(path) else {
        return false;
    };
    let Ok(value) = serde_json::from_reader::<_, Value>(std::io::BufReader::new(file)) else {
        return false;
    };
    let Some(rows) = value.as_object() else {
        return false;
    };
    !rows.is_empty()
        && rows.keys().any(|key| key.matches('.').count() >= 2)
        && rows
            .values()
            .all(|value| value.as_object().is_some_and(|item| item.contains_key("pname") || item.contains_key("description")))
}

#[pyfunction]
pub(crate) fn nix_snapshot_valid(py: Python<'_>, path: &str, max_bytes: u64) -> bool {
    NixCatalog::snapshot_valid(py, path, max_bytes)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn package(attr: &str, description: &str) -> NixPackage {
        NixPackage {
            attr: attr.into(),
            pname: attr.into(),
            version: "1.0".into(),
            description: description.into(),
        }
    }

    #[test]
    fn filters_nix_owned_packages() {
        for name in ["nix", "nix-bisect", "nixos-generators", "home-manager"] {
            assert!(!is_offerable(&package(name, "Nix tool")), "{name}");
        }
    }

    #[test]
    fn filters_hardware_and_desktop_setup() {
        for name in [
            "nvidia-x11", "linux", "linux_6_12", "broadcom-sta", "xf86-video-intel",
            "gnome-shell", "plasma-desktop", "sway", "hyprland", "dwm", "mesa",
        ] {
            assert!(!is_offerable(&package(name, "system component")), "{name}");
        }
        for name in ["firefox", "gimp", "ripgrep", "linuxqq", "mkvtoolnix-cli"] {
            assert!(is_offerable(&package(name, "application")), "{name}");
        }
    }

    #[test]
    fn normalizes_top_level_packages_only() {
        let value = serde_json::json!({
            "legacyPackages.x86_64-linux.firefox": {
                "pname": "firefox", "version": "1.0", "description": "Web browser"
            },
            "legacyPackages.x86_64-linux.python3Packages.requests": {
                "pname": "requests", "version": "1.0", "description": "HTTP library"
            },
            "legacyPackages.x86_64-linux.nix": {
                "pname": "nix", "version": "2.0", "description": "Package manager"
            }
        });
        let rows = value.as_object().unwrap();
        let packages: Vec<_> = rows
            .iter()
            .filter_map(|(key, value)| normalize_nix_package(key, value))
            .collect();
        assert_eq!(packages.len(), 1);
        assert_eq!(packages[0].attr, "firefox");
    }

    #[test]
    fn entries_expose_both_scopes_when_available() {
        let scopes = vec!["home-manager".to_string(), "system".to_string()];
        let entry = nix_entry_value(&package("firefox", "Web browser"), &scopes, "home-manager");
        assert_eq!(entry.get("appstream_source").and_then(Value::as_str), Some("nix"));
        assert_eq!(entry.get("category").and_then(Value::as_str), Some("nix"));
        let options = entry.get("source_options").and_then(Value::as_array).unwrap();
        assert_eq!(options.len(), 2);
        let scopes: Vec<_> = options
            .iter()
            .filter_map(|option| option.get("nix_scope").and_then(Value::as_str))
            .collect();
        assert_eq!(scopes, vec!["home-manager", "system"]);
        assert_eq!(entry.get("recommended_source").and_then(Value::as_str), Some("nix:home-manager"));
    }

    #[test]
    fn loads_and_caches_snapshot() {
        let directory = std::env::temp_dir().join(format!("lt-nix-test-{}", std::process::id()));
        let _ = fs::create_dir_all(&directory);
        let source = directory.join("packages.json");
        fs::write(&source, serde_json::json!({
            "legacyPackages.x86_64-linux.hello": {"pname":"hello","version":"2.12","description":"A program that prints a greeting"},
            "legacyPackages.x86_64-linux.nix": {"pname":"nix","version":"2.20","description":"Package manager"},
        }).to_string()).unwrap();
        let packages = load_nix_packages(source.to_str().unwrap()).unwrap();
        assert_eq!(packages.len(), 1);
        assert_eq!(packages[0].attr, "hello");
        assert!(source.with_extension("bin").is_file());
        let cached = load_nix_packages(source.to_str().unwrap()).unwrap();
        assert_eq!(cached.len(), 1);
        let _ = fs::remove_dir_all(&directory);
    }
}
