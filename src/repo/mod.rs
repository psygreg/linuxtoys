use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde_json::Value;
use std::fs;
use std::path::{Component, Path, PathBuf};
use unicode_normalization::{char::is_combining_mark, UnicodeNormalization};
use walkdir::WalkDir;

fn signature(path: &Path) -> Option<(u128, u64)> {
    let md = fs::metadata(path).ok()?;
    let modified = md.modified().ok()?.duration_since(std::time::UNIX_EPOCH).ok()?.as_nanos();
    Some((modified, md.len()))
}

#[pyfunction]
pub(crate) fn file_signature(path: &str) -> Option<(u128, u64)> {
    signature(Path::new(path))
}

#[pyfunction]
pub(crate) fn repo_app_id(name: &str) -> Option<String> {
    let ascii: String = name
        .nfkd()
        .filter(|c| !is_combining_mark(*c))
        .filter(|c| c.is_ascii())
        .collect();
    let mut out = String::new();
    let mut separator = false;
    for c in ascii.chars() {
        if c.is_ascii_alphanumeric() {
            if separator && !out.is_empty() { out.push('_'); }
            separator = false;
            out.push(c);
        } else {
            separator = true;
        }
    }
    if out.is_empty() { return None; }
    out.make_ascii_uppercase();
    if out.as_bytes()[0].is_ascii_digit() { out = format!("APP_{out}"); }
    Some(out)
}

#[pyfunction]
pub(crate) fn normalize_appstream_overlay_id(value: &str) -> String {
    let value = value.trim();
    let value = value.strip_suffix(".desktop")
        .or_else(|| value.strip_suffix(".Desktop"))
        .unwrap_or(value);
    value.trim().to_lowercase()
}

#[pyfunction]
pub(crate) fn scan_repo_tree(scripts_dir: &str) -> (Vec<String>, Vec<String>, Vec<(String, Option<(u128,u64)>)>) {
    let base = fs::canonicalize(scripts_dir).unwrap_or_else(|_| PathBuf::from(scripts_dir));
    let mut json_paths = Vec::new();
    let mut markdown_paths = Vec::new();
    let main = base.join("repos.json");
    if main.is_file() { json_paths.push(main); }
    let lists = base.join("lists");
    if lists.is_dir() {
        let mut found_json = Vec::new();
        let mut found_md = Vec::new();
        for e in WalkDir::new(&lists).follow_links(false).into_iter().filter_map(Result::ok) {
            if !e.file_type().is_file() { continue; }
            let p = e.into_path();
            let lower = p.file_name().and_then(|x| x.to_str()).unwrap_or("").to_ascii_lowercase();
            if lower.ends_with(".json") { found_json.push(p); }
            else if lower.ends_with(".md") { found_md.push(p); }
        }
        found_json.sort(); found_md.sort();
        json_paths.extend(found_json); markdown_paths.extend(found_md);
    }
    let mut sigs = Vec::new();
    for p in json_paths.iter().chain(markdown_paths.iter()) {
        sigs.push((p.to_string_lossy().into_owned(), signature(p)));
    }
    (
        json_paths.into_iter().map(|p| p.to_string_lossy().into_owned()).collect(),
        markdown_paths.into_iter().map(|p| p.to_string_lossy().into_owned()).collect(),
        sigs,
    )
}

fn json_to_py(py: Python<'_>, value: &Value) -> PyResult<Py<PyAny>> {
    Ok(match value {
        Value::Null => py.None(),
        Value::Bool(v) => v.into_pyobject(py)?.to_owned().unbind().into_any(),
        Value::Number(v) => {
            if let Some(i) = v.as_i64() { i.into_pyobject(py)?.to_owned().unbind().into_any() }
            else if let Some(u) = v.as_u64() { u.into_pyobject(py)?.to_owned().unbind().into_any() }
            else { v.as_f64().unwrap_or(0.0).into_pyobject(py)?.to_owned().unbind().into_any() }
        },
        Value::String(v) => v.into_pyobject(py)?.to_owned().unbind().into_any(),
        Value::Array(values) => {
            let list = PyList::empty(py);
            for v in values { list.append(json_to_py(py, v)?)?; }
            list.unbind().into_any()
        },
        Value::Object(values) => {
            let dict = PyDict::new(py);
            for (k,v) in values { dict.set_item(k, json_to_py(py,v)?)?; }
            dict.unbind().into_any()
        }
    })
}

#[pyfunction]
pub(crate) fn load_json_entries(py: Python<'_>, path: &str) -> PyResult<Vec<Py<PyAny>>> {
    let content = match fs::read_to_string(path) { Ok(v) => v, Err(_) => return Ok(Vec::new()) };
    let parsed: Value = match serde_json::from_str(&content) { Ok(v) => v, Err(_) => return Ok(Vec::new()) };
    let values: Vec<Value> = match parsed { Value::Array(v) => v, v @ Value::Object(_) => vec![v], _ => Vec::new() };
    let mut out = Vec::with_capacity(values.len());
    for value in values {
        match value {
            Value::Object(mut map) => {
                map.insert("_list_source".into(), Value::String(path.into()));
                out.push(json_to_py(py, &Value::Object(map))?);
            }
            other => out.push(json_to_py(py, &other)?),
        }
    }
    Ok(out)
}

