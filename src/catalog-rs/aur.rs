use flate2::read::GzDecoder;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fs::{self, File};
use std::io::{self, BufReader, Write};
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

const AUR_ARCHIVE_URL: &str = "https://aur.archlinux.org/packages-meta-ext-v1.json.gz";
const SHELLY_ICON_MANIFEST_URL: &str = "https://raw.githubusercontent.com/Seafoam-Labs/shelly-icon-stream/main/manifest.json";
const SHELLY_ICON_RAW_BASE: &str = "https://raw.githubusercontent.com/Seafoam-Labs/shelly-icon-stream/main/";
const SHELLY_ICON_MANIFEST_FILE: &str = "shelly-icon-stream.json";
const AUR_CATALOG_FILE: &str = "catalog.bin";
const AUR_CATALOG_VERSION_FILE: &str = "catalog.version";
const AUR_CATALOG_VERSION: u32 = 3;
const MAX_AGE: Duration = Duration::from_secs(14 * 24 * 60 * 60);

#[derive(Debug, Clone, Serialize, Deserialize)]
#[allow(non_snake_case)]
struct AurPackage {
    Name: String,
    #[serde(default)] PackageBase: String,
    #[serde(default)] Version: String,
    #[serde(default)] Description: Option<String>,
    #[serde(default)] URL: Option<String>,
    #[serde(default)] NumVotes: u64,
    #[serde(default)] Popularity: f64,
    #[serde(default)] OutOfDate: Option<i64>,
    #[serde(default)] Maintainer: Option<String>,
    #[serde(default)] FirstSubmitted: i64,
    #[serde(default)] LastModified: i64,
    #[serde(default)] Depends: Vec<String>,
    #[serde(default)] MakeDepends: Vec<String>,
    #[serde(default)] OptDepends: Vec<String>,
    #[serde(default)] CheckDepends: Vec<String>,
    #[serde(default)] Conflicts: Vec<String>,
    #[serde(default)] Provides: Vec<String>,
    #[serde(default)] Replaces: Vec<String>,
    #[serde(default)] Groups: Vec<String>,
    #[serde(default)] License: Vec<String>,
    #[serde(default)] Keywords: Vec<String>,
    #[serde(default)] Icon: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct CachedAurCatalog {
    version: u32,
    entries: Vec<AurPackage>,
    browse_order: Vec<usize>,
}

fn cache_fresh(path: &Path) -> bool {
    let modified = match fs::metadata(path).and_then(|m| m.modified()) {
        Ok(value) => value,
        Err(_) => return false,
    };
    SystemTime::now()
        .duration_since(modified)
        .map(|age| age <= MAX_AGE)
        .unwrap_or(false)
}

fn io_py(err: impl std::fmt::Display) -> PyErr {
    pyo3::exceptions::PyRuntimeError::new_err(err.to_string())
}

fn modified_time(path: &Path) -> Option<SystemTime> {
    fs::metadata(path).and_then(|meta| meta.modified()).ok()
}

#[pyfunction]
pub fn aur_cache_is_fresh(path: &str) -> bool {
    let archive = Path::new(path);
    let manifest = shelly_manifest_path(archive);
    let binary = catalog_path(archive);
    if !cache_fresh(archive)
        || !cache_fresh(&manifest)
        || !binary.is_file()
        || !catalog_version_matches(archive)
    {
        return false;
    }

    // A source download may have succeeded even if rebuilding catalog.bin did
    // not. Treat a binary older than either source as stale so the next refresh
    // retries the build instead of serving that generation for another 14 days.
    let Some(binary_time) = modified_time(&binary) else { return false; };
    let Some(archive_time) = modified_time(archive) else { return false; };
    let Some(manifest_time) = modified_time(&manifest) else { return false; };
    binary_time >= archive_time && binary_time >= manifest_time
}

fn download_to_path(url: &str, destination: &Path, user_agent: &str) -> Result<(), String> {
    let response = ureq::get(url)
        .set("User-Agent", user_agent)
        .call()
        .map_err(|error| error.to_string())?;
    if response.status() != 200 {
        return Err(format!("request returned HTTP {}", response.status()));
    }

    let tmp = destination.with_extension("tmp");
    let mut input = response.into_reader();
    let mut output = File::create(&tmp).map_err(|error| error.to_string())?;
    io::copy(&mut input, &mut output).map_err(|error| error.to_string())?;
    output.flush().map_err(|error| error.to_string())?;
    output.sync_all().map_err(|error| error.to_string())?;
    fs::rename(&tmp, destination).map_err(|error| error.to_string())?;
    Ok(())
}