#[pyfunction]
pub(crate) fn load_markdown_text(path: &str) -> String {
    fs::read_to_string(path).map(|s| s.trim().to_owned()).unwrap_or_default()
}

#[pyfunction]
pub(crate) fn safe_join_below(base: &str, source_dir: &str, value: &str) -> Option<String> {
    let rel = Path::new(value);
    if rel.is_absolute() || rel.components().any(|c| matches!(c, Component::ParentDir)) { return None; }
    let base = fs::canonicalize(base).ok()?;
    let candidate = fs::canonicalize(Path::new(source_dir).join(rel)).ok()?;
    if candidate.starts_with(&base) { Some(candidate.to_string_lossy().into_owned()) } else { None }
}


fn as_nonempty_string(v: Option<&Value>) -> Option<&str> {
    v?.as_str().map(str::trim).filter(|s| !s.is_empty())
}

fn normalize_package_names_json(v: Option<&Value>) -> Option<Vec<String>> {
    match v? {
        Value::String(s) => {
            let s = s.trim();
            if s.is_empty() { None } else { Some(vec![s.to_owned()]) }
        }
        Value::Array(items) => {
            if items.is_empty() { return None; }
            let mut out = Vec::with_capacity(items.len());
            for item in items {
                let s = item.as_str()?.trim();
                if s.is_empty() { return None; }
                out.push(s.to_owned());
            }
            Some(out)
        }
        _ => None,
    }
}

const OS_KEYS_RS: &[&str] = &["debian","ubuntu","cachy","arch","steamos","fedora","rhel","suse","ostree","ublue","zorin","solus","pika","deepin","manjaro"];
const TYPE_PRIORITY_RS: &[&str] = &["ublue","steamos","deepin","zorin","pika","manjaro","cachy","ostree","ubuntu","debian","fedora","rhel","suse","solus","arch"];
const VALID_TYPES_RS: &[&str] = &["git","tar","bin","make","flathub","native","repository","url","external"];
const DESKTOP_KEYS_RS: &[&str] = &["gnome","plasma","hyprland","sway","other"];

fn resolve_install_type_json(entry: &serde_json::Map<String, Value>, compat: &[String], dev_mode: bool, dev_override: bool) -> Option<String> {
    let value = entry.get("type").unwrap_or(&Value::String("git".into())).clone();
    match value {
        Value::String(s) => {
            let s = s.trim().to_ascii_lowercase();
            VALID_TYPES_RS.contains(&s.as_str()).then_some(s)
        }
        Value::Object(map) if !map.is_empty() => {
            let mut normalized = std::collections::HashMap::new();
            for (key, value) in map {
                if key != "all" && !OS_KEYS_RS.contains(&key.as_str()) { return None; }
                let ty = value.as_str()?.trim().to_ascii_lowercase();
                if !VALID_TYPES_RS.contains(&ty.as_str()) { return None; }
                normalized.insert(key, ty);
            }
            if dev_mode && !dev_override {
                return normalized.get("all").cloned().or_else(|| normalized.values().next().cloned());
            }
            for key in TYPE_PRIORITY_RS {
                if compat.iter().any(|c| c == key) {
                    if let Some(v) = normalized.get(*key) { return Some(v.clone()); }
                }
            }
            normalized.get("all").cloned()
        }
        _ => None,
    }
}

fn validate_package_spec_json(v: Option<&Value>) -> bool {
    if normalize_package_names_json(v).is_some() { return true; }
    let Some(Value::Object(map)) = v else { return false; };
    if map.is_empty() { return false; }
    map.iter().all(|(k,v)| (k == "all" || OS_KEYS_RS.contains(&k.as_str())) && normalize_package_names_json(Some(v)).is_some())
}

fn validate_hook_json(v: &Value) -> bool {
    match v {
        Value::String(s) => !s.trim().is_empty(),
        Value::Object(map) if map.len() == 1 && map.contains_key("script") => {
            let Some(script) = map.get("script").and_then(Value::as_str).map(str::trim) else { return false; };
            if script.is_empty() || Path::new(script).is_absolute() { return false; }
            !Path::new(script).components().any(|c| matches!(c, Component::ParentDir))
        }
        _ => false,
    }
}


fn valid_release_selector_rs(v: Option<&Value>) -> bool {
    fn one(s:&str)->bool { let s=s.trim(); !s.is_empty() && s!="." && s!=".." && !s.contains('/') && !s.contains('\\') }
    match v { None=>true, Some(Value::String(s))=>one(s), Some(Value::Object(m)) if !m.is_empty()=>m.iter().all(|(k,v)|(k=="all"||OS_KEYS_RS.contains(&k.as_str()))&&v.as_str().is_some_and(one)), _=>false }
}
fn valid_http_url_rs(s:&str)->bool { url::Url::parse(s.trim()).ok().is_some_and(|u|matches!(u.scheme(),"http"|"https")&&u.host_str().is_some()) }
fn valid_services_rs(entry:&serde_json::Map<String,Value>)->bool {
    fn vals(v:&Value)->bool { match v { Value::String(s)=>!s.trim().is_empty(), Value::Array(a)=>a.iter().all(|x|x.as_str().is_some_and(|s|!s.trim().is_empty())), _=>false } }
    match entry.get("services") { None=>true, Some(Value::String(s))=>!s.trim().is_empty(), Some(Value::Array(a))=>a.iter().all(|x|x.as_str().is_some_and(|s|!s.trim().is_empty())), Some(Value::Object(m))=>m.keys().all(|k|matches!(k.as_str(),"system"|"user"))&&m.values().all(vals), _=>false }
}
fn tarball_post_valid_rs(entry:&serde_json::Map<String,Value>,keys:&[String],ty:&str)->bool {
    let uses=ty=="tar" || (ty=="url"&&resolve_url_kind_rs(entry,keys)==Some("tar")); if !uses{return true}
    entry.get("overrides").and_then(Value::as_object).and_then(|o|o.get("post")).is_some_and(validate_hook_json)
}
fn validate_static_entry(entry: &serde_json::Map<String, Value>, compat: &[String], dev_mode: bool, dev_override: bool) -> Option<String> {
    for field in ["name","repo","category"] {
        if as_nonempty_string(entry.get(field)).is_none() { return None; }
    }
    let has_desc = as_nonempty_string(entry.get("description")).is_some();
    let has_desc_file = entry.get("descriptions").or_else(|| entry.get("description-file")).and_then(Value::as_str).map(str::trim).is_some_and(|s| !s.is_empty());
    if !has_desc && !has_desc_file { return None; }

    let ty = resolve_install_type_json(entry, compat, dev_mode, dev_override)?;
    match ty.as_str() {
        "flathub" | "native" => if !validate_package_spec_json(entry.get("package-name")) { return None; },
        "git" | "tar" => if !valid_release_selector_rs(entry.get("package-name")) { return None; },
        "make" => {
            let source = entry.get("make-source").and_then(Value::as_str).unwrap_or("git").trim().to_ascii_lowercase();
            if source != "git" && source != "tar" { return None; }
            if let Some(cmd) = entry.get("make-command") {
                let Some(cmd) = cmd.as_str().map(str::trim) else { return None; };
                if cmd.is_empty() || !cmd.split(|c: char| !c.is_ascii_alphanumeric() && c != '_' && c != '-').any(|x| x == "install" || x.starts_with("install-") || x.starts_with("install_")) { return None; }
            }
            if source == "git" && entry.get("package-name").is_some() { return None; }
            if source == "tar" && !valid_release_selector_rs(entry.get("package-name")) { return None; }
        }
        "bin" => {
            let Some(asset) = entry.get("package-name").and_then(Value::as_str).map(str::trim) else { return None; };
            if asset.is_empty() || asset == "." || asset == ".." || asset.contains('/') || asset.contains('\\') || asset.chars().any(|c| "*?[".contains(c)) { return None; }
        }
        "url" => { let Some(urls)=entry.get("urls").and_then(Value::as_object) else{return None}; if urls.is_empty() || !urls.iter().any(|(k,v)| ["deb","rpm","pacman","pkg.tar.zst","flatpak","appimage","tar","bin"].contains(&k.as_str()) && usable_url_value(Some(v),entry)){return None} },
        "external" => { let Some(script)=as_nonempty_string(entry.get("script")) else{return None}; if !valid_http_url_rs(script) { let p=Path::new(script); if p.is_absolute()||p.components().any(|c|matches!(c,Component::ParentDir)){return None} } },
        "repository" => return None,
        _ => {}
    }

    if let Some(v) = entry.get("container") {
        let Some(s) = v.as_str() else { return None; };
        if !matches!(s.trim().to_ascii_lowercase().as_str(), "allow"|"deny") { return None; }
    }
    if let Some(v) = entry.get("license") {
        let Some(s) = v.as_str() else { return None; };
        let s=s.trim(); if s.is_empty() || s.len()>20 { return None; }
    }
    if let Some(v) = entry.get("wsl") {
        let Some(s)=v.as_str() else { return None; };
        if !matches!(s.trim().to_ascii_lowercase().as_str(),"yes"|"no") { return None; }
    }
    if let Some(v)=entry.get("desktop") {
        let vals: Vec<&Value> = match v { Value::String(_) => vec![v], Value::Array(a) if !a.is_empty()=>a.iter().collect(), _=>return None };
        if !vals.iter().all(|x| x.as_str().map(str::trim).is_some_and(|s| DESKTOP_KEYS_RS.contains(&s.to_ascii_lowercase().as_str()))) { return None; }
    }
    if let Some(v)=entry.get("dependencies") {
        if !v.is_null() {
            let Some(arr)=v.as_array() else { return None; };
            for dep in arr {
                let Some(d)=dep.as_object() else { return None; };
                let Some(dt)=d.get("type").and_then(Value::as_str) else { return None; };
                if dt!="native" && dt!="flathub" { return None; }
                if dt=="native" { if !validate_package_spec_json(d.get("package-name")) { return None; } }
                else if normalize_package_names_json(d.get("package-name")).is_none() { return None; }
            }
        }
    }
    if let Some(v)=entry.get("overrides") {
        let Some(o)=v.as_object() else { return None; };
        if o.keys().any(|k| !matches!(k.as_str(),"flatpak"|"pre"|"post"|"skip-user")) { return None; }
        if o.get("skip-user").is_some_and(|x| !x.is_boolean()) { return None; }
        for key in ["pre","post"] { if let Some(h)=o.get(key) { if !validate_hook_json(h) { return None; } } }
        if let Some(f)=o.get("flatpak") {
            let Some(arr)=f.as_array() else { return None; };
            for ov in arr {
                let Some(m)=ov.as_object() else { return None; };
                let scope=m.get("scope").and_then(Value::as_str);
                let typ=m.get("type").and_then(Value::as_str);
                let setting=m.get("setting").and_then(Value::as_str).map(str::trim);
                let target=m.get("target").and_then(Value::as_str).map(str::trim);
                if !matches!(scope,Some("user"|"system")) || !matches!(typ,Some("fs"|"name"|"dbus"|"share"|"env"|"runtime"|"device"|"socket"|"filesystem"|"talk-name"|"talk-dbus")) || setting.is_none_or(str::is_empty) || target.is_none_or(str::is_empty) { return None; }
            }
        }
    }
    Some(ty)
}