fn shelly_manifest_path(aur_archive: &Path) -> PathBuf {
    aur_archive
        .parent()
        .unwrap_or_else(|| Path::new("."))
        .join(SHELLY_ICON_MANIFEST_FILE)
}

fn catalog_path(aur_archive: &Path) -> PathBuf {
    aur_archive
        .parent()
        .unwrap_or_else(|| Path::new("."))
        .join(AUR_CATALOG_FILE)
}

fn catalog_version_path(aur_archive: &Path) -> PathBuf {
    aur_archive
        .parent()
        .unwrap_or_else(|| Path::new("."))
        .join(AUR_CATALOG_VERSION_FILE)
}

fn catalog_version_matches(aur_archive: &Path) -> bool {
    fs::read_to_string(catalog_version_path(aur_archive))
        .ok()
        .and_then(|value| value.trim().parse::<u32>().ok())
        == Some(AUR_CATALOG_VERSION)
}

fn publish_catalog_version(aur_archive: &Path) -> Result<(), String> {
    let destination = catalog_version_path(aur_archive);
    let tmp = destination.with_extension("tmp");
    let mut output = File::create(&tmp).map_err(|error| error.to_string())?;
    write!(output, "{}\n", AUR_CATALOG_VERSION).map_err(|error| error.to_string())?;
    output.flush().map_err(|error| error.to_string())?;
    output.sync_all().map_err(|error| error.to_string())?;
    fs::rename(&tmp, destination).map_err(|error| error.to_string())?;
    Ok(())
}

fn resolve_icon(
    pkg: &AurPackage,
    icons: &HashMap<String, Vec<String>>,
) -> String {
    let paths = icons.get(&pkg.Name).or_else(|| {
        if pkg.PackageBase.is_empty() || pkg.PackageBase == pkg.Name {
            None
        } else {
            icons.get(&pkg.PackageBase)
        }
    });

    let Some(paths) = paths else {
        return "aurpackage.webp".to_string();
    };
    let selected = paths
        .iter()
        .find(|path| path.contains("/128x128/"))
        .or_else(|| paths.iter().find(|path| path.contains("/64x64/")))
        .or_else(|| paths.iter().find(|path| path.contains("/48x48/")))
        .or_else(|| paths.first());

    selected
        .map(|path| format!("{SHELLY_ICON_RAW_BASE}{path}"))
        .unwrap_or_else(|| "aurpackage.webp".to_string())
}


fn dependency_name(value: &str) -> &str {
    let value = value.split(':').next().unwrap_or(value).trim();
    let end = value
        .find(|ch: char| matches!(ch, '<' | '>' | '='))
        .unwrap_or(value.len());
    value[..end].trim()
}

fn description_looks_like_library(description: Option<&str>) -> bool {
    let Some(description) = description else { return false; };
    let text = description.to_ascii_lowercase();

    // Deliberately conservative: these phrases describe implementation
    // components rather than merely mentioning that an application uses a library.
    const SIGNALS: &[&str] = &[
        "a library for ",
        "library for ",
        "libraries for ",
        "shared library",
        "client library",
        "runtime library",
        "development library",
        "development files for ",
        "header files for ",
        "headers for ",
        "bindings for ",
        "bindings to ",
        "language bindings",
        "python bindings",
        "rust bindings",
        "go bindings",
        "perl bindings",
        "ruby bindings",
        "lua bindings",
        "a python module",
        "python module for ",
        "perl module for ",
        "ruby module for ",
        "lua module for ",
    ];

    SIGNALS.iter().any(|signal| text.contains(signal))
}

fn provides_shared_library(pkg: &AurPackage) -> bool {
    pkg.Provides.iter().any(|provided| {
        let provided = dependency_name(provided).to_ascii_lowercase();
        provided.ends_with(".so") || provided.contains(".so.")
    })
}