#[pyfunction]
pub(crate) fn prefilter_repo_entries(py: Python<'_>, entries_json: &str, compat_keys: Vec<String>, dev_mode: bool, dev_override: bool, containerized: bool, wsl: bool, override_container: bool) -> PyResult<Vec<Py<PyAny>>> {
    let parsed: Value = match serde_json::from_str(entries_json) { Ok(v)=>v, Err(_)=>return Ok(Vec::new()) };
    let Some(entries)=parsed.as_array() else { return Ok(Vec::new()); };
    let mut out=Vec::new();
    for entry in entries {
        let Some(map)=entry.as_object() else { continue; };
        if map.contains_key("appstream-name") { continue; }
        let Some(ty)=validate_static_entry(map,&compat_keys,dev_mode,dev_override) else { continue; };
        if !runtime_compatible_rs(map, &compat_keys, &ty, dev_mode && !dev_override, containerized, wsl, override_container) { continue; }
        let mut copied=map.clone(); copied.insert("_rust_resolved_type".into(),Value::String(ty));
        out.push(json_to_py(py,&Value::Object(copied))?);
    }
    Ok(out)
}

fn compat_has(keys: &[String], key: &str) -> bool { keys.iter().any(|k| k == key) }
fn string_list(v: Option<&Value>) -> Option<Vec<String>> {
    match v? {
        Value::String(s) => Some(vec![s.trim().to_ascii_lowercase()]),
        Value::Array(a) => a.iter().map(|x| x.as_str().map(|s| s.trim().to_ascii_lowercase())).collect(),
        _ => None,
    }
}
fn resolve_package_names_rs(entry: &serde_json::Map<String,Value>, keys: &[String]) -> Option<Vec<String>> {
    let p=entry.get("package-name")?;
    if let Some(v)=normalize_package_names_json(Some(p)) { return Some(v); }
    let m=p.as_object()?;
    for key in TYPE_PRIORITY_RS { if compat_has(keys,key) { if let Some(v)=normalize_package_names_json(m.get(*key)) { return Some(v); } } }
    normalize_package_names_json(m.get("all"))
}
fn has_pre_hook_rs(entry:&serde_json::Map<String,Value>)->bool { entry.get("overrides").and_then(Value::as_object).is_some_and(|o| o.get("pre").is_some()) }
fn usable_url_value(v:Option<&Value>,entry:&serde_json::Map<String,Value>)->bool {
    match v { Some(Value::String(s)) => { let s=s.trim(); s.starts_with("https://")||s.starts_with("http://") }, Some(Value::Object(m)) => m.get("env").and_then(Value::as_str).is_some_and(|s| !s.trim().is_empty()) && has_pre_hook_rs(entry), _=>false }
}
fn resolve_url_kind_rs(entry:&serde_json::Map<String,Value>,keys:&[String])->Option<&'static str> {
    let urls=entry.get("urls")?.as_object()?;
    let mut native=Vec::new();
    if ["debian","ubuntu","deepin","zorin","pika"].iter().any(|k|compat_has(keys,k)) { native.push("deb"); }
    if ["fedora","rhel","suse","ostree","ublue"].iter().any(|k|compat_has(keys,k)) { native.push("rpm"); }
    if ["arch","cachy","manjaro"].iter().any(|k|compat_has(keys,k)) { native.extend(["pkg.tar.zst","pacman"]); }
    for k in native { if usable_url_value(urls.get(k),entry) { return Some(match k {"deb"=>"deb","rpm"=>"rpm","pkg.tar.zst"=>"pkg.tar.zst",_=>"pacman"}); } }
    for k in ["appimage","flatpak","tar","bin"] { if usable_url_value(urls.get(k),entry) { return Some(k); } }
    None
}
fn make_uses_sudo_rs(entry:&serde_json::Map<String,Value>)->bool {
    let cmd=entry.get("make-command").and_then(Value::as_str).unwrap_or("sudo make install").trim();
    if cmd.is_empty(){return true} cmd.split(|c:char| c.is_whitespace()||";|&()".contains(c)).any(|x|x=="sudo")
}
fn services_empty_rs(entry:&serde_json::Map<String,Value>)->bool {
    match entry.get("services") { None=>true, Some(Value::String(s))=>s.trim().is_empty(), Some(Value::Array(a))=>a.is_empty(), Some(Value::Object(m))=> ["system","user"].iter().all(|k| match m.get(*k){None=>true,Some(Value::String(s))=>s.trim().is_empty(),Some(Value::Array(a))=>a.is_empty(),_=>false}), _=>false }
}
fn runtime_compatible_rs(entry:&serde_json::Map<String,Value>, keys:&[String], ty:&str, dev_plain:bool, containerized:bool, wsl:bool, override_container:bool)->bool {
    let sandboxed = ty=="flathub" || (ty=="url" && matches!(resolve_url_kind_rs(entry,keys),Some("flatpak"|"appimage"))) || entry.get("dependencies").and_then(Value::as_array).is_some_and(|a|a.iter().any(|d|d.get("type").and_then(Value::as_str)==Some("flathub")));
    if !override_container && containerized && (sandboxed || entry.get("container").and_then(Value::as_str).unwrap_or("allow").trim().eq_ignore_ascii_case("deny")) { return false; }
    if dev_plain { return true; }
    if let Some(v)=entry.get("wsl").and_then(Value::as_str) { if v.trim().eq_ignore_ascii_case("yes") != wsl { return false; } }
    if compat_has(keys,"steamos") {
        let user_make=ty=="make"&&!make_uses_sudo_rs(entry);
        match ty {"git"|"flathub"|"tar"|"bin"|"external"=>{},"make" if user_make=>{},"url" if matches!(resolve_url_kind_rs(entry,keys),Some("flatpak"|"appimage"|"tar"|"bin"))=>{},_=>return false}
        if !user_make && entry.get("dependencies").and_then(Value::as_array).is_some_and(|a|a.iter().any(|d|d.get("type").and_then(Value::as_str)==Some("native"))) {return false}
        if let Some(o)=entry.get("overrides").and_then(Value::as_object) { if o.get("pre").is_some(){return false} if o.get("post").is_some() && ty!="tar" && !(ty=="url"&&resolve_url_kind_rs(entry,keys)==Some("tar")){return false} }
        if !services_empty_rs(entry){return false}
    }
    if let Some(os)=entry.get("os") {
        let Some(vals)=string_list(Some(os)) else{return false}; let mut inc=false; let mut inc_match=false;
        for raw in vals { let excl=raw.starts_with('!'); let k=raw.strip_prefix('!').unwrap_or(&raw); if excl&&compat_has(keys,k){return false} if !excl {inc=true;if compat_has(keys,k){inc_match=true}} }
        if inc&&!inc_match{return false}
    }
    if let Some(d)=entry.get("desktop") { let Some(vals)=string_list(Some(d)) else{return false}; let ok=vals.iter().any(|x| {let k=format!("desktop-{x}");compat_has(keys,&k)}); if !ok{return false} }
    if let Some(s)=entry.get("systemd") { let Some(v)=s.as_str() else{return false}; let v=v.trim().to_ascii_lowercase(); if v=="yes"&&!compat_has(keys,"systemd"){return false} if v=="no"&&compat_has(keys,"systemd"){return false} }
    if entry.get("services").is_some()&&!compat_has(keys,"systemd"){return false}
    if ty=="flathub"&&!compat_has(keys,"systemd"){return false}
    if ty=="url" { let Some(k)=resolve_url_kind_rs(entry,keys) else{return false}; if k=="flatpak"&&!compat_has(keys,"systemd"){return false} }
    if let Some(h)=entry.get("hardware") { if !h.is_null() { let Some(m)=h.as_object() else{return false}; for kind in ["gpu","cpu"] { if let Some(vals)=string_list(m.get(kind)) { let required:Vec<String>=vals.into_iter().filter(|v|!v.is_empty()&&v!="all").map(|v|if v.starts_with(&format!("{kind}-")){v}else{format!("{kind}-{v}")}).collect(); if !required.is_empty()&&!required.iter().any(|k|compat_has(keys,k)){return false} } } } }
    if let Some(deps)=entry.get("dependencies").and_then(Value::as_array) { for d in deps { let Some(dm)=d.as_object() else{return false}; match dm.get("type").and_then(Value::as_str){Some("flathub") if !compat_has(keys,"systemd")=>return false,Some("native")=>{ let depkeys:Vec<String>=if compat_has(keys,"steamos")&&ty=="make"&&!make_uses_sudo_rs(entry){vec!["arch".into()]}else{keys.to_vec()}; if resolve_package_names_rs(dm,&depkeys).is_none(){return false}},_=>{}} } }
    true
}


fn load_git_db_rs(scripts_dir: &Path) -> serde_json::Map<String, Value> {
    let path = scripts_dir.join("git-db.json");
    let Ok(content) = fs::read_to_string(path) else { return serde_json::Map::new(); };
    let Ok(Value::Object(root)) = serde_json::from_str::<Value>(&content) else { return serde_json::Map::new(); };
    root.get("repositories").and_then(Value::as_object).cloned().unwrap_or_default()
}

fn normalize_git_repo_url_rs(value: Option<&Value>) -> Option<String> {
    let raw = value?.as_str()?.trim();
    let parsed = url::Url::parse(raw).ok()?;
    if parsed.scheme() != "https" || parsed.query().is_some() || parsed.fragment().is_some() || !parsed.username().is_empty() || parsed.password().is_some() || parsed.port().is_some() { return None; }
    let host = parsed.host_str()?.to_ascii_lowercase();
    let mut path = parsed.path().trim_matches('/').to_owned();
    if path.ends_with(".git") { path.truncate(path.len()-4); }
    let parts: Vec<&str> = path.split('/').filter(|p| !p.is_empty()).collect();
    if parts.iter().any(|p| *p == "." || *p == "..") { return None; }
    match host.as_str() { "github.com"|"codeberg.org" if parts.len()==2 => {}, "gitlab.com" if parts.len()>=2 => {}, _ => return None }
    Some(format!("https://{host}/{}", parts.join("/")))
}