fn dependency_library_names(packages: &[AurPackage]) -> HashSet<String> {
    let mut referenced = HashSet::new();

    for pkg in packages {
        // OptDepends are intentionally excluded: optional dependencies are often
        // standalone applications users may reasonably want to discover.
        for dependency in pkg
            .Depends
            .iter()
            .chain(pkg.MakeDepends.iter())
            .chain(pkg.CheckDepends.iter())
        {
            let name = dependency_name(dependency);
            if !name.is_empty() {
                referenced.insert(name.to_ascii_lowercase());
            }
        }
    }

    referenced
}

fn should_hide_dependency_library(pkg: &AurPackage, referenced: &HashSet<String>) -> bool {
    let name = pkg.Name.to_ascii_lowercase();
    let base = if pkg.PackageBase.is_empty() {
        name.as_str()
    } else {
        pkg.PackageBase.as_str()
    };

    if !referenced.contains(&name) && !referenced.contains(&base.to_ascii_lowercase()) {
        return false;
    }

    provides_shared_library(pkg) || description_looks_like_library(pkg.Description.as_deref())
}

fn out_of_date_too_long(pkg: &AurPackage, now: i64) -> bool {
    const TWO_WEEKS: i64 = 14 * 24 * 60 * 60;
    pkg.OutOfDate
        .map(|marked| marked > 0 && now.saturating_sub(marked) > TWO_WEEKS)
        .unwrap_or(false)
}


#[derive(Clone, Copy, PartialEq, Eq)]
enum AurVariant {
    Standard,
    Bin,
    Git,
}

fn package_variant(pkg: &AurPackage) -> AurVariant {
    let name = pkg.Name.to_ascii_lowercase();
    if name.ends_with("-bin") {
        AurVariant::Bin
    } else if name.ends_with("-git") {
        AurVariant::Git
    } else {
        AurVariant::Standard
    }
}

fn family_key(value: &str) -> Option<String> {
    let normalized = dependency_name(value).trim().to_ascii_lowercase();
    if normalized.is_empty() {
        return None;
    }
    let base = normalized
        .strip_suffix("-bin")
        .or_else(|| normalized.strip_suffix("-git"))
        .unwrap_or(&normalized)
        .trim();
    (!base.is_empty()).then(|| base.to_string())
}

fn package_family_keys(pkg: &AurPackage) -> HashSet<String> {
    std::iter::once(pkg.Name.as_str())
        .chain(pkg.Provides.iter().map(String::as_str))
        .filter_map(family_key)
        .collect()
}

fn preferred_binary_families(packages: &[AurPackage]) -> HashSet<String> {
    // Bit mask: standard=1, bin=2, git=4. A binary variant only participates
    // when it has never been marked out of date; a recently flagged -bin must
    // not suppress source/development alternatives.
    let mut variants: HashMap<String, u8> = HashMap::new();

    for pkg in packages {
        let bit = match package_variant(pkg) {
            AurVariant::Standard => 0b001,
            AurVariant::Bin if pkg.OutOfDate.is_none() => 0b010,
            AurVariant::Bin => 0,
            AurVariant::Git => 0b100,
        };
        if bit == 0 {
            continue;
        }
        for key in package_family_keys(pkg) {
            *variants.entry(key).or_insert(0) |= bit;
        }
    }

    variants
        .into_iter()
        .filter_map(|(key, mask)| (mask == 0b111).then_some(key))
        .collect()
}

fn should_hide_for_binary_variant(
    pkg: &AurPackage,
    preferred_families: &HashSet<String>,
) -> bool {
    if package_variant(pkg) == AurVariant::Bin {
        return false;
    }
    package_family_keys(pkg)
        .iter()
        .any(|key| preferred_families.contains(key))
}