fn canonical_machine_rs(machine: &str) -> Option<&'static str> {
    match machine.to_ascii_lowercase().as_str() {
        "x86_64"|"amd64"|"x64" => Some("x86_64"), "i386"|"i486"|"i586"|"i686"|"ia32"|"x86" => Some("i686"),
        "aarch64"|"arm64" => Some("aarch64"), "armv7l"|"armv7"|"armhf" => Some("armv7l"), "armv6l"|"armv6"|"armel" => Some("armv6l"),
        "riscv64" => Some("riscv64"), "ppc64le"|"ppc64el" => Some("ppc64le"), "ppc64" => Some("ppc64"), "s390x" => Some("s390x"), "loongarch64" => Some("loongarch64"), _ => None
    }
}

fn git_asset_matches_machine_rs(asset: &serde_json::Map<String,Value>, machine: &str) -> bool {
    let Some(canon)=canonical_machine_rs(machine) else{return false};
    let Some(a)=asset.get("architectures").and_then(Value::as_array) else{return true};
    if a.is_empty(){return true}
    let detected: Vec<&str>=a.iter().filter_map(Value::as_str).collect();
    detected.contains(&canon) || (canon=="x86_64" && detected.contains(&"i686"))
}

fn git_db_requirement_matches_rs(entry:&serde_json::Map<String,Value>, keys:&[String], ty:&str, db:&serde_json::Map<String,Value>, machine:&str)->bool {
    if entry.get("os").is_some() || ty!="git" { return true; }
    let Some(repo)=normalize_git_repo_url_rs(entry.get("repo")) else{return false};
    let Some(rec)=db.get(&repo).and_then(Value::as_object) else{return false};
    if rec.get("error").is_some_and(|v| !v.is_null() && v.as_bool()!=Some(false)) {return false}
    let Some(assets)=rec.get("assets").and_then(Value::as_array) else{return false};
    for a in assets { let Some(m)=a.as_object() else{continue}; if !git_asset_matches_machine_rs(m,machine){continue} match m.get("kind").and_then(Value::as_str) { Some("appimage")=>return true, Some("flatpak") if compat_has(keys,"systemd")=>return true, Some("pacman") if compat_has(keys,"arch")||compat_has(keys,"cachy")=>return true, Some("rpm") if ["fedora","rhel","ostree","ublue"].iter().any(|k|compat_has(keys,k))=>return true, Some("deb") if compat_has(keys,"debian")||compat_has(keys,"ubuntu")=>return true, Some("eopkg") if compat_has(keys,"solus")=>return true, _=>{} } }
    false
}

fn safe_list_path_rs(entry:&serde_json::Map<String,Value>, scripts_dir:&Path, value:&str)->Option<PathBuf>{
    let rel=Path::new(value.trim()); if rel.is_absolute(){return None}
    let source=Path::new(entry.get("_list_source")?.as_str()?); let source_dir=source.parent()?;
    let lists=fs::canonicalize(scripts_dir.join("lists")).ok()?; let candidate=fs::canonicalize(source_dir.join(rel)).ok()?;
    candidate.starts_with(&lists).then_some(candidate)
}
fn resolve_runtime_paths_rs(entry:&mut serde_json::Map<String,Value>, scripts_dir:&Path, ty:&str)->bool{
    let lists=fs::canonicalize(scripts_dir.join("lists")).unwrap_or_else(|_|scripts_dir.join("lists"));
    if let Some(Value::Object(mut o))=entry.get("overrides").cloned(){ for k in ["pre","post"] { if let Some(Value::Object(h))=o.get(k).cloned(){ if let Some(script)=h.get("script").and_then(Value::as_str){ let Some(p)=safe_list_path_rs(entry,scripts_dir,script) else{return false}; if !p.is_file(){return false} let Ok(rel)=p.strip_prefix(&lists) else{return false}; let mut nh=serde_json::Map::new(); nh.insert("script".into(),Value::String(rel.to_string_lossy().into_owned())); o.insert(k.into(),Value::Object(nh)); } } } entry.insert("overrides".into(),Value::Object(o)); }
    if ty=="external" { let Some(script)=entry.get("script").and_then(Value::as_str).map(str::trim) else{return false}; if !(script.starts_with("https://")||script.starts_with("http://")){ let Some(p)=safe_list_path_rs(entry,scripts_dir,script) else{return false}; if !p.is_file(){return false} let Ok(rel)=p.strip_prefix(&lists) else{return false}; entry.insert("script".into(),Value::String(rel.to_string_lossy().into_owned())); } }
    true
}