fn build_binary_catalog(aur_archive: &Path, destination: &Path) -> Result<(), String> {
    let file = File::open(aur_archive).map_err(|error| error.to_string())?;
    let decoder = GzDecoder::new(BufReader::new(file));
    let packages: Vec<AurPackage> =
        serde_json::from_reader(decoder).map_err(|error| error.to_string())?;

    let manifest_path = shelly_manifest_path(aur_archive);
    let icons: HashMap<String, Vec<String>> = File::open(&manifest_path)
        .ok()
        .and_then(|file| serde_json::from_reader(BufReader::new(file)).ok())
        .unwrap_or_default();

    let referenced_dependencies = dependency_library_names(&packages);
    let now = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .map(|duration| duration.as_secs().min(i64::MAX as u64) as i64)
        .unwrap_or(0);

    let mut entries: Vec<AurPackage> = packages
        .into_iter()
        .filter(|pkg| {
            let maintained = pkg.Maintainer
                .as_deref()
                .map(str::trim)
                .map(|value| !value.is_empty())
                .unwrap_or(false);

            maintained
                // lib32-* packages are multilib compatibility counterparts, not
                // useful standalone software for AUR discovery.
                && !pkg.Name.starts_with("lib32-")
                && !out_of_date_too_long(pkg, now)
                && !should_hide_dependency_library(pkg, &referenced_dependencies)
        })
        .collect();

    // When a complete standard/-bin/-git family survives the normal safety
    // filters, prefer the prebuilt binary variant. A -bin package that is
    // marked out of date at all never triggers this collapse.
    let preferred_families = preferred_binary_families(&entries);
    if !preferred_families.is_empty() {
        entries.retain(|pkg| !should_hide_for_binary_variant(pkg, &preferred_families));
    }

    for pkg in &mut entries {
        pkg.Icon = resolve_icon(pkg, &icons);
    }

    let mut browse_order: Vec<usize> = (0..entries.len()).collect();
    browse_order.sort_unstable_by(|&a, &b| {
        entries[b]
            .Popularity
            .partial_cmp(&entries[a].Popularity)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| entries[b].NumVotes.cmp(&entries[a].NumVotes))
            .then_with(|| entries[a].Name.cmp(&entries[b].Name))
    });

    let cached = CachedAurCatalog {
        version: AUR_CATALOG_VERSION,
        entries,
        browse_order,
    };
    let bytes = rmp_serde::to_vec_named(&cached).map_err(|error| error.to_string())?;
    let tmp = destination.with_extension("bin.tmp");
    let mut output = File::create(&tmp).map_err(|error| error.to_string())?;
    output.write_all(&bytes).map_err(|error| error.to_string())?;
    output.flush().map_err(|error| error.to_string())?;
    output.sync_all().map_err(|error| error.to_string())?;
    fs::rename(&tmp, destination).map_err(|error| error.to_string())?;
    Ok(())
}

fn refresh_aur_archive_inner(path: &str, force: bool) -> Result<bool, String> {
    let destination = PathBuf::from(path);
    let manifest = shelly_manifest_path(&destination);
    let binary = catalog_path(&destination);
    let aur_needs_refresh = force || !cache_fresh(&destination);
    let icons_need_refresh = force || !cache_fresh(&manifest);
    let binary_missing = !binary.is_file();
    let binary_incompatible = !catalog_version_matches(&destination);
    let binary_outdated = match modified_time(&binary) {
        Some(binary_time) => {
            modified_time(&destination).map(|time| binary_time < time).unwrap_or(true)
                || modified_time(&manifest).map(|time| binary_time < time).unwrap_or(true)
        }
        None => true,
    };

    if !aur_needs_refresh
        && !icons_need_refresh
        && !binary_missing
        && !binary_incompatible
        && !binary_outdated
    {
        return Ok(false);
    }
    if let Some(parent) = destination.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }

    // Source downloads are staged atomically by download_to_path(). The existing
    // binary remains published and usable while all of this work happens.
    if aur_needs_refresh {
        download_to_path(AUR_ARCHIVE_URL, &destination, "LinuxToys AUR catalog")?;
    }

    // Icon enrichment is optional. A failed Shelly refresh retains the previous
    // manifest if one exists, otherwise the binary builder uses aurpackage.webp.
    if icons_need_refresh {
        let _ = download_to_path(
            SHELLY_ICON_MANIFEST_URL,
            &manifest,
            "LinuxToys AUR icon catalog",
        );
    }

    // Publish only after the complete new generation has parsed, filtered,
    // enriched, sorted and serialized successfully. On failure catalog.bin is
    // untouched, giving callers stale-while-refresh semantics.
    build_binary_catalog(&destination, &binary)?;

    // Publish the tiny compatibility marker only after catalog.bin itself has
    // been atomically replaced. A crash/failure before this point leaves the
    // generation marked stale and guarantees a rebuild on the next refresh.
    publish_catalog_version(&destination)?;
    Ok(true)
}

#[pyfunction]
pub fn refresh_aur_archive(py: Python<'_>, path: &str, force: bool) -> PyResult<bool> {
    // This function is called from a Python worker thread, but without releasing
    // the GIL the download + gzip/JSON parse + filtering + MessagePack write can
    // still starve GTK's Python callbacks. Keep the whole refresh transaction
    // outside the interpreter and reacquire the GIL only to return the result.
    py.allow_threads(|| refresh_aur_archive_inner(path, force))
        .map_err(io_py)
}
#[pyclass]
pub struct AurCatalog {
    entries: Vec<AurPackage>,
    // Developer omissions are resolved once at load time. This keeps the
    // persistent binary developer-policy agnostic while preserving O(page)
    // browsing and avoiding repeated Provides scans during search.
    browse_order: Vec<usize>,
    omitted: HashSet<usize>,
}

impl AurCatalog {
    fn package_to_py(&self, py: Python<'_>, pkg: &AurPackage) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("name", &pkg.Name)?;
        dict.set_item("package-name", &pkg.Name)?;
        dict.set_item("package_base", &pkg.PackageBase)?;
        dict.set_item("version", &pkg.Version)?;
        dict.set_item("description", pkg.Description.as_deref().unwrap_or(""))?;
        dict.set_item("developer", pkg.Maintainer.as_deref().unwrap_or(""))?;
        dict.set_item("license", pkg.License.join(", "))?;
        dict.set_item("homepage_url", pkg.URL.as_deref().unwrap_or(""))?;
        dict.set_item("repo", format!("https://aur.archlinux.org/packages/{}", pkg.Name))?;
        dict.set_item("appstream_id", format!("aur:{}", pkg.Name))?;
        dict.set_item("appstream_source", "aur")?;
        dict.set_item("appstream_badge", "aur.webp")?;
        dict.set_item("is_appstream_entry", true)?;
        dict.set_item("is_aur_entry", true)?;
        dict.set_item("is_script", true)?;
        dict.set_item("type", "native")?;
        dict.set_item("icon", if pkg.Icon.is_empty() { "aurpackage.webp" } else { &pkg.Icon })?;
        dict.set_item("has_app_page", false)?;
        dict.set_item("category", "aur")?;
        dict.set_item("screenshots", PyList::empty(py))?;
        dict.set_item("aur_votes", pkg.NumVotes)?;
        dict.set_item("aur_popularity", pkg.Popularity)?;
        dict.set_item("aur_out_of_date", pkg.OutOfDate)?;
        dict.set_item("aur_first_submitted", pkg.FirstSubmitted)?;
        dict.set_item("aur_last_modified", pkg.LastModified)?;
        dict.set_item("depends", &pkg.Depends)?;
        dict.set_item("makedepends", &pkg.MakeDepends)?;
        dict.set_item("optdepends", &pkg.OptDepends)?;
        dict.set_item("checkdepends", &pkg.CheckDepends)?;
        dict.set_item("conflicts", &pkg.Conflicts)?;
        dict.set_item("provides", &pkg.Provides)?;
        dict.set_item("replaces", &pkg.Replaces)?;
        dict.set_item("groups", &pkg.Groups)?;
        dict.set_item("keywords", &pkg.Keywords)?;
        Ok(dict.into())
    }
}

#[pymethods]
impl AurCatalog {
    fn len(&self) -> usize { self.browse_order.len() }

    #[pyo3(signature = (offset=0, limit=0))]
    fn browse(&self, py: Python<'_>, offset: usize, limit: usize) -> PyResult<Vec<PyObject>> {
        self.browse_order
            .iter()
            .copied()
            .skip(offset)
            .take(if limit == 0 { usize::MAX } else { limit })
            .map(|index| self.package_to_py(py, &self.entries[index]))
            .collect()
    }