#[pyfunction]
pub(crate) fn build_repo_catalog(
    py: Python<'_>,
    scripts_dir: &str,
    compat_keys: Vec<String>,
    dev_mode: bool,
    dev_override: bool,
    containerized: bool,
    wsl: bool,
    override_container: bool,
    machine: String,
    translations_json: String,
    language: String,
) -> PyResult<Vec<Py<PyAny>>> {
    use std::collections::HashSet;

    let (json_paths, _, _) = scan_repo_tree(scripts_dir);
    let mut out = Vec::new();
    let mut seen_ids: HashSet<String> = HashSet::new();
    let mut seen_names: HashSet<String> = HashSet::new();
    let git_db = load_git_db_rs(Path::new(scripts_dir));
    let translations: serde_json::Map<String, Value> = serde_json::from_str::<Value>(&translations_json).ok().and_then(|v| v.as_object().cloned()).unwrap_or_default();

    for path in json_paths {
        let content = match fs::read_to_string(&path) {
            Ok(v) => v,
            Err(_) => continue,
        };
        let parsed: Value = match serde_json::from_str(&content) {
            Ok(v) => v,
            Err(_) => continue,
        };
        let values: Vec<Value> = match parsed {
            Value::Array(v) => v,
            v @ Value::Object(_) => vec![v],
            _ => continue,
        };

        for value in values {
            let Value::Object(mut map) = value else { continue; };
            map.insert("_list_source".into(), Value::String(path.clone()));
            if map.contains_key("appstream-name") { continue; }

            let Some(ty) = validate_static_entry(&map, &compat_keys, dev_mode, dev_override) else { continue; };
            if !runtime_compatible_rs(
                &map, &compat_keys, &ty, dev_mode && !dev_override,
                containerized, wsl, override_container,
            ) { continue; }
            if !valid_services_rs(&map) || !tarball_post_valid_rs(&map, &compat_keys, &ty) { continue; }

            if !(dev_mode && !dev_override) && !git_db_requirement_matches_rs(&map, &compat_keys, &ty, &git_db, &machine) { continue; }
            if !resolve_runtime_paths_rs(&mut map, Path::new(scripts_dir), &ty) { continue; }
            if !resolve_descriptions_rs(&mut map, &translations, &language) { continue; }
            let icon = resolve_icon_rs(&map, Path::new(scripts_dir));
            let screenshots = resolve_screenshots_rs(&map, Path::new(scripts_dir));
            map.insert("icon".into(), Value::String(icon));
            map.insert("screenshots".into(), Value::Array(screenshots.into_iter().map(Value::String).collect()));

            let Some(name) = map.get("name").and_then(Value::as_str).map(str::trim) else { continue; };
            let Some(app_id) = repo_app_id(name) else { continue; };
            let normalized_name = name.to_lowercase();
            if seen_ids.contains(&app_id) || seen_names.contains(&normalized_name) { continue; }
            seen_ids.insert(app_id);
            seen_names.insert(normalized_name);

            map.insert("_rust_resolved_type".into(), Value::String(ty));
            out.push(json_to_py(py, &Value::Object(map))?);
        }
    }
    Ok(out)
}

// Step 6 enrichment helpers. Repository-local presentation metadata is resolved
// before entries cross the PyO3 boundary; Python retains only shared commerce
// and index/developer annotations that are also consumed by AppStream overlays.
fn trimmed_str(map: &serde_json::Map<String, Value>, key: &str) -> String {
    map.get(key).and_then(Value::as_str).map(str::trim).unwrap_or("").to_owned()
}

fn catalog_translation_rs(catalog: &serde_json::Map<String, Value>, language: &str, tag: &str) -> String {
    if tag.trim().is_empty() { return String::new(); }
    let lang = if language.trim().is_empty() { "en" } else { language.trim() }.replace('_', "-");
    let base = lang.split('-').next().unwrap_or("en").to_owned();
    let mut candidates = vec![lang];
    if !candidates.contains(&base) { candidates.push(base); }
    if !candidates.iter().any(|x| x == "en") { candidates.push("en".into()); }
    for key in candidates {
        if let Some(s) = catalog.get(&key).and_then(Value::as_object)
            .and_then(|m| m.get(tag)).and_then(Value::as_str).map(str::trim).filter(|s| !s.is_empty()) {
            return s.to_owned();
        }
    }
    String::new()
}

fn load_description_catalog_rs(entry: &serde_json::Map<String, Value>) -> serde_json::Map<String, Value> {
    let Some(name) = entry.get("descriptions").or_else(|| entry.get("description-file"))
        .and_then(Value::as_str).map(str::trim).filter(|s| !s.is_empty()) else { return serde_json::Map::new(); };
    let p = Path::new(name);
    if p.is_absolute() || p.file_name().and_then(|x| x.to_str()) != Some(name) || !name.to_ascii_lowercase().ends_with(".json") { return serde_json::Map::new(); }
    let Some(source) = entry.get("_list_source").and_then(Value::as_str) else { return serde_json::Map::new(); };
    let Some(dir) = Path::new(source).parent() else { return serde_json::Map::new(); };
    let path = dir.join(name);
    if !path.is_file() { return serde_json::Map::new(); }
    let Ok(text) = fs::read_to_string(path) else { return serde_json::Map::new(); };
    serde_json::from_str::<Value>(&text).ok().and_then(|v| v.as_object().cloned()).unwrap_or_default()
}

fn resolve_long_content_rs(entry: &serde_json::Map<String, Value>, value: String) -> (String, String) {
    let value = value.trim().to_owned();
    if value.is_empty() { return (String::new(), "plain".into()); }
    if !value.to_ascii_lowercase().ends_with(".md") { return (value, "plain".into()); }
    let rel = Path::new(&value);
    if rel.is_absolute() || rel.components().any(|c| matches!(c, Component::ParentDir)) { return (String::new(), "markdown".into()); }
    let Some(source) = entry.get("_list_source").and_then(Value::as_str) else { return (String::new(), "markdown".into()); };
    let Some(source_dir) = Path::new(source).parent() else { return (String::new(), "markdown".into()); };
    let Ok(base) = fs::canonicalize(source_dir) else { return (String::new(), "markdown".into()); };
    let Ok(path) = fs::canonicalize(source_dir.join(rel)) else { return (String::new(), "markdown".into()); };
    if !path.starts_with(&base) || !path.is_file() { return (String::new(), "markdown".into()); }
    (fs::read_to_string(path).map(|s| s.trim().to_owned()).unwrap_or_default(), "markdown".into())
}

fn resolve_descriptions_rs(entry: &mut serde_json::Map<String, Value>, translations: &serde_json::Map<String, Value>, language: &str) -> bool {
    let mut description = trimmed_str(entry, "description");
    let mut description_tag = trimmed_str(entry, "description_tag");
    let mut localized = language == "en" && !description.is_empty();
    if !description_tag.is_empty() {
        if let Some(s) = translations.get(&description_tag).and_then(Value::as_str).map(str::trim).filter(|s| !s.is_empty()) { description=s.to_owned(); localized=true; }
    }
    let mut long = entry.get("long-description").or_else(|| entry.get("long_description")).and_then(Value::as_str).map(str::trim).unwrap_or("").to_owned();
    let mut long_tag = entry.get("long-description_tag").or_else(|| entry.get("long_description_tag")).and_then(Value::as_str).map(str::trim).unwrap_or("").to_owned();
    if !long_tag.is_empty() { if let Some(s)=translations.get(&long_tag).and_then(Value::as_str).map(str::trim).filter(|s|!s.is_empty()){long=s.to_owned();} }
    let catalog=load_description_catalog_rs(entry);
    if !catalog.is_empty() {
        if let Some(s)=catalog.get("description_tag").and_then(Value::as_str).map(str::trim).filter(|s|!s.is_empty()){description_tag=s.to_owned();}
        if let Some(s)=catalog.get("description_long_tag").and_then(Value::as_str).map(str::trim).filter(|s|!s.is_empty()){long_tag=s.to_owned();}
        let short=catalog_translation_rs(&catalog,language,&description_tag);
        if !short.is_empty(){
            description=short;
            let lang=language.replace('_',"-"); let base=lang.split('-').next().unwrap_or("en");
            localized=[lang.as_str(),base].iter().any(|k|catalog.get(*k).and_then(Value::as_object).and_then(|m|m.get(&description_tag)).and_then(Value::as_str).is_some_and(|s|!s.trim().is_empty()));
        }
        let l=catalog_translation_rs(&catalog,language,&long_tag); if !l.is_empty(){long=l;}
    }
    if description.is_empty(){return false}
    let (long,format)=resolve_long_content_rs(entry,long);
    entry.insert("description".into(),Value::String(description));
    entry.insert("description_tag".into(),Value::String(description_tag));
    entry.insert("description_localized".into(),Value::Bool(localized));
    entry.insert("long_description".into(),Value::String(long));
    entry.insert("long_description_tag".into(),Value::String(long_tag));
    entry.insert("long_description_format".into(),Value::String(format));
    true
}

fn resolve_icon_rs(entry:&serde_json::Map<String,Value>,scripts_dir:&Path)->String{
    let icon=entry.get("icon").and_then(Value::as_str).map(str::trim).filter(|s|!s.is_empty()).unwrap_or("application-x-executable");
    if !icon.contains('/')&&!icon.starts_with('.') {return icon.to_owned()}
    if Path::new(icon).is_absolute(){return "application-x-executable".into()}
    let Some(p)=safe_list_path_rs(entry,scripts_dir,icon) else{return "application-x-executable".into()};
    let lower=p.to_string_lossy().to_ascii_lowercase(); if p.is_file()&&(lower.ends_with(".svg")||lower.ends_with(".png")){p.to_string_lossy().into_owned()}else{"application-x-executable".into()}
}

fn resolve_screenshots_rs(entry:&serde_json::Map<String,Value>,scripts_dir:&Path)->Vec<String>{
    let vals:Vec<String>=match entry.get("screenshots"){Some(Value::String(s))=>vec![s.clone()],Some(Value::Array(a))=>a.iter().filter_map(Value::as_str).map(str::to_owned).collect(),_=>Vec::new()};
    let mut out=Vec::new(); let mut seen=std::collections::HashSet::new();
    for v in vals { let Some(p)=safe_list_path_rs(entry,scripts_dir,&v) else{continue}; if p.is_dir(){ let Ok(rd)=fs::read_dir(&p) else{continue}; let mut files:Vec<PathBuf>=rd.filter_map(Result::ok).map(|e|e.path()).filter(|x|x.is_file()).collect(); files.sort_by_key(|x|x.file_name().and_then(|s|s.to_str()).unwrap_or("").to_ascii_lowercase()); for f in files { let l=f.to_string_lossy().to_ascii_lowercase(); if [".png",".jpg",".jpeg",".webp",".svg"].iter().any(|e|l.ends_with(e)){let s=f.to_string_lossy().into_owned();if seen.insert(s.clone()){out.push(s)}} } } else if p.is_file(){let l=p.to_string_lossy().to_ascii_lowercase();if [".png",".jpg",".jpeg",".webp",".svg"].iter().any(|e|l.ends_with(e)){let s=p.to_string_lossy().into_owned();if seen.insert(s.clone()){out.push(s)}}} }
    out
}