    #[pyo3(signature = (query, limit=100))]
    fn search(&self, py: Python<'_>, query: &str, limit: usize) -> PyResult<Vec<(PyObject, i32)>> {
        let q = query.trim().to_lowercase();
        if q.len() < 2 { return Ok(Vec::new()); }
        let mut matches: Vec<(usize, i32)> = Vec::new();
        for (index, pkg) in self.entries.iter().enumerate() {
            if self.omitted.contains(&index) {
                continue;
            }
            let name = pkg.Name.to_lowercase();
            let description = pkg.Description.as_deref().unwrap_or("").to_lowercase();
            let maintainer = pkg.Maintainer.as_deref().unwrap_or("").to_lowercase();
            let keywords = pkg.Keywords.iter().any(|value| value.to_lowercase().contains(&q));
            let score = if name == q { 100 }
                else if name.starts_with(&q) { 90 }
                else if name.contains(&q) { 80 }
                else if maintainer.contains(&q) { 55 }
                else if keywords { 45 }
                else if description.contains(&q) { 35 }
                else { 0 };
            if score > 0 { matches.push((index, score)); }
        }
        matches.sort_unstable_by(|(ai, ascore), (bi, bscore)| {
            bscore.cmp(ascore)
                .then_with(|| self.entries[*bi].Popularity.partial_cmp(&self.entries[*ai].Popularity).unwrap_or(std::cmp::Ordering::Equal))
                .then_with(|| self.entries[*ai].Name.cmp(&self.entries[*bi].Name))
        });
        matches.into_iter().take(limit)
            .map(|(index, score)| Ok((self.package_to_py(py, &self.entries[index])?, score)))
            .collect()
    }
}

#[pyfunction]
#[pyo3(signature = (path, omit=Vec::new(), native_packages=Vec::new()))]
pub fn load_aur_catalog(
    py: Python<'_>,
    path: &str,
    omit: Vec<String>,
    native_packages: Vec<String>,
) -> PyResult<AurCatalog> {
    py.allow_threads(|| load_aur_catalog_inner(path, omit, native_packages))
}

fn load_aur_catalog_inner(
    path: &str,
    omit: Vec<String>,
    native_packages: Vec<String>,
) -> PyResult<AurCatalog> {
    let file = File::open(path).map_err(io_py)?;
    let cached: CachedAurCatalog =
        rmp_serde::from_read(BufReader::new(file)).map_err(io_py)?;
    if cached.version != AUR_CATALOG_VERSION {
        return Err(io_py(format!(
            "unsupported AUR catalog version {} (expected {})",
            cached.version, AUR_CATALOG_VERSION
        )));
    }

    // Resolve runtime-only exclusions once. catalog.bin remains independent of
    // both developer policy and the host's currently enabled native repositories.
    // dependency_name() strips version constraints from Provides entries.
    let omitted_names: HashSet<String> = omit
        .into_iter()
        .map(|value| value.trim().to_ascii_lowercase())
        .filter(|value| !value.is_empty())
        .collect();
    let native_names: HashSet<String> = native_packages
        .into_iter()
        .map(|value| value.trim().to_ascii_lowercase())
        .filter(|value| !value.is_empty())
        .collect();

    let omitted: HashSet<usize> = if omitted_names.is_empty() && native_names.is_empty() {
        HashSet::new()
    } else {
        cached.entries
            .iter()
            .enumerate()
            .filter_map(|(index, pkg)| {
                let package_name = pkg.Name.to_ascii_lowercase();
                let direct = omitted_names.contains(&package_name)
                    || native_names.contains(&package_name);
                let developer_provided = pkg.Provides.iter().any(|value| {
                    let name = dependency_name(value);
                    !name.is_empty() && omitted_names.contains(&name.to_ascii_lowercase())
                });

                // Native shadowing through Provides is deliberately strict:
                // every non-empty provided package identity must exist in the
                // enabled native repositories. One coincidental/virtual match
                // is not enough to hide the AUR package.
                let mut provided_names = pkg.Provides.iter()
                    .map(|value| dependency_name(value))
                    .filter(|name| !name.is_empty())
                    .peekable();
                let native_provides_match = provided_names.peek().is_some()
                    && provided_names.all(|name| {
                        native_names.contains(&name.to_ascii_lowercase())
                    });

                (direct || developer_provided || native_provides_match).then_some(index)
            })
            .collect()
    };

    let browse_order = if omitted.is_empty() {
        cached.browse_order
    } else {
        cached.browse_order
            .into_iter()
            .filter(|index| !omitted.contains(index))
            .collect()
    };

    Ok(AurCatalog {
        entries: cached.entries,
        browse_order,
        omitted,
    })
}
