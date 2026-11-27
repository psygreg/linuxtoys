use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs;
use std::io::Write;
use std::hash::{BuildHasher, Hash, Hasher};
use std::sync::OnceLock;

fn json_to_py(py: Python<'_>, value: &Value) -> PyResult<Py<PyAny>> {
    crate::shared::json_to_py(py, value)
}

fn normalize_id(value: &str) -> String {
    crate::shared::normalize_appstream_id(value)
}


fn component_policy_keys_rs(item: &serde_json::Map<String, Value>) -> Vec<String> {
    let mut keys = Vec::new();
    let mut push = |value: &str, normalize: bool| {
        let key = if normalize { normalize_id(value) } else { value.trim().to_lowercase() };
        if !key.is_empty() && !keys.contains(&key) { keys.push(key); }
    };
    if let Some(v) = item.get("id").and_then(Value::as_str) { push(v, true); }
    if let Some(v) = item.get("flatpak_id").and_then(Value::as_str) { push(v, true); }
    if let Some(v) = item.get("snap_name").and_then(Value::as_str) { push(v, false); }
    if let Some(v) = item.get("snap_id").and_then(Value::as_str) { push(v, false); }
    if let Some(v) = item.get("name").and_then(Value::as_str) { push(v, false); }
    if let Some(pkgs) = item.get("packages").and_then(Value::as_array) {
        for pkg in pkgs.iter().filter_map(Value::as_str) { push(pkg, false); }
    }
    keys
}

// APPSTREAM_OMIT-only identities for catalog-specific sources. These namespaced
// forms exist purely for omission matching: preference, category overrides and
// every other id-keyed mechanism keep using the entries' own ids, so adding a
// key here can never change what an app resolves to or how it installs.
fn omission_keys_rs(item: &serde_json::Map<String, Value>) -> Vec<String> {
    let mut keys = component_policy_keys_rs(item);
    let source = item.get("source").and_then(Value::as_str).unwrap_or("");
    if source == "snap" {
        if let Some(name) = item.get("snap_name").and_then(Value::as_str) {
            let name = name.trim().to_lowercase();
            if !name.is_empty() { keys.push(format!("io.snapcraft.{}", name)); }
        }
        if let Some(id) = item.get("snap_id").and_then(Value::as_str) {
            let id = id.trim().to_lowercase();
            if !id.is_empty() { keys.push(id); }
        }
    }
    if source == "homebrew" {
        if let Some(name) = item.get("name").and_then(Value::as_str) {
            let name = name.trim().to_lowercase();
            if !name.is_empty() { keys.push(format!("homebrew.{}", name)); }
        }
    }
    keys
}

fn reconcile_snap_common_ids_rs(components: &mut [serde_json::Map<String, Value>]) {
    // Snap Store records can advertise several common IDs. snap_catalog.py keeps
    // all of them in snap_common_ids but uses only the first one as `id`.
    // Resolve any common ID that matches an existing native/Flatpak component so
    // source grouping sees the Snap as another source for that application.
    let canonical_ids: std::collections::HashMap<String, String> = components.iter()
        .filter(|m| m.get("source").and_then(Value::as_str) != Some("snap"))
        .filter_map(|m| {
            let id = m.get("id").and_then(Value::as_str)?.trim();
            (!id.is_empty()).then(|| (normalize_id(id), id.to_string()))
        })
        .collect();

    for component in components.iter_mut()
        .filter(|m| m.get("source").and_then(Value::as_str) == Some("snap"))
    {
        let matched = component.get("snap_common_ids")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .find_map(|common_id| canonical_ids.get(&normalize_id(common_id)).cloned());

        if let Some(id) = matched {
            component.insert("id".into(), Value::String(id));
        }
    }
}

fn apply_snap_identity_overlays_rs(components: &mut [serde_json::Map<String, Value>], overlays: &Value) {
    let Some(overlays) = overlays.as_object() else { return; };
    for component in components.iter_mut().filter(|m| m.get("source").and_then(Value::as_str) == Some("snap")) {
        let snap_name = component.get("snap_name").and_then(Value::as_str).unwrap_or("");
        if snap_name.is_empty() { continue; }
        if let Some((appstream_id, _)) = overlays.iter().find(|(_, v)| {
            v.get("snap_name").and_then(Value::as_str).is_some_and(|n| n.eq_ignore_ascii_case(snap_name))
        }) {
            component.insert("id".into(), Value::String(appstream_id.clone()));
        }
    }
}

#[pyfunction]
pub(crate) fn load_appstream_catalog(py: Python<'_>, path: &str) -> PyResult<Vec<Py<PyAny>>> {
    // I/O and JSON parsing are pure Rust. Do not block GTK's Python main loop.
    let values: Vec<Value> = py.allow_threads(|| {
        let content = fs::read_to_string(path).ok()?;
        let parsed: Value = serde_json::from_str(&content).ok()?;
        parsed.as_array().map(|values| {
            values.iter().filter(|value| value.is_object()).cloned().collect()
        })
    }).unwrap_or_default();

    // Python object materialization still requires the GIL.
    values.iter().map(|value| json_to_py(py, value)).collect()
}

fn py_to_json(obj: &Bound<'_, PyAny>) -> PyResult<Value> {
    if obj.is_none() { return Ok(Value::Null); }
    if let Ok(v) = obj.extract::<bool>() { return Ok(Value::Bool(v)); }
    if let Ok(v) = obj.extract::<i64>() { return Ok(Value::Number(v.into())); }
    if let Ok(v) = obj.extract::<f64>() { return Ok(serde_json::Number::from_f64(v).map(Value::Number).unwrap_or(Value::Null)); }
    if let Ok(v) = obj.extract::<String>() { return Ok(Value::String(v)); }
    if let Ok(d) = obj.downcast::<PyDict>() {
        let mut m = serde_json::Map::new();
        for (k,v) in d.iter() { m.insert(k.extract::<String>()?, py_to_json(&v)?); }
        return Ok(Value::Object(m));
    }
    if let Ok(l) = obj.downcast::<PyList>() {
        let mut a=Vec::with_capacity(l.len()); for v in l.iter(){a.push(py_to_json(&v)?);} return Ok(Value::Array(a));
    }
    if let Ok(t) = obj.downcast::<pyo3::types::PyTuple>() {
        let mut a=Vec::with_capacity(t.len()); for v in t.iter(){a.push(py_to_json(&v)?);} return Ok(Value::Array(a));
    }
    Ok(Value::Null)
}

fn locale_candidates(lang:&str)->Vec<String>{
    let code=if lang.trim().is_empty(){"en".to_string()}else{lang.trim().replace('_',"-")};
    let language=code.split('-').next().unwrap_or("en").to_lowercase();
    let mut out=Vec::new(); for v in [code.clone(),code.replace('-',"_"),language] {if !v.is_empty()&&!out.contains(&v){out.push(v)}} out
}
fn localized(m:&serde_json::Map<String,Value>,field:&str,lang:&str,fallback:Value)->(Value,String){
    let Some(vals)=m.get(field).and_then(Value::as_object) else{return(fallback,String::new())};
    for c in locale_candidates(lang){for(k,v)in vals{if k.replace('_',"-").eq_ignore_ascii_case(&c.replace('_',"-"))&&!v.is_null(){return(v.clone(),k.clone())}}}
    if let Some(v)=vals.get(""){if !v.is_null(){return(v.clone(),"en".into())}}
    (fallback,String::new())
}
fn has_localized(m:&serde_json::Map<String,Value>,field:&str,lang:&str)->bool{
    let language=lang.replace('_',"-").split('-').next().unwrap_or("en").to_lowercase(); if language=="en" {return m.get("summary").and_then(Value::as_str).is_some_and(|s|!s.is_empty())}
    let Some(vals)=m.get(field).and_then(Value::as_object) else{return false}; locale_candidates(lang).iter().any(|c|vals.iter().any(|(k,v)|k.replace('_',"-").eq_ignore_ascii_case(&c.replace('_',"-"))&&!v.is_null()))
}
fn first_category(cands:&Value, exact:&std::collections::HashSet<String>, by:&std::collections::HashMap<String,Vec<String>>)->Option<String>{
    for c in cands.as_array()? {let s=c.as_str()?.trim_matches('/'); if exact.contains(s){return Some(s.into())} if let Some(v)=by.get(s){if let Some(x)=v.first(){return Some(x.clone())}}} None
}
fn category_path_is_within_rs(path:&str, parent:&str)->bool{
    path==parent||path.strip_prefix(parent).is_some_and(|suffix|suffix.starts_with('/'))
}
/// Exact-path set + suffix index for the category resolvers, built once from
/// the indexed category paths.
fn category_index_maps(paths: &[String]) -> (std::collections::HashSet<String>, std::collections::HashMap<String, Vec<String>>) {
    let mut exact = std::collections::HashSet::new();
    let mut by: std::collections::HashMap<String, Vec<String>> = std::collections::HashMap::new();
    for path in paths {
        let path = path.replace('\\', "/").trim_matches('/').to_string();
        if path.is_empty() || path == "lists" { continue; }
        exact.insert(path.clone());
        by.entry(path.rsplit('/').next().unwrap_or(&path).into()).or_default().push(path);
    }
    for values in by.values_mut() {
        values.sort_by_key(|p| (p.matches('/').count(), p.clone()));
    }
    (exact, by)
}

fn resolve_category_rs(cats:&Value, paths:&[String], cfg:&Value)->Option<String>{
    let set:std::collections::HashSet<&str>=cats.as_array()?.iter().filter_map(Value::as_str).collect();
    let (exact, by)=category_index_maps(paths);
    let o=cfg.as_object()?;
    let main_map=o.get("main").and_then(Value::as_object);
    let preferred_main=o.get("main_priority").and_then(Value::as_array).into_iter().flatten().filter_map(Value::as_str).find_map(|key|{
        if !set.contains(key){return None}
        let candidates=main_map?.get(key)?;
        Some((key,first_category(candidates,&exact,&by)?))
    });

    // Emulator is a useful refinement of a game/emulator category, but should
    // not defeat an unrelated, more specific Main category.
    if set.contains("Emulator"){
        if let Some(category)=first_category(&serde_json::json!(["emu"]),&exact,&by){
            let relevant=preferred_main.as_ref().map_or(true,|(key,parent)|{
                *key=="Game"||*key=="Emulator"||category_path_is_within_rs(&category,parent)
            });
            if relevant{return Some(category)}
        }
    }

    if let Some(rules)=o.get("expressions").and_then(Value::as_array){
        for rule in rules{
            let Some(parts)=rule.as_array() else{continue};
            let Some(required)=parts.first().and_then(Value::as_array) else{continue};
            let Some(destinations)=parts.get(1) else{continue};
            let required:Option<Vec<&str>>=required.iter().map(Value::as_str).collect();
            let Some(required)=required else{continue};
            if required.is_empty()||!required.iter().all(|category|set.contains(category)){continue}
            let Some(category)=first_category(destinations,&exact,&by) else{continue};
            let relevant=preferred_main.as_ref().map_or(true,|(main_key,main_path)|{
                required.iter().any(|category|category==main_key)
                    ||category_path_is_within_rs(&category,main_path)
            });
            if relevant{return Some(category)}
        }
    }

    let generic_main_categories=o.get("generic_main_categories").and_then(Value::as_array);
    if let Some((main_key,main_category))=preferred_main{
        let generic=generic_main_categories.is_some_and(|categories|{
            categories.iter().any(|category|category.as_str()==Some(main_key))
        });
        if let Some(priority)=o.get("standalone_priority").and_then(Value::as_array){
            if let Some(additional)=o.get("additional").and_then(Value::as_object){
                for key in priority.iter().filter_map(Value::as_str){
                    if !set.contains(key){continue}
                    let Some(candidates)=additional.get(key) else{continue};
                    if let Some(category)=first_category(candidates,&exact,&by){
                        if generic||category_path_is_within_rs(&category,&main_category){return Some(category)}
                    }
                }
            }
        }
        return Some(main_category)
    }

    if let Some(priority)=o.get("standalone_priority").and_then(Value::as_array){
        if let Some(additional)=o.get("additional").and_then(Value::as_object){
            for key in priority.iter().filter_map(Value::as_str){
                if !set.contains(key){continue}
                if let Some(candidates)=additional.get(key){
                    if let Some(category)=first_category(candidates,&exact,&by){return Some(category)}
                }
            }
        }
    }
    None
}
fn resolve_component_category_rs(component:&serde_json::Map<String,Value>, paths:&[String], cfg:&Value)->Option<String>{
    if let Some(overrides)=cfg.get("overrides").and_then(Value::as_object){
        let id=normalize_id(component.get("id").and_then(Value::as_str).unwrap_or(""));
        if !id.is_empty(){
            if let Some(destination)=overrides.iter()
                .find(|(key,_)|normalize_id(key)==id)
                .and_then(|(_,value)|value.as_str())
                .map(str::trim)
                .filter(|value|!value.is_empty())
            {
                let (exact, by) = category_index_maps(paths);
                if let Some(category) = first_category(&serde_json::json!([destination]), &exact, &by) { return Some(category) }
            }
        }
    }
    if component.get("source").and_then(Value::as_str) == Some("homebrew") { return Some("homebrew".into()); }
    if component.get("source").and_then(Value::as_str) == Some("nix") {
        if let Some(category)=component.get("nix_category").and_then(Value::as_str).filter(|value|!value.is_empty()) {
            let (exact, by) = category_index_maps(paths);
            if let Some(category) = first_category(&serde_json::json!([category]), &exact, &by) { return Some(category) }
        }
        // Merged Nix cards borrow the group's AppStream categories while the
        // install identity stays Nix. Honour those categories instead of
        // dropping the card into the standalone Nix Packages group; raw/no-API
        // packages keep that fallback.
        if let Some(category)=resolve_category_rs(component.get("categories").unwrap_or(&Value::Null),paths,cfg){
            return Some(category)
        }
        return Some("nix".into());
    }
    resolve_category_rs(component.get("categories").unwrap_or(&Value::Null),paths,cfg)
}
fn flatten_blocks(v:&Value)->String{let Some(a)=v.as_array()else{return String::new()};let mut blocks=Vec::new();for b in a{let Some(m)=b.as_object()else{continue};if m.get("type").and_then(Value::as_str)==Some("paragraph"){if let Some(sp)=m.get("spans").and_then(Value::as_array){blocks.push(sp.iter().filter_map(|s|s.get("text").and_then(Value::as_str)).collect::<Vec<_>>().join(" ").trim().to_string())}}else if let Some(items)=m.get("items").and_then(Value::as_array){blocks.push(items.iter().filter_map(|i|i.as_array()).map(|sp|sp.iter().filter_map(|s|s.get("text").and_then(Value::as_str)).collect::<Vec<_>>().join(" ").trim().to_string()).collect::<Vec<_>>().join("\n"))}}blocks.into_iter().filter(|s|!s.is_empty()).collect::<Vec<_>>().join("\n\n")}
fn clean_screens(v:Option<&Value>)->Value{let mut out=Vec::new();if let Some(a)=v.and_then(Value::as_array){for s in a{if let Some(m)=s.as_object(){let mut imgs=Vec::new();if let Some(ia)=m.get("images").and_then(Value::as_array){for i in ia{let Some(im)=i.as_object()else{continue};let url=im.get("url").and_then(Value::as_str).unwrap_or("").trim();if url.is_empty(){continue}imgs.push(serde_json::json!({"url":url,"width":im.get("width").and_then(Value::as_i64).unwrap_or(0).max(0),"height":im.get("height").and_then(Value::as_i64).unwrap_or(0).max(0)}))}}if !imgs.is_empty(){out.push(serde_json::json!({"images":imgs}))}}else if let Some(p)=s.as_str(){if !p.trim().is_empty(){out.push(Value::String(p.trim().into()))}}}}Value::Array(out)}

fn adapt_appstream_maps_values(components:Vec<serde_json::Map<String,Value>>, category_paths:Vec<String>, category_config_json:&str, lang:&str, curated_ids:Vec<String>, curated_packages:Vec<String>, curated_names:Vec<String>, overlays_json:&str, native_badge:&str)->Vec<Value>{
    let cfg:Value=serde_json::from_str(category_config_json).unwrap_or(Value::Null);let overlays:Value=serde_json::from_str(overlays_json).unwrap_or_else(|_|serde_json::json!({}));let ov=overlays.as_object();let ids:std::collections::HashSet<String>=curated_ids.into_iter().map(|s|s.to_lowercase()).collect();let pkgs:std::collections::HashSet<String>=curated_packages.into_iter().map(|s|s.to_lowercase()).collect();let names:std::collections::HashSet<String>=curated_names.into_iter().map(|s|s.to_lowercase()).collect();let mut out=Vec::new();
    for m in components {let brew=m.get("source").and_then(Value::as_str)==Some("homebrew");let nix=m.get("source").and_then(Value::as_str)==Some("nix");let id=m.get("id").and_then(Value::as_str).unwrap_or("");if id.is_empty()||(!brew&&ids.contains(&id.to_lowercase())){continue}if !brew&&m.get("name").and_then(Value::as_str).is_some_and(|n|names.contains(&n.to_lowercase())){continue}if !brew&&m.get("packages").and_then(Value::as_array).is_some_and(|a|a.iter().filter_map(Value::as_str).any(|p|pkgs.contains(&p.to_lowercase()))){continue}
        let Some(category)=resolve_component_category_rs(&m,&category_paths,&cfg) else{continue};let packages:Vec<String>=m.get("packages").and_then(Value::as_array).into_iter().flatten().filter_map(Value::as_str).map(str::to_string).collect();if packages.is_empty(){continue}
        let (name,_)=localized(&m,"localized_names",lang,m.get("name").cloned().unwrap_or(Value::String(String::new())));let(summary,_)=localized(&m,"localized_summaries",lang,m.get("summary").cloned().unwrap_or(Value::String(String::new())));let(dev,_)=localized(&m,"localized_developers",lang,m.get("developer").cloned().unwrap_or(Value::String(String::new())));let(blocks,bloc)=localized(&m,"localized_descriptions",lang,m.get("description_blocks").cloned().unwrap_or_else(||Value::Array(vec![])));let shots=clean_screens(m.get("screenshots"));let source=m.get("source").and_then(Value::as_str).unwrap_or("native");let flat=source=="flatpak";let snap=source=="snap";let origin=m.get("origin").and_then(Value::as_str).unwrap_or("");let scope=m.get("flatpak_scope").and_then(Value::as_str).unwrap_or("");let long=flatten_blocks(&blocks);
        let mut e=serde_json::Map::new();macro_rules! s { ($k:expr, $v:expr) => {{ let _ = e.insert($k.into(), Value::String($v.to_string())); }} }
        s!("id",id);e.insert("name".into(),name);s!("appstream_canonical_name",m.get("name").and_then(Value::as_str).unwrap_or(id));e.insert("description".into(),summary);s!("description_tag","");e.insert("description_localized".into(),Value::Bool(has_localized(&m,"localized_summaries",lang)));s!("long_description",long);e.insert("long_description_blocks".into(),blocks);s!("long_description_locale",bloc);s!("long_description_tag","");s!("long_description_format",m.get("metadata_description_format").and_then(Value::as_str).filter(|value|!value.is_empty()).unwrap_or(if snap{"markdown"}else{"appstream"}));e.insert("screenshots".into(),shots.clone());
        for(k,src)in [("homepage_url","homepage"),("donate","donation"),("donate_url","donation"),("license","license")]{s!(k,m.get(src).and_then(Value::as_str).unwrap_or(""));}e.insert("developer".into(),dev);let icon_value=if brew{"brewpkg.webp"}else if nix{let candidate=m.get("icon").and_then(Value::as_str).unwrap_or("");if source_icon_rank_rs(candidate)>1{candidate}else{"nix.svg"}}else{m.get("icon").and_then(Value::as_str).unwrap_or("application-x-executable")};s!("icon",icon_value);s!("category",category);s!("type",if flat{"flathub"}else if snap{"snap"}else if brew{"homebrew"}else if nix{"nix"}else if source=="appimage"{"appimage"}else{"native"});e.insert("package-name".into(),if flat||snap||brew||nix||source=="appimage"{Value::String(packages.first().cloned().unwrap_or_else(||id.into()))}else{Value::Array(packages.iter().cloned().map(Value::String).collect())});s!("repo",if origin.is_empty(){"appstream"}else{origin});for(k,v)in [("revert","yes"),("reboot","no")]{s!(k,v)}for k in ["is_script","is_repo_entry","is_appstream_entry"]{e.insert(k.into(),Value::Bool(true));}e.insert("is_subcategory".into(),Value::Bool(false));s!("appstream_id",id);s!("appstream_launchable",m.get("launchable").and_then(Value::as_str).unwrap_or(""));s!("appstream_source",source);s!("appstream_origin",origin);for k in ["flatpak_remote","flatpak_scope","flatpak_installation","flatpak_ref","flatpak_arch","flatpak_branch"]{s!(k,m.get(k).and_then(Value::as_str).unwrap_or(""));}for k in ["snap_name","snap_id","snap_channel","snap_confinement"]{s!(k,m.get(k).and_then(Value::as_str).unwrap_or(""));}e.insert("overrides".into(),if flat&&scope=="system"{serde_json::json!({"skip-user":true})}else{serde_json::json!({})});for k in ["review_rating","review_count"]{e.insert(k.into(),m.get(k).cloned().unwrap_or(Value::Null));}s!("appstream_version",m.get("version").and_then(Value::as_str).unwrap_or(""));s!("repo_app_id",id);e.insert("is_new".into(),Value::Bool(false));e.insert("is_verified".into(),Value::Bool(flat&&m.get("verified").and_then(Value::as_bool).unwrap_or(false)));s!("native_distro_badge",if flat||snap||brew||nix||source=="appimage"{""}else{native_badge});s!("appstream_badge",if flat{if origin=="flatpark"{"distros/flatpark.webp"}else{"distros/flathub.webp"}}else if snap{"snapbadge.webp"}else if brew{"brew.png"}else if nix{"nix.svg"}else if source=="appimage"{"appimages.webp"}else{""});e.insert("has_app_page".into(),Value::Bool(brew||nix||source=="appimage"||!long.is_empty()||shots.as_array().is_some_and(|a|!a.is_empty())));s!("path",format!("appstream://{source}/{id}"));
        if source=="appimage" {
            e.insert("appimage_links".into(),m.get("appimage_links").cloned().unwrap_or(Value::Array(vec![])));
            e.insert("appimage_needs_resolution".into(),Value::Bool(true));
        }
        if brew { e.insert("homebrew_install_count".into(), m.get("homebrew_install_count").cloned().unwrap_or(Value::Number(0.into()))); s!("homebrew_name",packages.first().map(String::as_str).unwrap_or("")); s!("registry_name",id); }
        if nix { s!("nix_name",m.get("nix_name").and_then(Value::as_str).unwrap_or(packages.first().map(String::as_str).unwrap_or(""))); s!("nix_pname",m.get("nix_pname").and_then(Value::as_str).unwrap_or("")); s!("nix_version",m.get("nix_version").and_then(Value::as_str).unwrap_or("")); s!("nix_scope",m.get("nix_scope").and_then(Value::as_str).unwrap_or("home-manager")); s!("registry_name",id); }
        if let Some(overlay)=ov.and_then(|o|o.get(&normalize_id(id))).and_then(Value::as_object){for(k,v)in overlay{e.insert(k.clone(),v.clone());}if overlay.get("purchase_options").is_some()||overlay.get("subscription_options").is_some(){e.insert("has_app_page".into(),Value::Bool(true));}}
        if let Some(alts)=m.get("_source_alternatives").and_then(Value::as_array){let mut opts=vec![Value::Object(e.clone())];for a in alts{if let Value::Object(am)=a{let nested=adapt_appstream_maps_values(vec![am.clone()],category_paths.clone(),category_config_json,lang,vec![],vec![],vec![],overlays_json,native_badge);if let Some(n)=nested.into_iter().next(){opts.push(n);}}}if opts.len()>1{e.insert("source_options".into(),Value::Array(opts));s!("recommended_source",m.get("_source_recommended").and_then(Value::as_str).unwrap_or(source));}}
        out.push(Value::Object(e));
    }
    out.sort_by_key(|x|x.get("name").and_then(Value::as_str).unwrap_or("").to_lowercase());out
}

fn source_option_key_rs(item: &serde_json::Map<String, Value>) -> String {
    let source = item.get("source").and_then(Value::as_str).unwrap_or("native");
    if source == "nix" {
        let scope = item.get("nix_scope").and_then(Value::as_str).unwrap_or("");
        return format!("nix:{scope}");
    }
    if source == "appimage" {
        let id = normalize_id(item.get("id").and_then(Value::as_str).unwrap_or(""));
        let name = item.get("name").and_then(Value::as_str).unwrap_or("");
        let name = normalized_app_name_rs(name);
        if !id.is_empty() {
            return if name.is_empty(){format!("appimage:{id}")}else{format!("appimage:{id}:{name}")};
        }
        return if name.is_empty() { source.to_string() } else { format!("appimage:{name}") };
    }
    if source != "flatpak" { return source.to_string(); }
    let scope = item.get("flatpak_scope").and_then(Value::as_str).unwrap_or("");
    let installation = item.get("flatpak_installation").and_then(Value::as_str).unwrap_or("");
    let remote = item.get("flatpak_remote").and_then(Value::as_str).unwrap_or("");
    format!("flatpak:{scope}:{installation}:{remote}")
}
fn component_identity_rs(item:&serde_json::Map<String,Value>)->(String,String){
    (normalize_id(item.get("id").and_then(Value::as_str).unwrap_or("")), item.get("name").and_then(Value::as_str).unwrap_or("").trim().to_lowercase())
}
fn normalized_app_name_rs(name:&str)->String{
    name.chars().flat_map(char::to_lowercase).filter(|ch|ch.is_alphanumeric()).collect()
}
fn canonical_app_name_rs(name:&str)->String{
    // Catalog sources often append a generic descriptor to the same app name:
    // Flathub calls it "Chromium Web Browser" while Snap and Nixpkgs call it
    // "Chromium". Strip only trailing descriptor words so distinct qualifiers
    // (for example "Ungoogled Chromium" or "Chromium B.S.U.") remain separate.
    let words:Vec<&str>=name.split_whitespace().collect();
    let mut end=words.len();
    while end>1{
        let word=normalized_app_name_rs(words[end-1]);
        if matches!(word.as_str(),"web"|"browser"|"launcher"){end-=1}else{break}
    }
    let canonical=normalized_app_name_rs(&words[..end].join(" "));
    if canonical.chars().count()>=4{canonical}else{normalized_app_name_rs(name)}
}
fn is_appimage_variant_suffix_rs(suffix:&str)->bool{
    !suffix.is_empty()&&(suffix.chars().all(|ch|ch.is_ascii_digit())||suffix.strip_prefix("asm").is_some_and(|digits|!digits.is_empty()&&digits.chars().all(|ch|ch.is_ascii_digit())))
}
fn appimage_name_aliases_rs(name:&str)->Vec<String>{
    let lowered=name.trim().to_lowercase();
    let exact=canonical_app_name_rs(&lowered);
    if exact.is_empty(){return Vec::new()}
    let mut aliases=vec![exact.clone()];
    let mut push_base=|base:&str|{
        let base=canonical_app_name_rs(base);
        if base.chars().count()>=4&&!aliases.contains(&base){aliases.push(base);}
    };

    // AppImage feeds sometimes append a release/version or build flavor to the
    // application name (e.g. "FreeCAD 2" or "FreeCAD-asm3"). Keep the exact
    // form first, then expose a conservative base-name alias for matching.
    for (index, separator) in lowered.char_indices().rev(){
        if separator.is_alphanumeric(){continue}
        let suffix=normalized_app_name_rs(&lowered[index+separator.len_utf8()..]);
        if is_appimage_variant_suffix_rs(&suffix){push_base(&lowered[..index]);}
    }
    let without_digits=exact.trim_end_matches(|ch:char|ch.is_ascii_digit());
    if without_digits.len()!=exact.len(){push_base(without_digits);}
    if let Some(index)=exact.rfind("asm"){
        let digits=&exact[index+3..];
        if !digits.is_empty()&&digits.chars().all(|ch|ch.is_ascii_digit()){push_base(&exact[..index]);}
    }
    aliases
}
fn appimage_standard_name_group_rs(name:&str,standard_names:&std::collections::HashMap<String,std::collections::HashSet<String>>)->Option<String>{
    for (index,alias) in appimage_name_aliases_rs(name).iter().enumerate(){
        let Some(groups)=standard_names.get(alias) else{continue};
        if groups.len()==1{return groups.iter().next().cloned()}
        // An exact but ambiguous standard name should not be guessed into one
        // of two unrelated catalog entries.
        if index==0{return None}
    }
    None
}
fn standard_name_group_rs(name:&str,standard_names:&std::collections::HashMap<String,std::collections::HashSet<String>>)->Option<String>{
    let normalized=canonical_app_name_rs(name);
    if normalized.is_empty(){return None}
    let groups=standard_names.get(&normalized)?;
    if groups.len()==1{groups.iter().next().cloned()}else{None}
}
// Raw nixpkgs attributes carry no API identity. They may still join an
// existing catalog entry when the attribute/pname names the same application,
// the provider metadata proves the same vendor identity, and the package
// description describes the same product. Any one signal alone is too weak:
// ``ark``/``boxes``/``element`` all collide with unrelated CLI packages.
const METADATA_GENERIC_WORDS:&[&str]=&[
    "about","after","against","allows","also","always","another","application","applications","authors",
    "available","based","because","before","being","better","between","built","collection","command",
    "community","company","complete","computer","computers","contributors","corporation","create","cross",
    "desktop","developers","development","different","directly","display","download","editing","editor",
    "efficient","entire","environment","every","experience","feature","features","files","first","focus",
    "focused","foundation","free","from","fully","function","functions","graphical","great","gmbh","have",
    "includes","including","information","interface","language","laptop","latest","lightweight","linux",
    "little","maintainers","makes","management","manager","many","modern","more","most","multiple","network",
    "official","online","open","operating","other","package","performance","platform","powerful","previously",
    "professional","program","programs","project","provide","provides","providing","quality","quick","really",
    "release","released","releases","remember","running","runtime","screen","service","services","several",
    "simple","simplest","small","software","solution","source","special","stable","standard","studio","support",
    "supported","supports","system","systems","their","there","these","things","through","tools","using","users",
    "various","version","versions","very","video","well","which","while","windows","without","working","written","your","yours",
];
const GROUP_IDENTITY_GENERIC_WORDS:&[&str]=&[
    "the","and","team","project","software","community","foundation","contributors","developers",
    "authors","maintainers","llc","ltd","inc","gmbh","corporation","company","nixpkgs",
];
fn push_identity_token_rs(tokens:&mut std::collections::HashSet<String>,value:&str){
    let token=normalized_app_name_rs(value);
    if token.chars().count()<3{return}
    if GROUP_IDENTITY_GENERIC_WORDS.contains(&token.as_str()){return}
    tokens.insert(token);
}
fn entry_vendor_tokens_rs(item:&serde_json::Map<String,Value>)->std::collections::HashSet<String>{
    // The reverse-DNS vendor segment and the developer name describe who makes
    // the application. Store names are deliberately excluded: they are shared
    // by CLI tools and applications alike (``ark``, ``bar``). ``Nixpkgs`` is
    // the packager, not the application vendor.
    let source=item.get("source").and_then(Value::as_str).unwrap_or("native");
    let mut tokens=std::collections::HashSet::new();
    if let Some(developer)=item.get("developer").and_then(Value::as_str){
        let developer=developer.trim();
        if !(source=="nix"&&developer=="Nixpkgs"){
            for word in developer.split(|character:char|!character.is_alphanumeric()){push_identity_token_rs(&mut tokens,word);}
        }
    }
    if matches!(source,"appimage"|"nix"){return tokens}
    let Some(id)=item.get("id").and_then(Value::as_str).map(str::trim).filter(|value|!value.is_empty()) else{return tokens};
    let id=id.strip_suffix(".desktop").unwrap_or(id);
    let parts:Vec<&str>=id.split('.').filter(|part|!part.is_empty()).collect();
    if parts.len()>=2{push_identity_token_rs(&mut tokens,parts[parts.len()-2]);}
    tokens
}
fn entry_identity_tokens_rs(item:&serde_json::Map<String,Value>)->std::collections::HashSet<String>{
    let source=item.get("source").and_then(Value::as_str).unwrap_or("native");
    let mut tokens=entry_vendor_tokens_rs(item);
    if source=="nix"{
        // The nixpkgs attribute/pname is the package's catalog identity. It is
        // an alias, not a vendor mark, so it only proves identity when it
        // matches another entry's vendor or package-name alias.
        for key in ["nix_name","nix_pname"]{
            if let Some(value)=item.get(key).and_then(Value::as_str){push_identity_token_rs(&mut tokens,value);}
        }
        return tokens;
    }
    let Some(id)=item.get("id").and_then(Value::as_str).map(str::trim).filter(|value|!value.is_empty()) else{return tokens};
    let id=id.strip_suffix(".desktop").unwrap_or(id);
    let parts:Vec<&str>=id.split('.').filter(|part|!part.is_empty()).collect();
    let (Some(segment),Some(name))=(parts.last(),item.get("name").and_then(Value::as_str)) else{return tokens};
    // A package id often keeps the full application name while the display
    // name is shortened ("Faugus" vs ``faugus-launcher``). Expose that longer
    // form as a matching alias, but never when it merely repeats the display
    // name: unrelated same-name apps (CutWire Prism, Prism Launcher) would
    // otherwise share an identity token.
    if normalized_app_name_rs(segment)!=normalized_app_name_rs(name){push_identity_token_rs(&mut tokens,segment);}
    tokens
}
fn add_group_identity_tokens_rs(tokens:&mut std::collections::HashMap<String,std::collections::HashSet<String>>,group:&str,item:&serde_json::Map<String,Value>){
    for token in entry_vendor_tokens_rs(item){tokens.entry(group.to_string()).or_default().insert(token);}
}
fn application_summary_matches_rs(left:&serde_json::Map<String,Value>,right:&serde_json::Map<String,Value>,group:&str)->bool{
    let right_summary=component_summary_words_rs(right);
    component_summary_words_rs(left).iter().any(|word|word.as_str()!=group&&right_summary.contains(word))
}
fn application_description_matches_rs(left:&serde_json::Map<String,Value>,right:&serde_json::Map<String,Value>,group:&str)->bool{
    if application_summary_matches_rs(left,right,group){return true}
    let right_description=component_description_words_rs(right);
    component_description_words_rs(left).iter().filter(|word|word.as_str()!=group&&right_description.contains(*word)).count()>=2
}
fn same_application_entry_rs(left:&serde_json::Map<String,Value>,right:&serde_json::Map<String,Value>,group:&str)->bool{
    let (left_id,left_name)=component_identity_rs(left);
    let (right_id,right_name)=component_identity_rs(right);
    if !left_id.is_empty()&&left_id==right_id{return true}
    // Two components from the same selectable source are distinct catalog
    // identities even when they share a name: a source option can only install
    // one of them.
    if !left_id.is_empty()&&!right_id.is_empty()&&source_option_key_rs(left)==source_option_key_rs(right){return false}
    let left_vendors=entry_vendor_tokens_rs(left);
    let right_vendors=entry_vendor_tokens_rs(right);
    let vendor_match=left_vendors.iter().any(|token|right_vendors.contains(token));
    let vendor_conflict=!left_vendors.is_empty()&&!right_vendors.is_empty()&&!vendor_match;
    let left_tokens=entry_identity_tokens_rs(left);
    let right_tokens=entry_identity_tokens_rs(right);
    let identity_match=left_tokens.iter().any(|token|right_tokens.contains(token));
    let description_match=application_description_matches_rs(left,right,group);
    if vendor_conflict{
        // Different vendors usually mean different products. Long descriptions
        // of same-domain apps share too much incidental vocabulary ("audio",
        // "real time", "control"), so a conflicting vendor needs a matching
        // summary — a short product statement — before coalescing (a Snap
        // publisher such as Canonical versus the upstream developer).
        return application_summary_matches_rs(left,right,group);
    }
    let exact_name=!left_name.is_empty()&&normalized_app_name_rs(&left_name)==normalized_app_name_rs(&right_name);
    let raw_nix=item_is_raw_nix(left)||item_is_raw_nix(right);
    if raw_nix&&!identity_match&&!description_match{return false}
    identity_match||description_match||exact_name
}
fn item_is_raw_nix(item:&serde_json::Map<String,Value>)->bool{
    item.get("source").and_then(Value::as_str)==Some("nix")
        &&item.get("nix_api_name").and_then(Value::as_str).map(str::trim).filter(|value|!value.is_empty()).is_none()
}
fn split_application_clusters_rs(entries:Vec<serde_json::Map<String,Value>>,group:&str)->Vec<Vec<serde_json::Map<String,Value>>>{
    // Connected components, not complete linkage: a legitimate app can carry
    // source-specific vendor labels (a Snap publisher such as Canonical versus
    // the upstream developer), so two entries must still coalesce when a third
    // source proves both describe the same product. Unrelated same-name apps
    // stay in separate components because no evidence links them.
    let mut parent:Vec<usize>=(0..entries.len()).collect();
    fn root(parent:&mut [usize],mut index:usize)->usize{
        while parent[index]!=index{
            parent[index]=parent[parent[index]];
            index=parent[index];
        }
        index
    }
    for left in 0..entries.len(){
        for right in (left+1)..entries.len(){
            if !same_application_entry_rs(&entries[left],&entries[right],group){continue}
            let left_root=root(&mut parent,left);
            let right_root=root(&mut parent,right);
            if left_root!=right_root{parent[right_root]=left_root;}
        }
    }
    let mut clusters:Vec<Vec<serde_json::Map<String,Value>>>=Vec::new();
    let mut indexes=std::collections::HashMap::<usize,usize>::new();
    for (index,entry) in entries.into_iter().enumerate(){
        let cluster=root(&mut parent,index);
        let slot=*indexes.entry(cluster).or_insert_with(||{clusters.push(Vec::new());clusters.len()-1});
        clusters[slot].push(entry);
    }
    clusters
}
fn raw_nix_identity_matches_rs(alias:&str,group:&str,tokens:&std::collections::HashMap<String,std::collections::HashSet<String>>)->bool{
    let alias=normalized_app_name_rs(alias);
    if alias.is_empty(){return false}
    let Some(values)=tokens.get(group) else{return false};
    values.iter().any(|token|token==&alias||(token.chars().count()>=4&&alias.starts_with(token)&&alias.len()>token.len()))
}
fn collect_metadata_words_rs(text:&str,words:&mut std::collections::HashSet<String>){
    for word in text.split(|character:char|!character.is_alphanumeric()){
        let word=word.to_lowercase();
        if word.chars().count()<4||METADATA_GENERIC_WORDS.contains(&word.as_str()){continue}
        words.insert(word);
    }
}
fn component_summary_words_rs(item:&serde_json::Map<String,Value>)->std::collections::HashSet<String>{
    let mut words=std::collections::HashSet::new();
    if let Some(summary)=item.get("summary").and_then(Value::as_str){collect_metadata_words_rs(summary,&mut words);}
    words
}
fn component_description_words_rs(item:&serde_json::Map<String,Value>)->std::collections::HashSet<String>{
    let mut words=std::collections::HashSet::new();
    let empty=Value::Null;
    collect_metadata_words_rs(&flatten_blocks(item.get("description_blocks").unwrap_or(&empty)),&mut words);
    words
}
fn raw_nix_description_matches_rs(
    item:&serde_json::Map<String,Value>,
    group:&str,
    summary_words:Option<&std::collections::HashSet<String>>,
    description_words:Option<&std::collections::HashSet<String>>,
)->bool{
    // The application's own name appears in both descriptions but proves
    // nothing about the product (Todoist CLI vs the Todoist desktop app).
    let summary_shared=component_summary_words_rs(item).iter().filter(|word|word.as_str()!=group&&summary_words.map(|words|words.contains(*word)).unwrap_or(false)).count();
    if summary_shared>0{return true}
    // Long descriptions are paraphrase-prone; require two shared content words
    // so related-but-different projects (Solarus engine vs its launcher) or a
    // single generic category word cannot attach the wrong package.
    component_description_words_rs(item).iter().filter(|word|word.as_str()!=group&&description_words.map(|words|words.contains(*word)).unwrap_or(false)).count()>=2
}
fn raw_nix_group_rs(
    item:&serde_json::Map<String,Value>,
    display_names:&std::collections::HashSet<String>,
    exact_display_names:&std::collections::HashSet<String>,
    standard_names:&std::collections::HashMap<String,std::collections::HashSet<String>>,
    identity_tokens:&std::collections::HashMap<String,std::collections::HashSet<String>>,
    summary_words:&std::collections::HashMap<String,std::collections::HashSet<String>>,
    description_words:&std::collections::HashMap<String,std::collections::HashSet<String>>,
)->Option<String>{
    let attr=item.get("nix_name").and_then(Value::as_str).unwrap_or("");
    let pname=item.get("nix_pname").and_then(Value::as_str).unwrap_or("");
    for alias in [attr,pname]{
        if alias.is_empty(){continue}
        // Require an actual display-name match. Final-id-segment aliases are
        // useful for API-identified packages, but on raw attributes they would
        // attach unrelated CLI tools to apps such as Delta Chat. The exact form
        // also keeps a package from matching a differently-qualified app
        // ("Solarus" engine vs "Solarus Launcher").
        if !display_names.contains(&canonical_app_name_rs(alias)){continue}
        if !exact_display_names.contains(&normalized_app_name_rs(alias)){continue}
        let Some(group)=standard_name_group_rs(alias,standard_names) else{continue};
        if !raw_nix_identity_matches_rs(alias,&group,identity_tokens){continue}
        if !raw_nix_description_matches_rs(item,&group,summary_words.get(&group),description_words.get(&group)){continue}
        return Some(group);
    }
    None
}
fn metadata_string_field_rs<'a>(item:&'a serde_json::Map<String,Value>,key:&str)->&'a str{
    item.get(key).and_then(Value::as_str).map(str::trim).unwrap_or("")
}
fn metadata_text_len_rs(value:&str)->usize{value.chars().count()}
fn metadata_array_len_rs(item:&serde_json::Map<String,Value>,key:&str)->usize{
    item.get(key).and_then(Value::as_array).map(Vec::len).unwrap_or(0)
}
fn metadata_description_rs(item:&serde_json::Map<String,Value>)->String{
    let empty=Value::Null;
    flatten_blocks(item.get("description_blocks").unwrap_or(&empty))
}
fn source_metadata_score_rs(item:&serde_json::Map<String,Value>)->u32{
    let mut score=0u32;
    let summary=metadata_string_field_rs(item,"summary");
    if !summary.is_empty(){score+=2+(metadata_text_len_rs(summary)/24).min(8) as u32;}
    let description=metadata_description_rs(item);
    if !description.is_empty(){score+=6+(metadata_text_len_rs(&description)/120).min(10) as u32;}
    score+=(metadata_array_len_rs(item,"screenshots").min(4)*2) as u32;
    let developer=metadata_string_field_rs(item,"developer");
    if !developer.is_empty()&&developer!="Nixpkgs"{score+=4;}
    let homepage=metadata_string_field_rs(item,"homepage");
    if !homepage.is_empty()&&!homepage.contains("search.nixos.org"){score+=3;}
    if !metadata_string_field_rs(item,"license").is_empty(){score+=2;}
    if metadata_array_len_rs(item,"categories")>0{score+=2;}
    if !metadata_string_field_rs(item,"donation").is_empty(){score+=1;}
    if item.get("review_rating").map(|value|!value.is_null()).unwrap_or(false){score+=1;}
    score+=source_icon_rank_rs(metadata_string_field_rs(item,"icon")) as u32;
    score
}
fn metadata_source_rank_rs(item:&serde_json::Map<String,Value>)->u8{
    match item.get("source").and_then(Value::as_str).unwrap_or("native"){
        "flatpak"=>5,"native"=>4,"snap"=>3,"appimage"=>2,"nix"=>1,"homebrew"=>0,_=>0
    }
}
fn metadata_similarity_rs(left:&serde_json::Map<String,Value>,right:&serde_json::Map<String,Value>,group:&str)->(usize,usize){
    let left_summary=component_summary_words_rs(left);
    let right_summary=component_summary_words_rs(right);
    let left_description=component_description_words_rs(left);
    let right_description=component_description_words_rs(right);
    let summary_shared=left_summary.iter().filter(|word|word.as_str()!=group&&right_summary.contains(*word)).count();
    let description_shared=left_description.iter().filter(|word|word.as_str()!=group&&right_description.contains(*word)).count();
    (summary_shared,description_shared)
}
fn same_source_entry_rs(left:&serde_json::Map<String,Value>,right:&serde_json::Map<String,Value>)->bool{
    left.get("id").and_then(Value::as_str)==right.get("id").and_then(Value::as_str)
        &&source_option_key_rs(left)==source_option_key_rs(right)
}
struct MetadataCandidate<'a>{
    item:&'a serde_json::Map<String,Value>,
    score:u32,
    source:u8,
    verified:bool,
    summary_shared:usize,
    description_shared:usize,
}
fn metadata_candidates_rs<'a>(selected:&serde_json::Map<String,Value>,group:&'a [serde_json::Map<String,Value>])->Vec<MetadataCandidate<'a>>{
    let group_name=canonical_app_name_rs(metadata_string_field_rs(selected,"name"));
    let mut candidates=Vec::new();
    for item in group{
        if same_source_entry_rs(selected,item){continue}
        let (summary_shared,description_shared)=metadata_similarity_rs(selected,item,&group_name);
        candidates.push(MetadataCandidate{
            item,
            score:source_metadata_score_rs(item),
            source:metadata_source_rank_rs(item),
            verified:item.get("verified").and_then(Value::as_bool).unwrap_or(false),
            summary_shared,
            description_shared,
        });
    }
    let has_similar=candidates.iter().any(|candidate|candidate.summary_shared>0||candidate.description_shared>0);
    if has_similar{
        candidates.retain(|candidate|candidate.summary_shared>0||candidate.description_shared>0);
    }else if !component_summary_words_rs(selected).is_empty()||!component_description_words_rs(selected).is_empty(){
        // Same-name groups can contain unrelated applications (a "Vice" air
        // traffic simulator and the VICE Commodore emulator). Never borrow
        // metadata or icons from a provider whose description does not
        // describe the selected source; a brand-name match alone is not
        // evidence.
        candidates.clear();
    }
    candidates
}
fn best_metadata_source_rs<'a>(selected:&serde_json::Map<String,Value>,group:&'a [serde_json::Map<String,Value>])->Option<&'a serde_json::Map<String,Value>>{
    let mut best:Option<MetadataCandidate<'a>>=None;
    for candidate in metadata_candidates_rs(selected,group){
        let replace=match &best{None=>true,Some(current)=>(candidate.score,candidate.source,candidate.verified)>(current.score,current.source,current.verified)};
        if replace{best=Some(candidate);}
    }
    best.map(|candidate|candidate.item)
}
fn best_metadata_icon_rs(selected:&serde_json::Map<String,Value>,group:&[serde_json::Map<String,Value>])->Option<String>{
    let selected_rank=source_icon_rank_rs(metadata_string_field_rs(selected,"icon"));
    let mut best:Option<(u8,u8,u32,&str)>=None;
    for candidate in metadata_candidates_rs(selected,group){
        let icon=metadata_string_field_rs(candidate.item,"icon");
        let rank=source_icon_rank_rs(icon);
        if rank==0{continue}
        let replace=match best{None=>true,Some((best_rank,best_source,best_score,_))=>(rank,candidate.source,candidate.score)>(best_rank,best_source,best_score)};
        if replace{best=Some((rank,candidate.source,candidate.score,icon));}
    }
    best.filter(|(rank,_,_,_)|*rank>selected_rank).map(|(_,_,_,icon)|icon.to_string())
}
fn copy_source_metadata_rs(selected:&mut serde_json::Map<String,Value>,donor:&serde_json::Map<String,Value>){
    let from_nix=selected.get("source").and_then(Value::as_str)==Some("nix");
    let copy_string=|selected:&mut serde_json::Map<String,Value>,field:&str,localized:&str|{
        if let Some(value)=donor.get(field){selected.insert(field.to_string(),value.clone());if !localized.is_empty(){if let Some(value)=donor.get(localized){selected.insert(localized.to_string(),value.clone());}}}
    };
    let donor_name=metadata_string_field_rs(donor,"name");
    if !donor_name.is_empty()&&(from_nix||metadata_string_field_rs(selected,"name").is_empty()){copy_string(selected,"name","localized_names");}
    let donor_summary=metadata_string_field_rs(donor,"summary");
    let selected_summary_len=metadata_text_len_rs(metadata_string_field_rs(selected,"summary"));
    if !donor_summary.is_empty()&&(from_nix||selected_summary_len==0||metadata_text_len_rs(donor_summary)>selected_summary_len){copy_string(selected,"summary","localized_summaries");}
    let donor_description=metadata_description_rs(donor);
    let selected_description_len=metadata_text_len_rs(&metadata_description_rs(selected));
    if !donor_description.is_empty()&&(from_nix||selected_description_len==0||metadata_text_len_rs(&donor_description)>selected_description_len){
        copy_string(selected,"description_blocks","localized_descriptions");
        // The blocks now come from the donor, so render them with the donor's
        // format instead of the selected source's native description format.
        let format=if donor.get("source").and_then(Value::as_str)==Some("snap"){"markdown"}else{"appstream"};
        selected.insert("metadata_description_format".into(),Value::String(format.into()));
    }
    if metadata_array_len_rs(donor,"screenshots")>metadata_array_len_rs(selected,"screenshots"){copy_string(selected,"screenshots","");}
    let donor_developer=metadata_string_field_rs(donor,"developer");
    let selected_developer=metadata_string_field_rs(selected,"developer");
    let donor_is_nixpkgs=donor_developer=="Nixpkgs";
    if !donor_developer.is_empty()&&!(donor_is_nixpkgs&&!from_nix)&&(from_nix||selected_developer.is_empty()||selected_developer=="Nixpkgs"||metadata_text_len_rs(donor_developer)>metadata_text_len_rs(selected_developer)){copy_string(selected,"developer","localized_developers");}
    let donor_homepage=metadata_string_field_rs(donor,"homepage");
    let selected_homepage=metadata_string_field_rs(selected,"homepage");
    if !donor_homepage.is_empty()&&(from_nix||selected_homepage.is_empty()||selected_homepage.contains("search.nixos.org")){copy_string(selected,"homepage","");}
    if !metadata_string_field_rs(donor,"license").is_empty()&&(from_nix||metadata_string_field_rs(selected,"license").is_empty()){copy_string(selected,"license","");}
    if metadata_array_len_rs(donor,"categories")>0&&(from_nix||metadata_array_len_rs(selected,"categories")==0){copy_string(selected,"categories","");}
    if !metadata_string_field_rs(donor,"donation").is_empty()&&(from_nix||metadata_string_field_rs(selected,"donation").is_empty()){copy_string(selected,"donation","");}
    if selected.get("review_rating").map(|value|value.is_null()).unwrap_or(true){
        for field in ["review_rating","review_count"]{
            if donor.get(field).map(|value|!value.is_null()).unwrap_or(false){copy_string(selected,field,"");}
        }
    }
}
fn source_metadata_enriched_rs(selected:&serde_json::Map<String,Value>,group:&[serde_json::Map<String,Value>])->serde_json::Map<String,Value>{
    let mut enriched=selected.clone();
    if let Some(donor)=best_metadata_source_rs(selected,group){copy_source_metadata_rs(&mut enriched,donor);}
    enriched
}
fn standard_name_aliases_rs(item:&serde_json::Map<String,Value>)->Vec<String>{
    // AppStream display names are often shortened while the reverse-DNS id
    // keeps the full application name (the Flathub id
    // ``io.github.Faugus.faugus-launcher`` shows as "Faugus", while Nix calls
    // the same app "Faugus Launcher"). Expose the final id segment as an
    // additional matching alias so those entries still coalesce. Generic
    // suffixes and very short ids are ignored so a shared namespace cannot
    // create accidental merges.
    let Some(id)=item.get("id").and_then(Value::as_str).map(str::trim).filter(|value|!value.is_empty()) else{return Vec::new()};
    let id=id.strip_suffix(".desktop").unwrap_or(id);
    let segment=id.rsplit('.').next().unwrap_or(id);
    let normalized=canonical_app_name_rs(segment);
    if normalized.chars().count()<4{return Vec::new()}
    if matches!(normalized.as_str(),"desktop"|"app"|"application"|"client"|"launcher"|"manager"|"server"){return Vec::new()}
    vec![normalized]
}
fn is_verified_flatpak_rs(item:&serde_json::Map<String,Value>)->bool{
    item.get("source").and_then(Value::as_str).unwrap_or("native")=="flatpak" && item.get("verified").and_then(Value::as_bool).unwrap_or(false)
}
fn locked_system_flatpak_rs(group:&[serde_json::Map<String,Value>],locks:&std::collections::HashSet<String>)->Option<serde_json::Map<String,Value>>{
    let mut c:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str)==Some("flatpak")&&m.get("flatpak_scope").and_then(Value::as_str)==Some("system")&&locks.contains(&normalize_id(m.get("id").and_then(Value::as_str).unwrap_or("")))).cloned().collect();
    c.sort_by_key(|m|{let i=m.get("flatpak_installation").and_then(Value::as_str).unwrap_or("");(i!="default",i.to_string())});
    c.into_iter().next().map(|mut m|{m.remove("_source_alternatives");m.remove("_source_recommended");m})
}
fn expand_source_group_rs(group:&[serde_json::Map<String,Value>])->Vec<serde_json::Map<String,Value>>{
    let mut out=Vec::new();let mut seen=std::collections::HashSet::new();
    for item in group { let mut candidates=vec![item.clone()]; if let Some(a)=item.get("_source_alternatives").and_then(Value::as_array){candidates.extend(a.iter().filter_map(Value::as_object).cloned());}
        for mut c in candidates {let id=c.get("id").and_then(Value::as_str).unwrap_or("").to_string();if !seen.insert((source_option_key_rs(&c),id)){continue}c.remove("_source_alternatives");c.remove("_source_recommended");out.push(c)} }
    out
}
fn source_icon_rank_rs(value:&str)->u8{
    let value=value.trim();
    if value.is_empty()||value=="application-x-executable"{return 0}
    if matches!(value,"nix.svg"|"brewpkg.webp"){return 1}
    if value.starts_with("https://")||value.starts_with("http://")||value.starts_with("/v2/"){return 3}
    if value.starts_with('/'){return if std::path::Path::new(value).is_file(){3}else{0}}
    if value.ends_with(".png")||value.ends_with(".svg")||value.ends_with(".webp")||value.ends_with(".jxl"){return 2}
    0
}
fn source_key_collisions_rs(group:&[serde_json::Map<String,Value>],include_nix:bool)->std::collections::HashSet<String>{
    let mut ids=std::collections::HashMap::<String,std::collections::HashSet<String>>::new();
    for item in group{
        if !include_nix&&item.get("source").and_then(Value::as_str)==Some("nix"){continue}
        let Some(id)=item.get("id").and_then(Value::as_str).map(str::trim).filter(|value|!value.is_empty()) else{continue};
        ids.entry(source_option_key_rs(item)).or_default().insert(id.to_string());
    }
    ids.into_iter().filter(|(_,values)|values.len()>1).map(|(key,_)|key).collect()
}
fn with_source_options_rs(selected:&serde_json::Map<String,Value>,group:&[serde_json::Map<String,Value>])->serde_json::Map<String,Value>{
    let flat:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str)==Some("flatpak")).collect();
    let native:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str).unwrap_or("native")=="native").collect();
    let snap:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str)==Some("snap")).collect();
    let appimage:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str)==Some("appimage")).collect();
    let nix:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str)==Some("nix")).collect();
    // Verification affects which source may be chosen by the default policy, not
    // which valid sources the app page is allowed to expose. Keep every source in
    // the selector even when the currently selected Flatpak is verified.
    let mut candidates:Vec<&serde_json::Map<String,Value>>=native.into_iter().chain(flat).chain(snap).chain(appimage).chain(nix).collect();
    // A by-name group can contain two unrelated applications that share a
    // display name and a source key (two "Vice" Flatpaks, for example). Keep
    // only the selected identity and providers whose metadata describes it, so
    // the source selector can never install the wrong same-name app.
    if !source_key_collisions_rs(group,true).is_empty(){
        let mut allowed=std::collections::HashSet::<String>::new();
        if let Some(id)=selected.get("id").and_then(Value::as_str).map(str::trim).filter(|value|!value.is_empty()){allowed.insert(id.to_string());}
        for candidate in metadata_candidates_rs(selected,group){
            if let Some(id)=candidate.item.get("id").and_then(Value::as_str).map(str::trim).filter(|value|!value.is_empty()){allowed.insert(id.to_string());}
        }
        candidates.retain(|item|item.get("id").and_then(Value::as_str).map(|id|allowed.contains(id)).unwrap_or(false));
    }
    let mut seen=std::collections::HashSet::new();candidates.retain(|m|seen.insert(source_option_key_rs(m)));if candidates.len()<2{return selected.clone()}
    let sk=source_option_key_rs(selected);
    // Descriptive metadata is application-level, not source-level. Every
    // selectable source borrows it (and a usable icon) from the richest
    // similar provider in the group, while install identity (id, packages,
    // source, version) stays with the chosen source.
    let alts:Vec<Value>=candidates.into_iter().filter(|m|source_option_key_rs(m)!=sk).map(|m|{
        let mut enriched=source_metadata_enriched_rs(m,group);
        if let Some(icon)=best_metadata_icon_rs(m,group){enriched.insert("icon".into(),Value::String(icon));}
        Value::Object(enriched)
    }).collect();
    let mut r=source_metadata_enriched_rs(selected,group);
    if let Some(icon)=best_metadata_icon_rs(selected,group){r.insert("icon".into(),Value::String(icon));}
    if !alts.is_empty(){r.insert("_source_alternatives".into(),Value::Array(alts));r.insert("_source_recommended".into(),Value::String(sk));}r
}
fn group_prefers_dev_native_rs(group:&[serde_json::Map<String,Value>],paths:&[String],cfg:&Value,steamos:bool,suse:bool)->bool{
    !steamos&&group.iter().any(|m|resolve_component_category_rs(m,paths,cfg).is_some_and(|c|match c.rsplit('/').next(){
        // openSUSE native browser packages are managed by the distro update
        // stack; prefer their Flatpak/Snap sources there instead.
        Some("browsers")=>!suse,
        Some("devs"|"ides"|"txt")=>true,
        _=>false,
    }))
}
fn group_category_rs(group:&[serde_json::Map<String,Value>],paths:&[String],cfg:&Value)->Option<String>{
    group.iter().find_map(|m|resolve_component_category_rs(m,paths,cfg))
}
fn gregos_category_prefers_nix_rs(category:&str)->bool{
    if category.split('/').any(|part|matches!(part,"game"|"games")){return true}
    // The GregOS package-manager preference covers the Developers root
    // category plus the IDEs, Text Editors and Browsers leaves. Deeper
    // development subcategories (tools, AI agents) keep the normal policy.
    matches!(category.rsplit('/').next(),Some("devs"|"ides"|"txt"|"browsers"))
}
fn preference_value_rs(v:&Value,host_os:&std::collections::HashSet<String>)->Option<String>{
    if let Some(s)=v.as_str(){return matches!(s,"native"|"flatpak"|"appimage").then(||s.to_string())}
    if let Some(m)=v.as_object(){
        for(k,v)in m{if k!="all"&&host_os.contains(&k.to_lowercase()){if let Some(s)=v.as_str(){if matches!(s,"native"|"flatpak"|"appimage"){return Some(s.into())}}}}
        return m.get("all").and_then(Value::as_str).filter(|s|matches!(*s,"native"|"flatpak"|"appimage")).map(str::to_string)
    }
    None
}
fn explicit_preference_rs(item:&serde_json::Map<String,Value>,prefs:&Value,host_os:&std::collections::HashSet<String>)->Option<String>{
    let apps=prefs.as_object()?.get("apps")?.as_object()?;
    let policy_keys=component_policy_keys_rs(item);
    let v=apps.iter().find_map(|(key,value)| {
        let key_id=normalize_id(key);
        let key_plain=key.trim().to_lowercase();
        policy_keys.iter().any(|candidate| candidate==&key_id || candidate==&key_plain).then_some(value)
    })?;
    preference_value_rs(v,host_os)
}
fn explicit_group_preference_rs(group:&[serde_json::Map<String,Value>],prefs:&Value,host_os:&std::collections::HashSet<String>)->Option<String>{
    group.iter().find_map(|item|explicit_preference_rs(item,prefs,host_os))
}
fn preference_rs(item:&serde_json::Map<String,Value>,prefs:&Value,host_os:&std::collections::HashSet<String>)->String{
    explicit_preference_rs(item,prefs,host_os).unwrap_or_else(||prefs.as_object().and_then(|o|o.get("default")).and_then(Value::as_str).filter(|s|matches!(*s,"native"|"flatpak"|"appimage")).unwrap_or("flatpak").to_string())
}
fn collapse_source_groups_rs(components:Vec<serde_json::Map<String,Value>>,paths:&[String],cfg:&Value,prefs:&Value,locks:&std::collections::HashSet<String>,host_os:&std::collections::HashSet<String>,prefer_native_host:bool,prefer_nix:bool,prefer_nix_gregos:bool,steamos:bool,suse:bool,by_name_pass:bool)->Vec<serde_json::Map<String,Value>>{
    let mut groups:std::collections::BTreeMap<String,Vec<serde_json::Map<String,Value>>>=std::collections::BTreeMap::new();let mut pass=Vec::new();
    let mut standard_names=std::collections::HashMap::<String,std::collections::HashSet<String>>::new();
    let mut display_names=std::collections::HashSet::<String>::new();
    let mut exact_display_names=std::collections::HashSet::<String>::new();
    let mut identity_tokens=std::collections::HashMap::<String,std::collections::HashSet<String>>::new();
    let mut summary_words=std::collections::HashMap::<String,std::collections::HashSet<String>>::new();
    let mut description_words=std::collections::HashMap::<String,std::collections::HashSet<String>>::new();
    if by_name_pass{
        let mut raw_nix_names=std::collections::HashSet::<String>::new();
        for item in &components{
            if item.get("source").and_then(Value::as_str)!=Some("nix"){continue}
            if item.get("nix_api_name").and_then(Value::as_str).map(str::trim).filter(|value|!value.is_empty()).is_some(){continue}
            for alias in [item.get("nix_name").and_then(Value::as_str).unwrap_or(""),item.get("nix_pname").and_then(Value::as_str).unwrap_or("")]{
                let normalized=canonical_app_name_rs(alias);
                if !normalized.is_empty(){raw_nix_names.insert(normalized);}
            }
        }
        for item in &components{
            let source=item.get("source").and_then(Value::as_str).unwrap_or("native");
            if matches!(source,"appimage"|"homebrew"|"nix"){continue}
            let name=item.get("name").and_then(Value::as_str).unwrap_or("").trim();
            let normalized=canonical_app_name_rs(name);
            let group_name=if normalized.is_empty(){name.to_lowercase()}else{normalized.clone()};
            if !normalized.is_empty()&&!group_name.is_empty(){standard_names.entry(normalized.clone()).or_default().insert(group_name.clone());}
            if !group_name.is_empty(){
                display_names.insert(normalized.clone());
                let exact_name=normalized_app_name_rs(name);
                if !exact_name.is_empty(){exact_display_names.insert(exact_name);}
                add_group_identity_tokens_rs(&mut identity_tokens,&group_name,item);
                if raw_nix_names.contains(&normalized){
                    summary_words.entry(group_name.clone()).or_default().extend(component_summary_words_rs(item));
                    description_words.entry(group_name.clone()).or_default().extend(component_description_words_rs(item));
                }
                for alias in standard_name_aliases_rs(item){standard_names.entry(alias).or_default().insert(group_name.clone());}
            }
        }
    }
    for m in components {
        if m.get("source").and_then(Value::as_str)==Some("homebrew"){pass.push(m);continue}
        let source=m.get("source").and_then(Value::as_str).unwrap_or("native");
        let(id,name)=component_identity_rs(&m);
        let canonical_name=canonical_app_name_rs(&name);
        let key=if by_name_pass{
            if name.is_empty(){None}
            else if source=="appimage"{
                let canonical=m.get("name").and_then(Value::as_str).unwrap_or("");
                let matched=appimage_standard_name_group_rs(canonical,&standard_names);
                Some(matched.map(|group|format!("name:{group}")).unwrap_or_else(||{
                    format!("appimage:{}",if id.is_empty(){name.clone()}else{id.clone()})
                }))
            }else if source=="nix"{
                // API-identified GUI applications join their by-name group
                // directly. Raw attributes may join too when the attribute or
                // pname names the same application, the provider metadata
                // proves the same vendor identity, and the package description
                // describes the same product. That lets packages the API does
                // not index (Brave) merge while CLI/library collisions
                // (``ark``, ``boxes``, ``element``...) stay isolated.
                let api_name=m.get("nix_api_name").and_then(Value::as_str).unwrap_or("");
                if api_name.is_empty(){
                    if let Some(group)=raw_nix_group_rs(&m,&display_names,&exact_display_names,&standard_names,&identity_tokens,&summary_words,&description_words){
                        Some(format!("name:{group}"))
                    }else{
                        let attr=m.get("nix_name").and_then(Value::as_str).unwrap_or(name.as_str());
                        Some(format!("nix:{attr}"))
                    }
                }else{
                    let canonical=m.get("name").and_then(Value::as_str).unwrap_or("");
                    let attr=m.get("nix_name").and_then(Value::as_str).unwrap_or("");
                    let pname=m.get("nix_pname").and_then(Value::as_str).unwrap_or("");
                    let matched=standard_name_group_rs(canonical,&standard_names)
                        .or_else(||standard_name_group_rs(attr,&standard_names))
                        .or_else(||standard_name_group_rs(pname,&standard_names));
                    let fallback=if canonical_name.is_empty(){name.clone()}else{canonical_name.clone()};
                    Some(matched.map(|group|format!("name:{group}")).unwrap_or_else(||format!("name:{fallback}")))
                }
            }else{
                let canonical=if canonical_name.is_empty(){name.clone()}else{canonical_name.clone()};
                Some(format!("name:{canonical}"))
            }
        }else if !id.is_empty(){Some(format!("id:{id}"))}
        else if !name.is_empty(){Some(format!("name:{name}"))}
        else{None};
        if let Some(key)=key{groups.entry(key).or_default().push(m)}else{pass.push(m)}
    }
    // A canonical display name is not an application identity: several
    // unrelated apps can share one, and generic trailing descriptors
    // ("Prism Launcher" -> "Prism") widen the collision. A by-name group is
    // ambiguous only when a store source key itself carries several component
    // ids; such groups are split into application clusters using the same
    // vendor/description evidence rules as the raw Nix merge, so unrelated
    // same-name entries keep their own cards and source options.
    let groups=if by_name_pass{
        let mut split=std::collections::BTreeMap::new();
        for (key,raw) in groups{
            if let Some(group)=key.strip_prefix("name:"){
                // Same-name sources normally are the same application. A
                // store source key carrying two different component ids proves
                // the name collides inside one catalog (two Flathub apps called
                // "Prism"), so only then split the group by application
                // evidence and attach the remaining sources to the matching
                // identity. Nix keys are excluded: one nixpkgs pname can back
                // several package variants (yt-dlp / yt-dlp-light) that the
                // old grouping already treated as one app.
                if source_key_collisions_rs(&raw,false).is_empty(){split.insert(key.clone(),raw);continue}
                for (index,cluster) in split_application_clusters_rs(raw,group).into_iter().enumerate(){
                    let cluster_key=if index==0{key.clone()}else{format!("{key}#{index}")};
                    split.insert(cluster_key,cluster);
                }
            }else{split.insert(key,raw);}
        }
        split
    }else{groups};
    let mut out=pass;
    for (_,raw) in groups {let mut group=if by_name_pass{expand_source_group_rs(&raw)}else{raw};if let Some(l)=locked_system_flatpak_rs(&group,locks){out.push(l);continue}
        let mut flat:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str)==Some("flatpak")).cloned().collect();let natives:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str).unwrap_or("native")=="native").cloned().collect();let snaps:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str)==Some("snap")).cloned().collect();let appimages:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str)==Some("appimage")).cloned().collect();let mut nixes:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str)==Some("nix")).cloned().collect();
        // On NixOS the system scope is the native install; elsewhere user-scope
        // Home Manager is the least invasive default.
        nixes.sort_by_key(|m|{let scope=m.get("nix_scope").and_then(Value::as_str).unwrap_or("home-manager");let preferred=if prefer_nix{"system"}else{"home-manager"};(scope!=preferred,scope.to_string())});
        // User scope first, then the primary installation, and out of equal
        // scopes prefer the established default remote (flathub) over newly
        // added sources so the default selection stays stable when a hub like
        // FlatPark serves the same app.
        flat.sort_by_key(|m|(m.get("flatpak_scope").and_then(Value::as_str).unwrap_or("")!="user",m.get("flatpak_installation").and_then(Value::as_str).unwrap_or("").to_string(),m.get("flatpak_remote").and_then(Value::as_str).unwrap_or("flathub")!="flathub",m.get("flatpak_remote").and_then(Value::as_str).unwrap_or("").to_string()));group=natives.iter().cloned().chain(flat.iter().cloned()).chain(snaps.iter().cloned()).chain(appimages.iter().cloned()).chain(nixes.iter().cloned()).collect();
        if natives.is_empty()&&snaps.is_empty()&&appimages.is_empty()&&nixes.is_empty()&&flat.len()>1{out.push(with_source_options_rs(&flat[0],&group));continue}let sources:std::collections::HashSet<_>=group.iter().map(|m|m.get("source").and_then(Value::as_str).unwrap_or("native")).collect();if sources.len()<2{if !nixes.is_empty(){out.push(with_source_options_rs(&nixes[0],&group))}else if !appimages.is_empty(){out.extend(appimages)}else{out.extend(group)}continue}
        if let Some(pref)=explicit_group_preference_rs(&group,prefs,host_os){let mut selected:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str).unwrap_or("native")==pref).cloned().collect();if !selected.is_empty(){if matches!(pref.as_str(),"flatpak"|"appimage"){selected.truncate(1)}out.extend(selected.iter().map(|m|with_source_options_rs(m,&group)));continue}}
        // On NixOS and its derivatives Nixpkgs is the native package source.
        // Prefer it across every category, ahead of category-native policy and
        // Flatpak verification. Explicit per-app preferences above still win.
        if prefer_nix&&!nixes.is_empty(){
            if let Some(category)=group_category_rs(&group,paths,cfg){
                for nix in &mut nixes{nix.insert("nix_category".into(),Value::String(category.clone()));}
            }
            out.extend(nixes.iter().map(|m|with_source_options_rs(m,&group)));continue
        }
        // GregOS uses Nixpkgs as the host's user-level package source for
        // gaming plus the Developers and Text Editors categories. Prefer Nix
        // over category-native policy and verified Flatpak; explicit per-app
        // preferences above still win.
        if prefer_nix_gregos&&!nixes.is_empty(){
            if let Some(category)=group_category_rs(&group,paths,cfg){
                if gregos_category_prefers_nix_rs(&category){
                    // The selected source becomes a Nix component, whose own
                    // category hint is normally empty outside NixOS. Carry the
                    // group's category so the card stays where the app belongs
                    // instead of falling back to the standalone Nix category.
                    for nix in &mut nixes{nix.insert("nix_category".into(),Value::String(category.clone()));}
                    out.extend(nixes.iter().map(|m|with_source_options_rs(m,&group)));continue
                }
            }
        }
        // Whole-category native policy is a default-source decision and outranks
        // Flatpak verification. Explicit per-app preferences above still win, and
        // with_source_options_rs keeps Flatpak/Snap available for manual switching.
        let category_prefers_native=!natives.is_empty()&&group_prefers_dev_native_rs(&group,paths,cfg,steamos,suse);
        if category_prefers_native{out.extend(natives.iter().map(|m|with_source_options_rs(m,&group)));continue}
        if let Some(v)=flat.iter().find(|m|is_verified_flatpak_rs(m)){out.push(with_source_options_rs(v,&group));continue}if prefer_native_host&&!natives.is_empty(){out.extend(natives.iter().map(|m|with_source_options_rs(m,&group)));continue}
        let pref=preference_rs(&group[0],prefs,host_os);let mut selected:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str).unwrap_or("native")==pref).cloned().collect();if selected.is_empty(){selected=natives.clone()}if selected.is_empty(){selected=flat.clone()}if selected.is_empty(){selected=snaps.clone()}if selected.is_empty(){selected=appimages.clone()}if selected.first().and_then(|m|m.get("source")).and_then(Value::as_str)==Some("flatpak"){selected.truncate(1)}if selected.first().and_then(|m|m.get("source")).and_then(Value::as_str)==Some("snap"){selected.truncate(1)}out.extend(selected.iter().map(|m|with_source_options_rs(m,&group)));
    } out
}


#[derive(Clone, Debug)]
enum XmlPart { Text(String), Child(XmlNode) }

#[derive(Clone, Debug, Default)]
struct XmlNode {
    name: String,
    attrs: std::collections::HashMap<String, String>,
    parts: Vec<XmlPart>,
}

impl XmlNode {
    fn children_named<'a>(&'a self, name: &'a str) -> impl Iterator<Item=&'a XmlNode> {
        self.parts.iter().filter_map(move |p| match p { XmlPart::Child(n) if n.name == name => Some(n), _ => None })
    }
    fn children(&self) -> impl Iterator<Item=&XmlNode> { self.parts.iter().filter_map(|p| if let XmlPart::Child(n)=p {Some(n)} else {None}) }
    fn child(&self, name: &str) -> Option<&XmlNode> {
        self.parts.iter().find_map(|part| match part {
            XmlPart::Child(node) if node.name == name => Some(node),
            _ => None,
        })
    }
    fn text_trimmed(&self) -> String { self.all_text().trim().to_string() }
    fn direct_text(&self) -> String { self.parts.iter().filter_map(|p|if let XmlPart::Text(t)=p{Some(t.as_str())}else{None}).collect::<String>() }
    fn all_text(&self) -> String { let mut out=String::new(); for p in &self.parts { match p {XmlPart::Text(t)=>out.push_str(t),XmlPart::Child(n)=>out.push_str(&n.all_text())} } out }
}

fn xml_local_name(bytes: &[u8]) -> String {
    let s = String::from_utf8_lossy(bytes);
    s.rsplit(':').next().unwrap_or(&s).to_string()
}

fn parse_xml_tree(data: &[u8]) -> Result<XmlNode, String> {
    use quick_xml::events::Event;
    let mut reader = quick_xml::Reader::from_reader(data);
    reader.config_mut().trim_text(false);
    let mut stack: Vec<XmlNode> = Vec::new();
    let mut root: Option<XmlNode> = None;
    loop {
        match reader.read_event() {
            Ok(Event::Start(e)) => {
                let mut node = XmlNode { name: xml_local_name(e.name().as_ref()), ..Default::default() };
                for attr in e.attributes().with_checks(false).flatten() {
                    let key = xml_local_name(attr.key.as_ref());
                    if let Ok(value) = attr.decode_and_unescape_value(reader.decoder()) { node.attrs.insert(key, value.into_owned()); }
                }
                stack.push(node);
            }
            Ok(Event::Empty(e)) => {
                let mut node = XmlNode { name: xml_local_name(e.name().as_ref()), ..Default::default() };
                for attr in e.attributes().with_checks(false).flatten() {
                    let key = xml_local_name(attr.key.as_ref());
                    if let Ok(value) = attr.decode_and_unescape_value(reader.decoder()) { node.attrs.insert(key, value.into_owned()); }
                }
                if let Some(parent) = stack.last_mut() { parent.parts.push(XmlPart::Child(node)); } else { root = Some(node); }
            }
            Ok(Event::Text(e)) => { if let Some(node)=stack.last_mut() { if let Ok(t)=e.xml_content() { node.parts.push(XmlPart::Text(t.into_owned())); } } }
            Ok(Event::CData(e)) => { if let Some(node)=stack.last_mut() { if let Ok(t)=e.decode() { node.parts.push(XmlPart::Text(t.into_owned())); } } }
            Ok(Event::End(_)) => {
                if let Some(node)=stack.pop() {
                    if let Some(parent)=stack.last_mut() { parent.parts.push(XmlPart::Child(node)); } else { root=Some(node); }
                }
            }
            Ok(Event::Eof) => break,
            Err(e) => return Err(e.to_string()),
            _ => {}
        }
    }
    root.ok_or_else(|| "empty AppStream XML".to_string())
}

fn collapse_ws(value:&str)->String { value.split_whitespace().collect::<Vec<_>>().join(" ") }
fn stable_xml_repr(node:&XmlNode,out:&mut String){out.push('<');out.push_str(&node.name);let mut attrs:Vec<_>=node.attrs.iter().collect();attrs.sort_by(|a,b|a.0.cmp(b.0));for(k,v)in attrs{out.push(' ');out.push_str(k);out.push('=');out.push_str(v);}out.push('>');for p in &node.parts{match p{XmlPart::Text(t)=>out.push_str(t),XmlPart::Child(c)=>stable_xml_repr(c,out)}}out.push_str("</");out.push_str(&node.name);out.push('>');}
fn normalize_locale_code_rs(value:&str)->String {
    let base=value.trim().split('.').next().unwrap_or("").split('@').next().unwrap_or("").replace('_',"-");
    let parts:Vec<_>=base.split('-').filter(|p|!p.is_empty()).collect(); if parts.is_empty(){return String::new()}
    let mut out=vec![parts[0].to_lowercase()];
    if parts.len()>1 { out.push(if matches!(parts[1].len(),2|3){parts[1].to_uppercase()}else{parts[1].to_string()}); out.extend(parts[2..].iter().map(|s|s.to_string())); }
    out.join("-")
}
fn localized_text_values_rs(node:&XmlNode, tag:&str)->serde_json::Map<String,Value>{
    let mut out=serde_json::Map::new(); for child in node.children_named(tag){let value=collapse_ws(&child.all_text());if value.is_empty(){continue}let lang=normalize_locale_code_rs(child.attrs.get("lang").map(String::as_str).unwrap_or(""));out.insert(lang,Value::String(value));}out
}
fn default_localized_text_rs(node:&XmlNode,tag:&str)->String{let vals=localized_text_values_rs(node,tag);vals.get("").and_then(Value::as_str).or_else(||vals.values().find_map(Value::as_str)).unwrap_or("").to_string()}

fn append_span_rs(spans:&mut Vec<Value>, raw:&str, styles:&[String]) {
    let core=collapse_ws(raw); if core.is_empty(){return}
    let mut text=core; if raw.chars().next().is_some_and(char::is_whitespace){text.insert(0,' ')} if raw.chars().last().is_some_and(char::is_whitespace){text.push(' ')}
    if let Some(last)=spans.last_mut().and_then(Value::as_object_mut) {
        let same=last.get("styles").and_then(Value::as_array).is_some_and(|a|a.iter().filter_map(Value::as_str).eq(styles.iter().map(String::as_str)));
        if same {
            if let Some(s) = last.get("text").and_then(Value::as_str).map(str::to_owned) {
                last.insert("text".into(), Value::String(format!("{s}{text}")));
                return;
            }
        }
    }
    spans.push(serde_json::json!({"text":text,"styles":styles}));
}
fn inline_segments_rs(node:&XmlNode, inherited:&[String])->Vec<Value>{
    let mut spans=Vec::new();
    for part in &node.parts {
        match part {
            XmlPart::Text(t)=>append_span_rs(&mut spans,t,inherited),
            XmlPart::Child(child)=>{
                if child.name=="br" { if let Some(last)=spans.last_mut().and_then(Value::as_object_mut){if let Some(s)=last.get("text").and_then(Value::as_str){last.insert("text".into(),Value::String(format!("{}\n",s.trim_end())));}} continue; }
                let mut styles=inherited.to_vec(); match child.name.as_str(){"em"|"i"=>styles.push("italic".into()),"strong"|"b"=>styles.push("bold".into()),"code"=>styles.push("code".into()),_=>{}}
                for seg in inline_segments_rs(child,&styles){if let Some(m)=seg.as_object(){append_span_rs(&mut spans,m.get("text").and_then(Value::as_str).unwrap_or(""),&m.get("styles").and_then(Value::as_array).into_iter().flatten().filter_map(Value::as_str).map(str::to_string).collect::<Vec<_>>());}}
            }
        }
    }
    if let Some(first)=spans.first_mut().and_then(Value::as_object_mut){if let Some(t)=first.get("text").and_then(Value::as_str){first.insert("text".into(),Value::String(t.trim_start_matches(' ').to_string()));}}
    if let Some(last)=spans.last_mut().and_then(Value::as_object_mut){if let Some(t)=last.get("text").and_then(Value::as_str){last.insert("text".into(),Value::String(t.trim_end_matches(' ').to_string()));}}
    spans.into_iter().filter(|v|v.get("text").and_then(Value::as_str).is_some_and(|s|!s.is_empty())).collect()
}

fn description_blocks_rs(desc:&XmlNode)->Value{
    let mut blocks=Vec::new();
    for child in desc.children() { match child.name.as_str(){
        "p"=>{let spans=inline_segments_rs(child,&[]);if !spans.is_empty(){blocks.push(serde_json::json!({"type":"paragraph","spans":spans}));}},
        "ul"|"ol"=>{let items:Vec<Value>=child.children_named("li").map(|li|Value::Array(inline_segments_rs(li,&[]))).filter(|v|v.as_array().is_some_and(|a|!a.is_empty())).collect();if !items.is_empty(){blocks.push(serde_json::json!({"type":if child.name=="ol"{"ordered_list"}else{"unordered_list"},"items":items}));}},_=>{} }
    }
    if blocks.is_empty(){let t=collapse_ws(&desc.direct_text());if !t.is_empty(){blocks.push(serde_json::json!({"type":"paragraph","spans":[{"text":t,"styles":[]}]}));}}
    Value::Array(blocks)
}
fn localized_description_values_rs(node:&XmlNode)->serde_json::Map<String,Value>{let mut out=serde_json::Map::new();for d in node.children_named("description"){let v=description_blocks_rs(d);if v.as_array().is_some_and(|a|!a.is_empty()){out.insert(normalize_locale_code_rs(d.attrs.get("lang").map(String::as_str).unwrap_or("")),v);}}out}
fn default_description_rs(node:&XmlNode)->Value{let vals=localized_description_values_rs(node);vals.get("").cloned().or_else(||vals.values().next().cloned()).unwrap_or_else(||Value::Array(vec![]))}

fn join_url_rs(base:&str,value:&str)->String { url::Url::parse(base.trim_end_matches('/')).ok().and_then(|u|u.join(value.trim_start_matches('/')).ok()).map(|u|u.to_string()).unwrap_or_default() }
fn flatpak_icon_rs(component:&XmlNode,dir:&str,id:&str)->String{
    if let Some(icon)=component.children_named("icon").find(|n|n.attrs.get("type").map(String::as_str)==Some("cached")){let name=icon.text_trimmed();for size in ["128x128","64x64"]{let p=std::path::Path::new(dir).join("icons").join(size).join(&name);if p.is_file(){return p.to_string_lossy().into_owned()}}}
    for size in ["128x128","64x64"]{for ext in ["png","svg"]{let p=std::path::Path::new(dir).join("icons").join(size).join(format!("{id}.{ext}"));if p.is_file(){return p.to_string_lossy().into_owned()}}} "application-x-executable".into()
}
fn launchable_rs(c:&XmlNode,id:&str)->String{for n in c.children_named("launchable"){let v=n.text_trimmed();if !v.is_empty()&&(n.attrs.get("type").map(String::as_str)==Some("desktop-id")||v.ends_with(".desktop")){return v}}if id.ends_with(".desktop"){id.into()}else{String::new()}}


fn flatpak_bundle_ref_rs(component: &XmlNode) -> String {
    component.children_named("bundle")
        .find(|n| n.attrs.get("type").map(String::as_str) == Some("flatpak"))
        .map(XmlNode::text_trimmed).unwrap_or_default()
}

fn normalize_flatpak_extension_rs(component: &XmlNode, source: &serde_json::Map<String,Value>) -> Option<serde_json::Map<String,Value>> {
    let id = default_localized_text_rs(component, "id");
    let parent = component.children_named("extends").map(XmlNode::text_trimmed).find(|v| !v.is_empty())?;
    let flatpak_ref = flatpak_bundle_ref_rs(component);
    if id.is_empty() || flatpak_ref.is_empty() { return None; }
    let name = { let v=default_localized_text_rs(component,"name"); if v.is_empty(){id.clone()}else{v} };
    let summary = default_localized_text_rs(component,"summary");
    let remote=source.get("remote").and_then(Value::as_str).unwrap_or("");
    let scope=source.get("scope").and_then(Value::as_str).unwrap_or("");
    let installation=source.get("installation").and_then(Value::as_str).unwrap_or("");
    let arch=source.get("arch").and_then(Value::as_str).unwrap_or("");
    let dir=source.get("appstream_dir").and_then(Value::as_str).unwrap_or("");
    let parts: Vec<&str> = flatpak_ref.split('/').collect();
    let ref_arch = parts.get(2).copied().unwrap_or(arch).to_string();
    let branch = parts.get(3).copied().unwrap_or("").to_string();
    let mut m=serde_json::Map::new();
    m.insert("id".into(),Value::String(id.clone()));
    m.insert("parent_id".into(),Value::String(parent.strip_suffix(".desktop").unwrap_or(&parent).to_string()));
    m.insert("name".into(),Value::String(name)); m.insert("summary".into(),Value::String(summary));
    m.insert("icon".into(),Value::String(flatpak_icon_rs(component,dir,&id)));
    m.insert("flatpak_ref".into(),Value::String(flatpak_ref)); m.insert("flatpak_remote".into(),Value::String(remote.into()));
    m.insert("flatpak_scope".into(),Value::String(scope.into())); m.insert("flatpak_installation".into(),Value::String(installation.into()));
    m.insert("flatpak_arch".into(),Value::String(ref_arch)); m.insert("flatpak_branch".into(),Value::String(branch));
    Some(m)
}

fn normalize_flatpak_component_rs(component:&XmlNode, source:&serde_json::Map<String,Value>, eol:&std::collections::HashSet<String>, _now:i64)->Option<serde_json::Map<String,Value>>{
    let id=default_localized_text_rs(component,"id"); let app_id=id.strip_suffix(".desktop").unwrap_or(&id).to_string(); if eol.contains(&id)||eol.contains(&app_id){return None}
    let name=default_localized_text_rs(component,"name");let summary=default_localized_text_rs(component,"summary");
    let categories:Vec<Value>=component.child("categories").into_iter().flat_map(|n|n.children_named("category")).map(|n|n.text_trimmed()).filter(|s|!s.is_empty()).map(Value::String).collect();if id.is_empty()||name.is_empty()||summary.is_empty()||categories.is_empty(){return None}
    let mut developer=default_localized_text_rs(component,"developer_name");if developer.is_empty(){if let Some(d)=component.child("developer"){developer=default_localized_text_rs(d,"name")}}
    let media=source.get("media_baseurl").and_then(Value::as_str).unwrap_or("");let mut screenshots=Vec::new();if let Some(ss)=component.child("screenshots"){for shot in ss.children_named("screenshot"){let mut seen=std::collections::HashSet::new();let mut imgs=Vec::new();for im in shot.children_named("image"){let v=im.text_trimmed();let candidate=if v.starts_with("http://")||v.starts_with("https://"){v}else if !media.is_empty(){join_url_rs(media,&v)}else{String::new()};if candidate.is_empty()||!seen.insert(candidate.clone()){continue}let w=im.attrs.get("width").and_then(|x|x.parse::<i64>().ok()).unwrap_or(0).max(0);let h=im.attrs.get("height").and_then(|x|x.parse::<i64>().ok()).unwrap_or(0).max(0);imgs.push(serde_json::json!({"url":candidate,"width":w,"height":h}));}imgs.sort_by_key(|v|(v.get("width").and_then(Value::as_i64).unwrap_or(0),v.get("height").and_then(Value::as_i64).unwrap_or(0)));if !imgs.is_empty(){screenshots.push(serde_json::json!({"images":imgs}));}}}
    let url_of=|kind:&str|component.children_named("url").find(|n|n.attrs.get("type").map(String::as_str)==Some(kind)).map(XmlNode::text_trimmed).unwrap_or_default();
    let remote=source.get("remote").and_then(Value::as_str).unwrap_or("");let scope=source.get("scope").and_then(Value::as_str).unwrap_or("");let installation=source.get("installation").and_then(Value::as_str).unwrap_or("");let dir=source.get("appstream_dir").and_then(Value::as_str).unwrap_or("");
    let verified=component.child("custom").into_iter().flat_map(|n|n.children_named("value")).find(|n|n.attrs.get("key").map(String::as_str)==Some("flathub::verification::verified")).is_some_and(|n|n.text_trimmed().eq_ignore_ascii_case("true"));
    let version=component.child("releases").and_then(|r|r.child("release")).and_then(|r|r.attrs.get("version")).cloned().unwrap_or_default();
    let localized_names=localized_text_values_rs(component,"name");let localized_summaries=localized_text_values_rs(component,"summary");let localized_desc=localized_description_values_rs(component);let localized_devs={let a=localized_text_values_rs(component,"developer_name");if !a.is_empty(){a}else{component.child("developer").map(|d|localized_text_values_rs(d,"name")).unwrap_or_default()}};
    let raw_hash={use sha2::{Digest,Sha256};let mut h=Sha256::new();h.update(format!("{}\0{}\0{}\0{}\0{}\0{}",scope,installation,remote,source.get("arch").and_then(Value::as_str).unwrap_or(""),media,dir));let mut stable=String::new();stable_xml_repr(component,&mut stable);h.update(stable.as_bytes());format!("{:x}",h.finalize())};
    let mut m=serde_json::Map::new();macro_rules! ins{($k:expr,$v:expr)=>{m.insert($k.into(),$v);}}
    ins!("identity",Value::String(format!("flatpak:{scope}:{installation}:{remote}:{id}")));ins!("_metadata_hash",Value::String(raw_hash));ins!("id",Value::String(id.clone()));ins!("name",Value::String(name));ins!("summary",Value::String(summary));ins!("description_blocks",default_description_rs(component));ins!("localized_names",Value::Object(localized_names));ins!("localized_summaries",Value::Object(localized_summaries));ins!("localized_descriptions",Value::Object(localized_desc));ins!("localized_developers",Value::Object(localized_devs));ins!("packages",Value::Array(vec![Value::String(app_id)]));ins!("categories",Value::Array(categories));ins!("launchable",Value::String(launchable_rs(component,&id)));ins!("icon",Value::String(flatpak_icon_rs(component,dir,&id)));ins!("screenshots",Value::Array(screenshots));ins!("homepage",Value::String(url_of("homepage")));ins!("donation",Value::String(url_of("donation")));ins!("license",Value::String(default_localized_text_rs(component,"project_license")));ins!("developer",Value::String(developer));ins!("verified",Value::Bool(verified));ins!("origin",Value::String(remote.into()));ins!("source",Value::String("flatpak".into()));ins!("version",Value::String(version));ins!("flatpak_remote",Value::String(remote.into()));ins!("flatpak_scope",Value::String(scope.into()));ins!("flatpak_installation",Value::String(installation.into()));let bundle=flatpak_bundle_ref_rs(component);if !bundle.is_empty(){let parts:Vec<String>=bundle.split('/').map(str::to_string).collect();ins!("flatpak_ref",Value::String(bundle));if parts.len()>2{ins!("flatpak_arch",Value::String(parts[2].clone()));}if parts.len()>3{ins!("flatpak_branch",Value::String(parts[3].clone()));}}Some(m)
}


fn strip_markup_rs(value: &str) -> String {
    let wrapped = format!("<root>{value}</root>");
    if let Ok(root) = parse_xml_tree(wrapped.as_bytes()) {
        return root.all_text().split_whitespace().collect::<Vec<_>>().join(" ");
    }
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn description_blocks_from_markup_rs(value: &str) -> Value {
    let text = value.trim();
    if text.is_empty() { return Value::Array(vec![]); }
    let wrapped = format!("<description>{text}</description>");
    if let Ok(root) = parse_xml_tree(wrapped.as_bytes()) {
        let blocks = description_blocks_rs(&root);
        if blocks.as_array().is_some_and(|a| !a.is_empty()) { return blocks; }
    }
    let plain = strip_markup_rs(text);
    let blocks: Vec<Value> = plain.split("\n\n").map(str::trim).filter(|s| !s.is_empty())
        .map(|p| serde_json::json!({"type":"paragraph","spans":[{"text":p,"styles":[]}]})).collect();
    Value::Array(blocks)
}

fn normalize_native_payload_rs(mut m: serde_json::Map<String, Value>) -> Option<serde_json::Map<String, Value>> {
    let id = m.get("id").and_then(Value::as_str).unwrap_or("").trim().to_string();
    let name = m.get("name").and_then(Value::as_str).unwrap_or("").trim().to_string();
    let summary = strip_markup_rs(m.get("summary").and_then(Value::as_str).unwrap_or(""));
    let packages: Vec<Value> = m.get("packages").and_then(Value::as_array).into_iter().flatten()
        .filter_map(Value::as_str).map(str::trim).filter(|s| !s.is_empty()).map(|s| Value::String(s.to_string())).collect();
    let categories: Vec<Value> = m.get("categories").and_then(Value::as_array).into_iter().flatten()
        .filter_map(Value::as_str).map(str::trim).filter(|s| !s.is_empty()).map(|s| Value::String(s.to_string())).collect();
    if id.is_empty() || name.is_empty() || summary.is_empty() || packages.is_empty() || categories.is_empty() { return None; }

    let identity = m.get("identity").and_then(Value::as_str).unwrap_or("").to_string();
    let description = m.remove("description").and_then(|v| v.as_str().map(str::to_string)).unwrap_or_default();
    let launchable = m.get("launchable").and_then(Value::as_str).unwrap_or("").trim().to_string();
    let icon = m.get("icon").and_then(Value::as_str).unwrap_or("application-x-executable").to_string();
    let screenshots = clean_screens(m.get("screenshots"));
    let homepage = m.get("homepage").and_then(Value::as_str).unwrap_or("").trim().to_string();
    let donation = m.get("donation").and_then(Value::as_str).unwrap_or("").trim().to_string();
    let license = m.get("license").and_then(Value::as_str).unwrap_or("").trim().to_string();
    let developer = m.get("developer").and_then(Value::as_str).unwrap_or("").trim().to_string();
    let origin = m.get("origin").and_then(Value::as_str).unwrap_or("").trim().to_string();
    let version = m.get("version").and_then(Value::as_str).unwrap_or("").trim().to_string();

    let fingerprint = {
        use sha2::{Digest, Sha256};
        let payload = serde_json::json!({
            "categories": categories.clone(),
            "description": description.clone(),
            "developer": developer.clone(),
            "donation": donation.clone(),
            "homepage": homepage.clone(),
            "icon": icon.clone(),
            "id": id.clone(),
            "identity": identity.clone(),
            "launchable": launchable.clone(),
            "license": license.clone(),
            "name": name.clone(),
            "origin": origin.clone(),
            "packages": packages.clone(),
            "screenshots": screenshots.clone(),
            "summary": m.get("summary").and_then(Value::as_str).unwrap_or(""),
            "version": version.clone(),
        });
        let raw = serde_json::to_vec(&payload).unwrap_or_default();
        format!("{:x}", Sha256::digest(raw))
    };

    let mut out = serde_json::Map::new();
    out.insert("identity".into(), Value::String(identity));
    out.insert("_metadata_hash".into(), Value::String(fingerprint));
    out.insert("id".into(), Value::String(id));
    out.insert("name".into(), Value::String(name));
    out.insert("summary".into(), Value::String(summary));
    out.insert("description_blocks".into(), description_blocks_from_markup_rs(&description));
    out.insert("packages".into(), Value::Array(packages));
    out.insert("categories".into(), Value::Array(categories));
    out.insert("launchable".into(), Value::String(launchable));
    out.insert("icon".into(), Value::String(icon));
    out.insert("screenshots".into(), screenshots);
    out.insert("homepage".into(), Value::String(homepage));
    out.insert("donation".into(), Value::String(donation));
    out.insert("license".into(), Value::String(license));
    out.insert("developer".into(), Value::String(developer));
    out.insert("origin".into(), Value::String(origin));
    out.insert("source".into(), Value::String("native".into()));
    out.insert("version".into(), Value::String(version));
    Some(out)
}

/// Formula metadata is independent of desktop AppStream identities.
/// No name-based merging: a CLI formula can share a name with a desktop app.
fn normalize_homebrew_formula(value: &Value, arch: &str) -> Option<serde_json::Map<String, Value>> {
    let mut item = value.as_object()?.clone();
    let tag = format!("{arch}_linux");
    if let Some(variation) = item.get("variations").and_then(|v|v.get(&tag)).and_then(Value::as_object).cloned() {
        item.extend(variation);
    }
    let name = item.get("name")?.as_str()?.trim();
    if name.is_empty() || !name.chars().all(|c|c.is_ascii_alphanumeric() || matches!(c,'+'|'-'|'_'|'.'|'@')) || name.starts_with('-') { return None; }
    if item.get("disabled").and_then(Value::as_bool).unwrap_or(false) { return None; }
    if item.get("requirements").and_then(Value::as_array).is_some_and(|requirements| requirements.iter().any(|r| {
        let stable = r.get("contexts").and_then(Value::as_array).map_or(true, |a| a.is_empty() || a.iter().any(|v|v.as_str()==Some("stable")));
        if !stable { return false; }
        match r.get("name").and_then(Value::as_str).unwrap_or("") {
            "macos" | "xcode" => true,
            "arch" => r.get("version").and_then(Value::as_str).is_some_and(|v| !v.is_empty() && v != arch),
            _ => false,
        }
    })) { return None; }
    let summary = item.get("desc").and_then(Value::as_str).unwrap_or("");
    let mut paragraphs = vec![summary.to_string()];
    if let Some(caveats) = item.get("caveats").and_then(Value::as_str).filter(|v|!v.trim().is_empty()) { paragraphs.push(caveats.to_string()); }
    let id = format!("homebrew:{name}");
    let blocks: Vec<Value> = paragraphs.iter().filter(|p|!p.is_empty()).map(|p|serde_json::json!({"type":"paragraph","spans":[{"text":p}]})).collect();
    serde_json::json!({
        "identity":id, "id":id, "source":"homebrew", "origin":"homebrew/core",
        "name":name, "summary":summary, "description_blocks":blocks,
        "packages":[name], "categories":[], "icon":"brewpkg.webp", "screenshots":[],
        "homepage":item.get("homepage").and_then(Value::as_str).unwrap_or(""),
        "license":item.get("license").and_then(Value::as_str).unwrap_or(""),
        "version":item.get("versions").and_then(|v|v.get("stable")).and_then(Value::as_str).unwrap_or(""),
        "launchable":"", "developer":"", "verified":false
    }).as_object().cloned()
}

const HOMEBREW_CACHE_SCHEMA: u32 = 2;

#[derive(Serialize, Deserialize)]
struct CachedHomebrewFormulae {
    schema: u32,
    key: String,
    entries: Vec<serde_json::Map<String, Value>>,
}

fn load_homebrew_formulae(path: &str, arch: &str) -> Result<Vec<serde_json::Map<String, Value>>, String> {
    let source = std::path::Path::new(path);
    let metadata = fs::metadata(source).map_err(|e| e.to_string())?;
    let modified = metadata.modified().map_err(|e| e.to_string())?
        .duration_since(std::time::UNIX_EPOCH).map_err(|e| e.to_string())?.as_nanos();
    let popularity_path = source.with_file_name("popularity.json");
    let popularity_state = fs::metadata(&popularity_path).ok().and_then(|m| {
        Some((m.len(), m.modified().ok()?.duration_since(std::time::UNIX_EPOCH).ok()?.as_nanos()))
    });
    let key = format!("{arch}:{}:{modified}:{popularity_state:?}", metadata.len());
    let binary_path = source.with_extension(format!("{arch}.bin"));
    if let Ok(bytes) = fs::read(&binary_path) {
        if let Ok(cache) = rmp_serde::from_slice::<CachedHomebrewFormulae>(&bytes) {
            if cache.schema == HOMEBREW_CACHE_SCHEMA && cache.key == key && !cache.entries.is_empty() {
                return Ok(cache.entries);
            }
        }
    }
    let text = fs::read_to_string(source).map_err(|e| e.to_string())?;
    let values: Value = serde_json::from_str(&text).map_err(|e| e.to_string())?;
    let rows = values.as_array().ok_or("Homebrew catalog must be an array")?;
    let popularity: std::collections::HashMap<String, u64> = fs::read(&popularity_path).ok()
        .and_then(|bytes| serde_json::from_slice(&bytes).ok()).unwrap_or_default();
    let entries: Vec<_> = rows.iter().filter_map(|value| normalize_homebrew_formula(value, arch)).map(|mut entry| {
        let name = entry.get("name").and_then(Value::as_str).unwrap_or("");
        let count = popularity.get(name).copied().unwrap_or(0);
        entry.insert("homebrew_install_count".into(), Value::Number(count.into()));
        entry
    }).collect();
    if entries.is_empty() { return Err("No usable Linux formulae".into()); }
    let cache = CachedHomebrewFormulae { schema: HOMEBREW_CACHE_SCHEMA, key, entries };
    let bytes = rmp_serde::to_vec_named(&cache).map_err(|e| e.to_string())?;
    // Exclusive temporary files also isolate simultaneous catalog workers.
    static TEMP_SEQUENCE: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let sequence = TEMP_SEQUENCE.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    let temporary = binary_path.with_extension(format!("bin.{}.{}.tmp", std::process::id(), sequence));
    let result = (|| -> std::io::Result<()> {
        let mut file = fs::OpenOptions::new().write(true).create_new(true).open(&temporary)?;
        file.write_all(&bytes)?;
        file.sync_all()?;
        drop(file);
        let written = fs::read(&temporary)?;
        let verified: CachedHomebrewFormulae = rmp_serde::from_slice(&written)
            .map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error.to_string()))?;
        if written != bytes || verified.schema != HOMEBREW_CACHE_SCHEMA
            || verified.key != cache.key || verified.entries.is_empty() {
            return Err(std::io::Error::new(std::io::ErrorKind::InvalidData,
                "Homebrew binary cache failed verification"));
        }
        fs::rename(&temporary, &binary_path)
    })();
    if let Err(error) = result {
        let _ = fs::remove_file(&temporary);
        return Err(format!("Could not publish Homebrew binary cache: {error}"));
    }
    Ok(cache.entries)
}

#[pyclass]
pub(crate) struct AppStreamGeneration {
    previous: Vec<serde_json::Map<String, Value>>,
    entries: Vec<serde_json::Map<String, Value>>,
    extensions: Vec<serde_json::Map<String, Value>>,
}

impl AppStreamGeneration {
    fn previous_by_id(&self) -> std::collections::HashMap<&str, &serde_json::Map<String, Value>> {
        let mut out = std::collections::HashMap::with_capacity(self.previous.len());
        for map in &self.previous {
            let id = map.get("id").and_then(Value::as_str).unwrap_or("");
            if !id.is_empty() {
                out.insert(id, map);
            }
        }
        out
    }
}

#[pymethods]
impl AppStreamGeneration {
    #[new]
    fn new(py: Python<'_>, previous_path: &str) -> Self {
        let previous_path = previous_path.to_string();
        let previous = py.allow_threads(move || {
            fs::read_to_string(&previous_path)
                .ok()
                .and_then(|raw| serde_json::from_str::<Value>(&raw).ok())
                .and_then(|value| value.as_array().cloned())
                .unwrap_or_default()
                .into_iter()
                .filter_map(|value| value.as_object().cloned())
                .collect()
        });
        Self { previous, entries: Vec::new(), extensions: Vec::new() }
    }

    fn __len__(&self) -> usize {
        self.entries.len()
    }

    fn add_native(&mut self, py: Python<'_>, components: &Bound<'_, PyList>) -> PyResult<usize> {
        // GI extraction still arrives as small Python batches. Detach only that
        // batch, then keep the normalized result native for the rest of refresh.
        let mut maps = Vec::with_capacity(components.len());
        for obj in components.iter() {
            if let Value::Object(map) = py_to_json(&obj)? {
                maps.push(map);
            }
        }
        let normalized = py.allow_threads(move || {
            maps.into_iter().filter_map(normalize_native_payload_rs).collect::<Vec<_>>()
        });
        let count = normalized.len();
        self.entries.extend(normalized);
        Ok(count)
    }

    #[staticmethod]
    fn homebrew_snapshot_valid(py: Python<'_>, path: &str, max_bytes: u64) -> bool {
        let path = path.to_string();
        py.allow_threads(move || {
            validate_homebrew_snapshot_rs(&path, max_bytes)
        })
    }

    fn release_buffers(&mut self, py: Python<'_>) {
        // Dropping thousands of JSON maps must not stop GTK via the GIL.
        py.allow_threads(|| {
            self.previous.clear();
            self.entries.clear();
            self.extensions.clear();
        });
    }

    fn previous_source_count(&self, source: &str) -> usize {
        self.previous.iter().filter(|entry| {
            entry.get("source").and_then(Value::as_str) == Some(source)
        }).count()
    }

    fn homebrew_popularity_matches_previous(&self, py: Python<'_>) -> bool {
        py.allow_threads(|| {
            homebrew_counts_match(&self.entries, &self.previous)
        })
    }

    fn retain_other_sources(&mut self, py: Python<'_>, source: &str) {
        py.allow_threads(|| {
            self.entries.extend(self.previous.iter().filter(|entry| {
                entry.get("source").and_then(Value::as_str) != Some(source)
            }).cloned());
        });
    }

    fn add_homebrew(&mut self, py: Python<'_>, path: &str, arch: &str) -> PyResult<usize> {
        let path = path.to_string(); let arch = arch.to_string();
        let maps = py.allow_threads(move || load_homebrew_formulae(&path, &arch))
            .map_err(pyo3::exceptions::PyValueError::new_err)?;
        let count = maps.len(); self.entries.extend(maps); Ok(count)
    }

    fn add_appimage(&mut self, _py: Python<'_>, components: &Bound<'_, PyList>) -> PyResult<usize> {
        let mut maps = Vec::with_capacity(components.len());
        for obj in components.iter() {
            if let Value::Object(map) = py_to_json(&obj)? {
                if map.get("source").and_then(Value::as_str) == Some("appimage") {
                    maps.push(map);
                }
            }
        }
        let count = maps.len();
        self.entries.extend(maps);
        Ok(count)
    }

    fn add_snap(&mut self, _py: Python<'_>, components: &Bound<'_, PyList>) -> PyResult<usize> {
        let mut maps = Vec::with_capacity(components.len());
        for obj in components.iter() {
            if let Value::Object(map) = py_to_json(&obj)? { maps.push(map); }
        }
        let count = maps.len();
        self.entries.extend(maps);
        Ok(count)
    }

    fn add_flatpak_source(
        &mut self,
        py: Python<'_>,
        path: &str,
        source_json: &str,
        eol_ids: Vec<String>,
        now: i64,
    ) -> PyResult<usize> {
        let path = path.to_string();
        let source_json = source_json.to_string();
        let normalized = py.allow_threads(move || {
            use std::io::Read;
            let mut bytes = Vec::new();
            if path.ends_with(".gz") {
                let file = match fs::File::open(&path) { Ok(v) => v, Err(_) => return (Vec::new(), Vec::new()) };
                let mut gz = flate2::read::GzDecoder::new(file);
                if gz.read_to_end(&mut bytes).is_err() { return (Vec::new(), Vec::new()); }
            } else {
                bytes = match fs::read(&path) { Ok(v) => v, Err(_) => return (Vec::new(), Vec::new()) };
            }

            let root = match parse_xml_tree(&bytes) { Ok(v) => v, Err(_) => return (Vec::new(), Vec::new()) };
            let mut source: serde_json::Map<String, Value> =
                serde_json::from_str::<Value>(&source_json)
                    .ok().and_then(|v| v.as_object().cloned()).unwrap_or_default();
            if source.get("media_baseurl").and_then(Value::as_str).unwrap_or("").is_empty() {
                if let Some(v) = root.attrs.get("media_baseurl").or_else(|| root.attrs.get("media-baseurl")) {
                    source.insert("media_baseurl".into(), Value::String(v.clone()));
                }
            }
            let eol: std::collections::HashSet<String> = eol_ids.into_iter().collect();
            let mut apps = Vec::new();
            let mut extensions = Vec::new();
            for component in root.children_named("component") {
                if component.attrs.get("type").map(String::as_str) == Some("addon") {
                    if let Some(extension) = normalize_flatpak_extension_rs(component, &source) {
                        extensions.push(extension);
                    }
                } else if let Some(app) = normalize_flatpak_component_rs(component, &source, &eol, now) {
                    apps.push(app);
                }
            }
            (apps, extensions)
        });
        let (normalized, extensions) = normalized;
        let count = normalized.len();
        self.entries.extend(normalized);
        self.extensions.extend(extensions);
        Ok(count)
    }

    fn write_partial(&self, py: Python<'_>, path: &str, schema: u64) -> PyResult<()> {
        let path = path.to_string();
        let entries = self.entries.clone();
        py.allow_threads(move || -> PyResult<()> {
            let processed = entries.iter().filter_map(|map| {
                map.get("identity").and_then(Value::as_str).filter(|v| !v.is_empty()).map(str::to_string)
            }).collect::<Vec<_>>();
            let mut payload = serde_json::Map::new();
            payload.insert("schema".into(), Value::Number(schema.into()));
            payload.insert("entries".into(), Value::Array(entries.into_iter().map(Value::Object).collect()));
            payload.insert("processed".into(), Value::Array(processed.into_iter().map(Value::String).collect()));
            atomic_write_json_value(&path, &Value::Object(payload))
        })
    }

    fn apply_review_summaries(
        &mut self,
        py: Python<'_>,
        summaries_json: &str,
        snap_summaries_json: &str,
        fetch_available: bool,
        snap_fetch_available: bool,
    ) -> PyResult<()> {
        let summaries: std::collections::HashMap<String, Value> =
            serde_json::from_str(summaries_json).unwrap_or_default();
        let snap_summaries: std::collections::HashMap<String, Value> =
            serde_json::from_str(snap_summaries_json).unwrap_or_default();
        let previous = self.previous_by_id().into_iter().filter_map(|(id, map)| {
            let count = map.get("review_count").and_then(Value::as_i64)?;
            let rating = map.get("review_rating").and_then(Value::as_f64)?;
            Some((id.to_string(), (rating, count)))
        }).collect::<std::collections::HashMap<_, _>>();

        py.allow_threads(|| {
            for map in &mut self.entries {
                if map.get("source").and_then(Value::as_str) == Some("homebrew") {
                    map.remove("review_rating"); map.remove("review_count"); continue;
                }
                let id = map.get("id").and_then(Value::as_str).unwrap_or("").to_string();
                let odrs = if fetch_available {
                    summaries.get(&id).and_then(Value::as_object).and_then(|summary| Some((
                        summary.get("review_rating")?.as_f64()?,
                        summary.get("review_count")?.as_i64()?,
                    )))
                } else { previous.get(&id).copied() };

                // Canonical exposes raw_rating as a normalized binary-vote score.
                // Convert the [0, 1] value to LT/ODRS' [0, 100] scale before
                // weighting it by the number of Canonical votes.
                let snap = if map.get("source").and_then(Value::as_str) == Some("snap") && snap_fetch_available {
                    let snap_id = map.get("snap_id").and_then(Value::as_str).unwrap_or("");
                    snap_summaries.get(snap_id).and_then(Value::as_object).and_then(|summary| {
                        let raw = summary.get("raw_rating")?.as_f64()?;
                        let count = summary.get("total_votes")?.as_i64()?;
                        let band = summary.get("ratings_band").and_then(Value::as_i64).unwrap_or(5);
                        if count <= 0 || band == 5 || !(0.0..=1.0).contains(&raw) { return None; }
                        Some(((raw * 100.0).clamp(0.0, 100.0), count))
                    })
                } else { None };

                let pair = match (odrs, snap) {
                    (Some((orating, ocount)), Some((srating, scount))) if ocount > 0 && scount > 0 => {
                        let count = ocount.saturating_add(scount);
                        Some(((orating * ocount as f64 + srating * scount as f64) / count as f64, count))
                    }
                    (Some(pair), _) => Some(pair),
                    (None, Some(pair)) => Some(pair),
                    (None, None) => None,
                };

                if let Some((rating, count)) = pair {
                    if let Some(value) = serde_json::Number::from_f64(rating) {
                        map.insert("review_rating".into(), Value::Number(value));
                    }
                    map.insert("review_count".into(), Value::Number(count.into()));
                } else {
                    map.remove("review_rating");
                    map.remove("review_count");
                }
            }
        });
        Ok(())
    }

    fn publish_extensions(&self, py: Python<'_>, path: &str) -> PyResult<usize> {
        let path = path.to_string();
        let mut extensions = self.extensions.clone();
        py.allow_threads(move || -> PyResult<usize> {
            extensions.sort_by(|a,b| {
                a.get("parent_id").and_then(Value::as_str).unwrap_or("").cmp(b.get("parent_id").and_then(Value::as_str).unwrap_or(""))
                    .then_with(|| a.get("name").and_then(Value::as_str).unwrap_or("").to_lowercase().cmp(&b.get("name").and_then(Value::as_str).unwrap_or("").to_lowercase()))
            });
            let count=extensions.len();
            atomic_write_json_value(&path,&Value::Array(extensions.into_iter().map(Value::Object).collect()))?;
            Ok(count)
        })
    }

    fn publish(
        &mut self,
        py: Python<'_>,
        output_path: &str,
        reuse_previous: bool,
    ) -> PyResult<(bool, usize)> {
        let output_path = output_path.to_string();
        py.allow_threads(|| -> PyResult<(bool, usize)> {
            let mut previous_by_identity =
                std::collections::HashMap::<String, serde_json::Map<String, Value>>::new();
            if reuse_previous {
                previous_by_identity.reserve(self.previous.len());
                for map in &self.previous {
                    let identity = map.get("identity").and_then(Value::as_str).unwrap_or("");
                    if !identity.is_empty() {
                        previous_by_identity.insert(identity.to_string(), map.clone());
                    }
                }
            }

            let mut reconciled = Vec::with_capacity(self.entries.len());
            for map in self.entries.drain(..) {
                let identity = map.get("identity").and_then(Value::as_str).unwrap_or("");
                let metadata_hash = map.get("_metadata_hash").and_then(Value::as_str).unwrap_or("");
                let source = map.get("source").and_then(Value::as_str).unwrap_or("");

                let reused = if reuse_previous && !identity.is_empty() && !metadata_hash.is_empty() {
                    previous_by_identity.get(identity).filter(|old| {
                        old.get("source").and_then(Value::as_str).unwrap_or("") == source
                            && old.get("_metadata_hash").and_then(Value::as_str).unwrap_or("") == metadata_hash
                    }).cloned()
                } else { None };

                if let Some(mut old) = reused {
                    update_reused_metadata(&mut old, &map);
                    reconciled.push(old);
                } else {
                    reconciled.push(map);
                }
            }

            // A transient feed failure must not publish an empty AppImage source.
            // The feed loader rejects empty snapshots, so absence here indicates
            // an unavailable source rather than an intentional catalog deletion.
            if reuse_previous
                && !reconciled.iter().any(|entry| entry.get("source").and_then(Value::as_str) == Some("appimage"))
            {
                reconciled.extend(self.previous.iter().filter(|entry| {
                    entry.get("source").and_then(Value::as_str) == Some("appimage")
                }).cloned());
            }

            reconciled.sort_by(|a, b| {
                let an = a.get("name").and_then(Value::as_str).unwrap_or("").to_lowercase();
                let bn = b.get("name").and_then(Value::as_str).unwrap_or("").to_lowercase();
                an.cmp(&bn).then_with(|| {
                    a.get("id").and_then(Value::as_str).unwrap_or("")
                        .cmp(b.get("id").and_then(Value::as_str).unwrap_or(""))
                })
            });

            let changed = self.previous != reconciled;
            let count = reconciled.len();
            let value = Value::Array(reconciled.iter().cloned().map(Value::Object).collect());
            atomic_write_json_value(&output_path, &value)?;
            self.entries = reconciled;
            Ok((changed, count))
        })
    }
}

fn validate_homebrew_snapshot_rs(path: &str, max_bytes: u64) -> bool {
            let Ok(metadata) = fs::metadata(path) else { return false; };
            if metadata.len() == 0 || metadata.len() > max_bytes { return false; }
            let Ok(file) = fs::File::open(path) else { return false; };
            let Ok(rows) = serde_json::from_reader::<_, Vec<Value>>(std::io::BufReader::new(file)) else { return false; };
            !rows.is_empty() && rows.iter().all(|row| {
                row.as_object().and_then(|m|m.get("name")).and_then(Value::as_str)
                    .is_some_and(|name|!name.trim().is_empty())
            })
}

fn homebrew_counts_match(current_entries: &[serde_json::Map<String, Value>], previous_entries: &[serde_json::Map<String, Value>]) -> bool {
        let counts = |entries: &[serde_json::Map<String, Value>]| {
            entries.iter().filter(|entry| entry.get("source").and_then(Value::as_str) == Some("homebrew"))
                .map(|entry| (
                    entry.get("identity").and_then(Value::as_str).unwrap_or("").to_string(),
                    entry.get("homebrew_install_count").and_then(Value::as_u64),
                )).collect::<std::collections::HashMap<_, _>>()
        };
        let current = counts(current_entries);
        !current.is_empty() && current.values().all(Option::is_some)
            && current == counts(previous_entries)
}

fn update_reused_metadata(old: &mut serde_json::Map<String, Value>, current: &serde_json::Map<String, Value>) {
    for key in ["review_rating", "review_count", "homebrew_install_count"] {
        match current.get(key) {
            Some(value) => { old.insert(key.to_string(), value.clone()); }
            None => { old.remove(key); }
        }
    }
}

fn atomic_write_json_value(path: &str, value: &Value) -> PyResult<()> {
    let path = std::path::Path::new(path);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|e| pyo3::exceptions::PyOSError::new_err(e.to_string()))?;
    }
    let tmp = path.with_file_name(format!(
        "{}.tmp",
        path.file_name().and_then(|v| v.to_str()).unwrap_or("catalog.json")
    ));
    let result = (|| -> PyResult<()> {
        let mut file = fs::File::create(&tmp)
            .map_err(|e| pyo3::exceptions::PyOSError::new_err(e.to_string()))?;
        serde_json::to_writer(&mut file, value)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        file.flush()
            .map_err(|e| pyo3::exceptions::PyOSError::new_err(e.to_string()))?;
        file.sync_all()
            .map_err(|e| pyo3::exceptions::PyOSError::new_err(e.to_string()))?;
        fs::rename(&tmp, path)
            .map_err(|e| pyo3::exceptions::PyOSError::new_err(e.to_string()))?;
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_file(&tmp);
    }
    result
}

fn collect_search_packages(value: Option<&Value>, out: &mut Vec<String>) {
    let Some(value) = value else { return; };
    match value {
        Value::String(s) => { let s=s.trim().to_lowercase(); if !s.is_empty() && !out.contains(&s) { out.push(s); } }
        Value::Array(values) => for value in values { collect_search_packages(Some(value), out); },
        Value::Object(values) => for value in values.values() { collect_search_packages(Some(value), out); },
        _ => {}
    }
}

// The warm runtime cache deliberately does not deserialize every AppStream entry
// into serde_json::Value.  It keeps the fields needed for indexing/search typed,
// while the complete Python-facing entry remains an opaque MessagePack blob and
// is decoded only when that entry actually crosses the PyO3 boundary.
#[derive(Clone, Serialize, Deserialize)]
struct RuntimeAppStreamEntry {
    category: String,
    appstream_id: String,
    name: String,
    canonical_name: String,
    source: String,
    package_names: Vec<String>,
    search_packages: Vec<String>,
    nix_packages: Vec<String>,
    description_lower: String,
    developer_lower: String,
    is_new: bool,
    review_rating: Option<f64>,
    review_subscore: Option<i64>,
    category_review_score: Option<i64>,
    #[serde(default)]
    homebrew_install_count: u64,
    #[serde(with = "serde_bytes")]
    payload: Vec<u8>,
}

impl RuntimeAppStreamEntry {
    fn from_value(value: Value) -> Option<Self> {
        let category = value.get("category").and_then(Value::as_str).unwrap_or("").to_string();
        let appstream_id = value.get("appstream_id").and_then(Value::as_str).unwrap_or("").to_string();
        let name = value.get("name").and_then(Value::as_str).unwrap_or("").to_string();
        let canonical_name = value.get("appstream_canonical_name").and_then(Value::as_str).unwrap_or("").to_string();
        let source = value.get("appstream_source").and_then(Value::as_str).unwrap_or("").to_string();
        let mut package_names = Vec::new();
        collect_search_packages(value.get("package-name"), &mut package_names);
        let mut search_packages = package_names.clone();
        if let Some(options) = value.get("source_options").and_then(Value::as_array) {
            for option in options { collect_search_packages(option.get("package-name"), &mut search_packages); }
        }
        let mut nix_packages = Vec::new();
        if source == "nix" {
            collect_search_packages(value.get("package-name"), &mut nix_packages);
        }
        if let Some(options) = value.get("source_options").and_then(Value::as_array) {
            for option in options {
                if option.get("appstream_source").and_then(Value::as_str) == Some("nix") {
                    collect_search_packages(option.get("package-name"), &mut nix_packages);
                }
            }
        }
        let description_lower = value.get("description").and_then(Value::as_str).unwrap_or("").to_lowercase();
        let developer_lower = value.get("developer").and_then(Value::as_str).unwrap_or("").to_lowercase();
        let is_new = value.get("is_new").and_then(Value::as_bool).unwrap_or(false);
        let review_rating = value.get("review_rating").and_then(Value::as_f64);
        let review_subscore = value.get("review_subscore").and_then(Value::as_i64);
        let category_review_score = value.get("_category_review_score").and_then(Value::as_i64);
        let homebrew_install_count = value.get("homebrew_install_count").and_then(Value::as_u64).unwrap_or(0);
        let payload = rmp_serde::to_vec_named(&value).ok()?;
        Some(Self {
            category, appstream_id, name, canonical_name, source, package_names,
            search_packages, nix_packages, description_lower, developer_lower, is_new,
            review_rating, review_subscore, category_review_score, homebrew_install_count, payload,
        })
    }

    fn decode(&self) -> Option<Value> {
        rmp_serde::from_slice(&self.payload).ok()
    }
}


fn browse_identity_values(value: &serde_json::Map<String, Value>) -> Vec<String> {
    let mut values = Vec::new();
    for key in ["id", "appstream_id", "appstream_canonical_name", "canonical_name", "registry_name", "repo_app_id", "name"] {
        if let Some(v) = value.get(key).and_then(Value::as_str) {
            let v = v.trim().to_lowercase();
            if !v.is_empty() { values.push(v); }
        }
    }
    let mut add_package = |v: &Value| {
        if let Some(s) = v.as_str() {
            let s = s.trim().to_lowercase();
            if !s.is_empty() { values.push(s); }
        }
    };
    if let Some(packages) = value.get("package-name") {
        if let Some(items) = packages.as_array() { for item in items { add_package(item); } }
        else { add_package(packages); }
    }
    if let Some(path) = value.get("path").and_then(Value::as_str) {
        let leaf = path.rsplit('/').next().unwrap_or(path);
        let stem = leaf.rsplit_once('.').map(|(stem, _)| stem).unwrap_or(leaf).to_lowercase();
        if !stem.is_empty() { values.push(stem); }
    }
    values.sort(); values.dedup(); values
}

fn browse_session_key(value: &serde_json::Map<String, Value>) -> String {
    browse_identity_values(value).into_iter().next().unwrap_or_else(|| {
        format!("entry:{}:{}", value.get("name").and_then(Value::as_str).unwrap_or(""), value.get("path").and_then(Value::as_str).unwrap_or(""))
    })
}

fn browse_hash(key: &str, salt: &str) -> u64 {
    static STATE: OnceLock<std::collections::hash_map::RandomState> = OnceLock::new();
    let state = STATE.get_or_init(std::collections::hash_map::RandomState::new);
    let mut hasher = state.build_hasher();
    salt.hash(&mut hasher); key.hash(&mut hasher); hasher.finish()
}

fn browse_unit(key: &str, salt: &str) -> f64 {
    (browse_hash(key, salt) as f64) / (u64::MAX as f64)
}


fn browse_is_appstream(value: &serde_json::Map<String, Value>) -> bool { value.get("is_appstream_entry").and_then(Value::as_bool).unwrap_or(false) }
fn browse_is_curated(value: &serde_json::Map<String, Value>) -> bool {
    if browse_is_appstream(value) { return false; }
    let local = value.get("path").and_then(Value::as_str).unwrap_or("").contains(".local/linuxtoys/scripts");
    !local && (value.get("is_repo_entry").and_then(Value::as_bool).unwrap_or(false) || value.get("is_script").and_then(Value::as_bool).unwrap_or(false))
}
fn browse_is_known(value: &serde_json::Map<String, Value>, known: &std::collections::HashSet<String>) -> bool {
    browse_identity_values(value).iter().any(|v| known.contains(v))
}
fn browse_is_nix_distributed(value: &serde_json::Map<String, Value>) -> bool {
    value.get("appstream_source").and_then(Value::as_str) == Some("nix")
        && value
            .get("category")
            .and_then(Value::as_str)
            .map(str::trim)
            .is_some_and(|category| !category.is_empty() && category != "nix")
}
fn spread_browse_cohort_rs(base: Vec<Value>, cohort: Vec<Value>) -> Vec<Value> {
    // Nixpkgs has no popularity/review feed, so its rows would otherwise sit
    // in one block at the end of a category. Slot them evenly between the
    // ranked rows, with a session-stable random jitter inside each slot so the
    // spread stays even without looking like a fixed interleave.
    if cohort.is_empty() { return base }
    if base.is_empty() { return cohort }
    let total = base.len().saturating_add(cohort.len());
    let count = cohort.len();
    let mut slots = Vec::with_capacity(count);
    for (index, item) in cohort.iter().enumerate() {
        let left = index.saturating_mul(total) / count;
        let right = ((index + 1).saturating_mul(total) / count).saturating_sub(1).max(left);
        let width = right.saturating_sub(left).saturating_add(1);
        let key = browse_session_key(item.as_object().unwrap());
        let jitter = if width > 1 {
            (browse_unit(&key, "nix-category-spread") * (width as f64)) as usize
        } else { 0 };
        slots.push(left.saturating_add(jitter.min(width.saturating_sub(1))));
    }
    let mut base = base.into_iter();
    let mut cohort = cohort.into_iter();
    let mut out = Vec::with_capacity(total);
    let mut slot_index = 0usize;
    for position in 0..total {
        if slot_index < slots.len() && slots[slot_index] == position {
            if let Some(item) = cohort.next() { out.push(item); }
            slot_index += 1;
        } else if let Some(item) = base.next() {
            out.push(item);
        }
    }
    out.extend(base);
    out.extend(cohort);
    out
}

fn rank_browse_values(values: &mut [Value], known_popular: &[String]) {
    let known:std::collections::HashSet<String>=known_popular.iter().map(|s|s.trim().to_lowercase()).filter(|s|!s.is_empty()).collect();
    let rows:Vec<(Option<f64>,Option<i64>)>=values.iter().map(|v|(v.get("review_rating").and_then(Value::as_f64),v.get("review_count").and_then(Value::as_i64))).collect();
    let reviews=crate::popularity::review_subscores(rows);
    for (v,score) in values.iter_mut().zip(reviews) {
        if let Some(m)=v.as_object_mut(){
            if let Some(score)=score{m.insert("review_subscore".into(),Value::Number(score.into()));}else{m.remove("review_subscore");}
        }
    }

    let structural=|m:&serde_json::Map<String,Value>|m.get("is_create_script").and_then(Value::as_bool).unwrap_or(false)||m.get("is_subcategory").and_then(Value::as_bool).unwrap_or(false);
    let promoted=|m:&serde_json::Map<String,Value>|browse_is_known(m,&known)||browse_is_curated(m);

    let mut structural_values=Vec::new();
    let mut promoted_values=Vec::new();
    let mut ranked_values=Vec::new();
    let mut nix_values=Vec::new();
    for v in values.iter().cloned(){
        let Some(m)=v.as_object()else{continue};
        if structural(m){structural_values.push(v)}
        else if browse_is_nix_distributed(m){nix_values.push(v)}
        else if promoted(m){promoted_values.push(v)}
        else{ranked_values.push(v)}
    }

    structural_values.sort_by(|a,b|{
        let am=a.as_object().unwrap();let bm=b.as_object().unwrap();
        let asub=am.get("is_subcategory").and_then(Value::as_bool).unwrap_or(false);
        let bsub=bm.get("is_subcategory").and_then(Value::as_bool).unwrap_or(false);
        if asub!=bsub{return asub.cmp(&bsub)}
        am.get("name").and_then(Value::as_str).unwrap_or("").to_lowercase().cmp(&bm.get("name").and_then(Value::as_str).unwrap_or("").to_lowercase())
    });
    ranked_values.sort_by(|a,b|{
        let am=a.as_object().unwrap();let bm=b.as_object().unwrap();
        let ar=am.get("review_subscore").and_then(Value::as_i64);
        let br=bm.get("review_subscore").and_then(Value::as_i64);
        match (ar,br){
            (Some(a),Some(b)) if a!=b=>return b.cmp(&a),
            (Some(_),None)=>return std::cmp::Ordering::Less,
            (None,Some(_))=>return std::cmp::Ordering::Greater,
            _=>{}
        }
        let ak=browse_session_key(am);let bk=browse_session_key(bm);
        browse_unit(&ak,"order").total_cmp(&browse_unit(&bk,"order"))
    });
    promoted_values.sort_by(|a,b|{
        let ak=browse_session_key(a.as_object().unwrap());let bk=browse_session_key(b.as_object().unwrap());
        browse_unit(&ak,"promoted-order").total_cmp(&browse_unit(&bk,"promoted-order"))
    });
    nix_values.sort_by(|a,b|{
        let ak=browse_session_key(a.as_object().unwrap());let bk=browse_session_key(b.as_object().unwrap());
        browse_unit(&ak,"nix-category-order").total_cmp(&browse_unit(&bk,"nix-category-order"))
    });

    let total=ranked_values.len()+promoted_values.len();
    let count=promoted_values.len();
    let top_ten=(total+9)/10;
    // Preserve at least one ordinary result between promoted entries whenever
    // possible. If 10% is too small, widen only the promotion window needed.
    let top_slots=top_ten.max(count.saturating_mul(2).saturating_sub(1)).min(total);
    if count>0 {
        let mut placed=0usize;
        for (i,item) in promoted_values.into_iter().enumerate(){
            let left=i*top_slots/count;
            let right=(((i+1)*top_slots)/count).saturating_sub(1).max(left);
            let width=right-left+1;
            let key=browse_session_key(item.as_object().unwrap());
            let jitter=if width>1{(browse_unit(&key,"promoted-jitter")*(width as f64)) as usize}else{0};
            let pos=(left+jitter).min(top_slots.saturating_sub(1))+placed;
            ranked_values.insert(pos.min(ranked_values.len()),item);
            placed+=1;
        }
    }

    structural_values.extend(spread_browse_cohort_rs(ranked_values, nix_values));
    for (dst,src) in values.iter_mut().zip(structural_values){*dst=src;}
}

/// Whether an entry may appear in Featured.
///
/// Catalog sources keep their existing quality gate: only AppStream entries with
/// an ODRS/Snap rating of at least 3.5 stars participate. Nixpkgs has no review
/// feed, so Nix packages participate through the NixOS category distribution
/// instead: only packages mapped from the Nix Software API onto a normal
/// LinuxToys category qualify. The fallback ``nix`` pseudo-category stays out of
/// Featured, exactly like the other source-specific categories.
fn featured_entry_eligible(entry: &RuntimeAppStreamEntry) -> bool {
    if entry.source == "homebrew" {
        return false;
    }
    if entry.source == "nix" {
        return !entry.category.is_empty() && entry.category != "nix";
    }
    entry.review_rating.is_some_and(|rating| rating >= 70.0)
}

#[pyclass]
pub(crate) struct AppStreamCatalog {
    entries: Vec<RuntimeAppStreamEntry>,
    by_category: std::collections::HashMap<String, Vec<usize>>,
    by_id: std::collections::HashMap<String, usize>,
    by_name: std::collections::HashMap<String, usize>,
    by_removable_name: std::collections::HashMap<String, Vec<usize>>,
    by_native_package: std::collections::HashMap<String, Vec<usize>>,
    by_flatpak_package: std::collections::HashMap<String, Vec<usize>>,
    by_snap_package: std::collections::HashMap<String, Vec<usize>>,
    by_homebrew_package: std::collections::HashMap<String, Vec<usize>>,
    by_nix_package: std::collections::HashMap<String, Vec<usize>>,
    cache_key: String,
}

impl AppStreamCatalog {
    fn from_values(entries: Vec<Value>, cache_key: String) -> Self {
        let entries = entries.into_iter().filter_map(RuntimeAppStreamEntry::from_value).collect();
        Self::from_entries(entries, cache_key)
    }

    fn from_entries(entries: Vec<RuntimeAppStreamEntry>, cache_key: String) -> Self {
        let mut by_category: std::collections::HashMap<String, Vec<usize>> = std::collections::HashMap::new();
        let mut by_id = std::collections::HashMap::new();
        let mut by_name = std::collections::HashMap::new();
        let mut by_removable_name: std::collections::HashMap<String, Vec<usize>> = std::collections::HashMap::new();
        let mut by_native_package: std::collections::HashMap<String, Vec<usize>> = std::collections::HashMap::new();
        let mut by_flatpak_package: std::collections::HashMap<String, Vec<usize>> = std::collections::HashMap::new();
        let mut by_snap_package: std::collections::HashMap<String, Vec<usize>> = std::collections::HashMap::new();
        let mut by_homebrew_package: std::collections::HashMap<String, Vec<usize>> = std::collections::HashMap::new();
        let mut by_nix_package: std::collections::HashMap<String, Vec<usize>> = std::collections::HashMap::new();
        for (index, entry) in entries.iter().enumerate() {
            if !entry.category.is_empty() { by_category.entry(entry.category.clone()).or_default().push(index); }
            let id = normalize_id(&entry.appstream_id);
            if !id.is_empty() { by_id.entry(id).or_insert(index); }
            for (name, removable) in [(&entry.name, true), (&entry.canonical_name, false)] {
                let key = name.trim().to_lowercase();
                if !key.is_empty() {
                    by_name.entry(key.clone()).or_insert(index);
                    if removable { by_removable_name.entry(key).or_default().push(index); }
                }
            }
            let target = match entry.source.as_str() {
                "flatpak" => Some(&mut by_flatpak_package),
                "snap" => Some(&mut by_snap_package),
                "homebrew" => Some(&mut by_homebrew_package),
                "native" => Some(&mut by_native_package),
                _ => None,
            };
            if let Some(target) = target {
                for package in &entry.package_names { target.entry(package.clone()).or_default().push(index); }
            }
            for package in &entry.nix_packages {
                by_nix_package.entry(package.clone()).or_default().push(index);
            }
        }
        if let Some(indices) = by_category.get_mut("homebrew") {
            indices.sort_by(|&a, &b| entries[b].homebrew_install_count.cmp(&entries[a].homebrew_install_count)
                .then_with(|| entries[a].name.to_lowercase().cmp(&entries[b].name.to_lowercase())));
        }
        Self { entries, by_category, by_id, by_name, by_removable_name, by_native_package, by_flatpak_package, by_snap_package, by_homebrew_package, by_nix_package, cache_key }
    }

    fn materialize_entry(&self, py: Python<'_>, index: usize) -> PyResult<Option<Py<PyAny>>> {
        let Some(entry) = self.entries.get(index) else { return Ok(None); };
        let Some(value) = entry.decode() else { return Ok(None); };
        Ok(Some(json_to_py(py, &value)?))
    }

    fn materialize_indices(&self, py: Python<'_>, indices: &[usize]) -> PyResult<Vec<Py<PyAny>>> {
        let mut out = Vec::with_capacity(indices.len());
        for &index in indices {
            if let Some(value) = self.materialize_entry(py, index)? { out.push(value); }
        }
        Ok(out)
    }
}

#[pymethods]
impl AppStreamCatalog {
    fn __len__(&self) -> usize { self.entries.len() }

    fn cache_is_current(&self, expected_key: &str) -> bool { self.cache_key == expected_key }

    fn all_entries(&self, py: Python<'_>) -> PyResult<Vec<Py<PyAny>>> {
        let indices: Vec<usize> = (0..self.entries.len()).collect();
        self.materialize_indices(py, &indices)
    }

    fn entries_for_category(&self, py: Python<'_>, category: &str) -> PyResult<Vec<Py<PyAny>>> {
        match self.by_category.get(category.trim_matches('/')) {
            Some(indices) => self.materialize_indices(py, indices),
            None => Ok(Vec::new()),
        }
    }

    fn appimage_entries_for_category(&self, py: Python<'_>, relative: &str, root: &str) -> PyResult<Vec<Py<PyAny>>> {
        // Materialize only the entries under one relative category prefix; the
        // root level materializes the whole pool, so callers should prefer the
        // subcategory accessor for intermediate levels. Categories are stored
        // as absolute paths (the by_category convention) and are relativized
        // against the scripts root here so the tree is machine-independent.
        let relative = relative.trim_matches('/');
        let root = root.trim_matches('/');
        let mut indices = Vec::new();
        for (i, entry) in self.entries.iter().enumerate() {
            if entry.source != "appimage" { continue; }
            let cat = entry.category.trim_matches('/');
            let rel_cat = if root.is_empty() { cat } else { cat.strip_prefix(&format!("{root}/")).unwrap_or(cat) };
            let within = relative.is_empty()
                || rel_cat == relative
                || rel_cat.strip_prefix(&format!("{relative}/")).is_some();
            if within { indices.push(i); }
        }
        self.materialize_indices(py, &indices)
    }

    fn appimage_subcategory_paths(&self, relative: &str, root: &str) -> Vec<String> {
        // Child category paths under one relative prefix, computed from the
        // compact entries: no msgpack decode and no Python conversion, so the
        // sidebar can rebuild the tree cheaply on every refresh.
        let relative = relative.trim_matches('/');
        let root = root.trim_matches('/');
        let mut children: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
        for entry in &self.entries {
            if entry.source != "appimage" { continue; }
            let cat = entry.category.trim_matches('/');
            let rel_cat = if root.is_empty() { cat } else { cat.strip_prefix(&format!("{root}/")).unwrap_or(cat) };
            let rest = if relative.is_empty() {
                Some(rel_cat)
            } else {
                rel_cat.strip_prefix(&format!("{relative}/"))
            };
            if let Some(rest) = rest {
                if let Some(first) = rest.split('/').next() {
                    if !first.is_empty() {
                        children.insert(if relative.is_empty() {
                            first.to_string()
                        } else {
                            format!("{relative}/{first}")
                        });
                    }
                }
            }
        }
        children.into_iter().collect()
    }

    fn category_entry_count(&self, category: &str) -> usize {
        self.by_category.get(category.trim_matches('/')).map_or(0, Vec::len)
    }

    fn category_entry_slice(&self, py: Python<'_>, category: &str, offset: usize, limit: usize) -> PyResult<Vec<Py<PyAny>>> {
        let Some(indices) = self.by_category.get(category.trim_matches('/')) else { return Ok(Vec::new()); };
        let start = offset.min(indices.len());
        let end = start.saturating_add(limit).min(indices.len());
        self.materialize_indices(py, &indices[start..end])
    }

    fn homebrew_filtered_entry_count(&self, excluded: Vec<String>) -> usize {
        let excluded: std::collections::HashSet<String> = excluded
            .into_iter()
            .map(|value| value.trim().to_lowercase())
            .filter(|value| !value.is_empty())
            .collect();
        self.by_category
            .get("homebrew")
            .map_or(0, |indices| {
                indices
                    .iter()
                    .filter(|&&index| {
                        self.entries.get(index).is_some_and(|entry| {
                            !entry.package_names.iter().any(|package| {
                                excluded.contains(&package.trim().to_lowercase())
                            })
                        })
                    })
                    .count()
            })
    }

    fn homebrew_filtered_entry_slice(
        &self,
        py: Python<'_>,
        excluded: Vec<String>,
        offset: usize,
        limit: usize,
    ) -> PyResult<Vec<Py<PyAny>>> {
        let excluded: std::collections::HashSet<String> = excluded
            .into_iter()
            .map(|value| value.trim().to_lowercase())
            .filter(|value| !value.is_empty())
            .collect();
        let Some(indices) = self.by_category.get("homebrew") else {
            return Ok(Vec::new());
        };
        let mut out = Vec::with_capacity(limit);
        let mut skipped = 0usize;
        for &index in indices {
            let Some(entry) = self.entries.get(index) else { continue };
            if entry.package_names.iter().any(|package| {
                excluded.contains(&package.trim().to_lowercase())
            }) {
                continue;
            }
            if skipped < offset {
                skipped += 1;
                continue;
            }
            if out.len() >= limit {
                break;
            }
            if let Some(value) = self.materialize_entry(py, index)? {
                out.push(value);
            }
        }
        Ok(out)
    }

    fn browse_entries_for_category(&self, py: Python<'_>, category: &str, structural: Vec<Py<PyAny>>, known_popular: Vec<String>) -> PyResult<Vec<Py<PyAny>>> {
        let mut values = Vec::with_capacity(structural.len() + self.by_category.get(category.trim_matches('/')).map_or(0, Vec::len));
        for item in structural {
            values.push(py_to_json(item.bind(py))?);
        }
        if let Some(indices) = self.by_category.get(category.trim_matches('/')) {
            for &index in indices {
                if let Some(value) = self.entries.get(index).and_then(RuntimeAppStreamEntry::decode) {
                    if value.get("appstream_source").and_then(Value::as_str) != Some("appimage") { values.push(value); }
                }
            }
        }
        rank_browse_values(&mut values, &known_popular);
        values.iter().map(|value| json_to_py(py, value)).collect()
    }

    fn find_by_id(&self, py: Python<'_>, appstream_id: &str) -> PyResult<Option<Py<PyAny>>> {
        let key = normalize_id(appstream_id);
        match self.by_id.get(&key).copied() {
            Some(index) => self.materialize_entry(py, index),
            None => Ok(None),
        }
    }

    fn find_by_name(&self, py: Python<'_>, name: &str) -> PyResult<Option<Py<PyAny>>> {
        let key = name.trim().to_lowercase();
        match self.by_name.get(&key).copied() {
            Some(index) => self.materialize_entry(py, index),
            None => Ok(None),
        }
    }

    fn find_by_nix_package(&self, py: Python<'_>, attr: &str) -> PyResult<Option<Py<PyAny>>> {
        let key = attr.trim().to_lowercase();
        if key.is_empty() {
            return Ok(None);
        }
        match self.by_nix_package.get(&key).and_then(|indices| indices.first()).copied() {
            Some(index) => self.materialize_entry(py, index),
            None => Ok(None),
        }
    }

    #[pyo3(signature = (query, translated_new, translated_official, source=""))]
    fn search(&self, py: Python<'_>, query: &str, translated_new: &str, translated_official: &str, source: &str) -> PyResult<Vec<(Py<PyAny>, i64)>> {
        let query = query.trim().to_lowercase();
        if query.is_empty() { return Ok(Vec::new()); }
        let translated_new = translated_new.trim().to_lowercase();
        let _translated_official = translated_official.trim().to_lowercase();
        let mut matches = Vec::new();

        for (index, entry) in self.entries.iter().enumerate() {
            if !source.is_empty() && entry.source != source { continue; }
            let name = entry.name.to_lowercase();
            let packages = &entry.search_packages;
            let developer = &entry.developer_lower;
            let mut score = 0i64;
            if (query == "new" || query == translated_new) && entry.is_new { score += 90; }
            if query == name { score += 100; } else if name.starts_with(&query) { score += 80; } else if name.contains(&query) { score += 60; }
            if name == "r" && ("positron".contains(&query) || "rstudio".contains(&query)) { score += 60; }
            if packages.iter().any(|package| package == &query) { score += 90; }
            else if packages.iter().any(|package| package.starts_with(&query)) { score += 70; }
            else if packages.iter().any(|package| package.contains(&query)) { score += 50; }
            if query.as_str() == developer.as_str() { score += 55; } else if developer.starts_with(&query) { score += 45; } else if developer.contains(&query) { score += 40; }
            if entry.description_lower.contains(&query) { score += 30; }
            if score > 0 && name.chars().count() < 20 { score += 5; }
            if score > 0 { matches.push((index, score)); }
        }
        let mut out = Vec::with_capacity(matches.len());
        for (index, score) in matches {
            if let Some(value) = self.materialize_entry(py, index)? { out.push((value, score)); }
        }
        Ok(out)
    }

    fn featured_descriptors(&self, py: Python<'_>) -> PyResult<Vec<Py<PyAny>>> {
        let mut out = Vec::new();
        for (index, entry) in self.entries.iter().enumerate() {
            if !featured_entry_eligible(entry) { continue; }
            let descriptor = serde_json::json!({
                "_appstream_featured_index": index,
                "id": entry.appstream_id,
                "appstream_id": entry.appstream_id,
                "appstream_canonical_name": entry.canonical_name,
                "repo_app_id": entry.appstream_id,
                "name": entry.name,
                "category": entry.category,
                "appstream_source": entry.source,
                "package-name": entry.package_names,
                "review_rating": entry.review_rating,
                "review_subscore": entry.review_subscore,
                "_category_review_score": entry.category_review_score,
                "is_script": true,
                "is_repo_entry": true,
                "is_appstream_entry": true,
                "is_create_script": false,
                "path": format!("appstream://{}/{}", entry.source, entry.appstream_id),
                "repo": "appstream",
            });
            out.push(json_to_py(py, &descriptor)?);
        }
        Ok(out)
    }

    fn materialize_featured(&self, py: Python<'_>, indices: Vec<usize>) -> PyResult<Vec<Py<PyAny>>> {
        self.materialize_indices(py, &indices)
    }

    #[pyo3(signature = (native_packages, flatpak_ids, executed_names, snap_names=Vec::new(), homebrew_names=Vec::new()))]
    fn installed_entries(&self, py: Python<'_>, native_packages: Vec<String>, flatpak_ids: Vec<String>, executed_names: Vec<String>, snap_names: Vec<String>, homebrew_names: Vec<String>) -> PyResult<Vec<Py<PyAny>>> {
        let mut indices = std::collections::HashSet::new();
        for package in native_packages {
            let key = package.trim().to_lowercase();
            if let Some(matches) = self.by_native_package.get(&key) { indices.extend(matches.iter().copied()); }
        }
        for app_id in flatpak_ids {
            let key = app_id.trim().to_lowercase();
            if let Some(matches) = self.by_flatpak_package.get(&key) { indices.extend(matches.iter().copied()); }
        }
        for name in homebrew_names {
            if let Some(matches) = self.by_homebrew_package.get(&name.to_lowercase()) { indices.extend(matches.iter().copied()); }
        }
        for snap_name in snap_names {
            let key = snap_name.trim().to_lowercase();
            if let Some(matches) = self.by_snap_package.get(&key) { indices.extend(matches.iter().copied()); }
        }
        for name in executed_names {
            let key = name.trim().to_lowercase();
            if let Some(matches) = self.by_removable_name.get(&key) { indices.extend(matches.iter().copied()); }
        }
        let mut indices: Vec<usize> = indices.into_iter().collect();
        indices.sort_unstable();
        self.materialize_indices(py, &indices)
    }
}

const RUNTIME_CACHE_SCHEMA: u32 = 20;

#[derive(Serialize, Deserialize)]
struct CachedAppStreamCatalog {
    schema: u32,
    key: String,
    entries: Vec<RuntimeAppStreamEntry>,
}

fn load_binary_catalog_cache(cache_path: &str) -> Option<CachedAppStreamCatalog> {
    if cache_path.is_empty() { return None; }
    let bytes = fs::read(cache_path).ok()?;
    let payload: CachedAppStreamCatalog = rmp_serde::from_slice(&bytes).ok()?;
    (payload.schema == RUNTIME_CACHE_SCHEMA).then_some(payload)
}

fn write_binary_catalog_cache(cache_path: &str, cache_key: &str, entries: &[RuntimeAppStreamEntry]) {
    if cache_path.is_empty() { return; }
    let payload = CachedAppStreamCatalog { schema: RUNTIME_CACHE_SCHEMA, key: cache_key.to_string(), entries: entries.to_vec() };
    let Ok(bytes) = rmp_serde::to_vec_named(&payload) else { return; };
    let path = std::path::Path::new(cache_path);
    if let Some(parent) = path.parent() { if fs::create_dir_all(parent).is_err() { return; } }
    let tmp = path.with_extension(format!("{}.tmp", path.extension().and_then(|value| value.to_str()).unwrap_or("bin")));
    let write_result = (|| -> std::io::Result<()> {
        let mut file = fs::File::create(&tmp)?;
        file.write_all(&bytes)?;
        file.sync_all()?;
        fs::rename(&tmp, path)?;
        Ok(())
    })();
    if write_result.is_err() { let _ = fs::remove_file(tmp); }
}

#[pyfunction]
pub(crate) fn build_appstream_catalog_index(
    py: Python<'_>,
    path: &str,
    omit_keys: Vec<String>,
    category_paths: Vec<String>,
    category_config_json: &str,
    source_preferences_json: &str,
    system_flatpak_locks: Vec<String>,
    host_os_keys: Vec<String>,
    compat_keys: Vec<String>,
    lang: &str,
    curated_ids: Vec<String>,
    curated_packages: Vec<String>,
    curated_names: Vec<String>,
    overlays_json: &str,
    native_badge: &str,
    nix_catalog_path: &str,
    nix_scopes: Vec<String>,
    nix_api_names_json: &str,
    nix_categories_json: &str,
    nixos: bool,
    cache_path: &str,
    cache_key: &str,
    force_rebuild: bool,
) -> PyResult<AppStreamCatalog> {
    py.allow_threads(|| {
    let homebrew_enabled = serde_json::from_str::<Value>(category_config_json).ok()
        .and_then(|v|v.get("homebrew_enabled").and_then(Value::as_bool)).unwrap_or(false);
    let nix_enabled = !nix_scopes.is_empty();
    // A warm cache is immediately usable even when its key is stale.  Normal UI
    // callers keep using that last complete snapshot while the refresh worker
    // rebuilds the new generation with force_rebuild=true.  Publication below is
    // atomic, so readers can only ever observe a complete old or new cache.
    if !force_rebuild {
        if let Some(mut payload) = load_binary_catalog_cache(cache_path) {
            if !homebrew_enabled { payload.entries.retain(|entry|entry.source != "homebrew"); }
            if !nix_enabled { payload.entries.retain(|entry|entry.source != "nix"); }
            return Ok(AppStreamCatalog::from_entries(payload.entries, payload.key));
        }
    } else if let Some(mut payload) = load_binary_catalog_cache(cache_path) {
            if !homebrew_enabled { payload.entries.retain(|entry|entry.source != "homebrew"); }
            if !nix_enabled { payload.entries.retain(|entry|entry.source != "nix"); }
        if payload.key == cache_key {
            return Ok(AppStreamCatalog::from_entries(payload.entries, payload.key));
        }
    }

    let content = match fs::read_to_string(path) { Ok(v) => v, Err(_) => return Ok(AppStreamCatalog::from_values(Vec::new(), cache_key.to_string())) };
    let parsed: Value = match serde_json::from_str(&content) { Ok(v) => v, Err(_) => return Ok(AppStreamCatalog::from_values(Vec::new(), cache_key.to_string())) };
    let Some(values) = parsed.as_array() else { return Ok(AppStreamCatalog::from_values(Vec::new(), cache_key.to_string())); };
    let omit: std::collections::HashSet<String> = omit_keys.into_iter().flat_map(|s| {
        let plain=s.trim().to_lowercase();
        let normalized=normalize_id(&s);
        if plain==normalized { vec![plain] } else { vec![plain,normalized] }
    }).filter(|s|!s.is_empty()).collect();
    let cfg:Value=serde_json::from_str(category_config_json).unwrap_or(Value::Null);
    let overlay_map:Value=serde_json::from_str(overlays_json).unwrap_or_else(|_|serde_json::json!({}));
    let mut vals:Vec<_>=values.iter().filter_map(|value| {
        let m=value.as_object()?;
        m.get("packages").and_then(Value::as_array).is_some_and(|a|!a.is_empty()).then(||m.clone())
    }).collect();

    // Canonicalize Snap identities before applying parser policy. This makes omit,
    // category overrides, source grouping/locks and explicit source preferences see
    // the same AppStream ID as the rest of the catalog while retaining snap_name.
    reconcile_snap_common_ids_rs(&mut vals);
    apply_snap_identity_overlays_rs(&mut vals,&overlay_map);
    // Nixpkgs is optional and host-local: its normalized snapshot is merged only
    // while the subsystem is configured. Components participate in the normal
    // source grouping so matching AppStream entries gain a Nix source option.
    let nix_identities: std::collections::HashMap<String, (String, bool)> =
        serde_json::from_str(nix_api_names_json).unwrap_or_default();
    let nix_categories: std::collections::HashMap<String, String> =
        serde_json::from_str(nix_categories_json).unwrap_or_default();
    vals.extend(crate::nix::nix_components(
        nix_catalog_path,
        &nix_scopes,
        &nix_identities,
        &nix_categories,
        nixos,
    ));
    vals.retain(|m| (m.get("source").and_then(Value::as_str)!=Some("homebrew") || cfg.get("homebrew_enabled").and_then(Value::as_bool).unwrap_or(false)) && !omission_keys_rs(m).iter().any(|k|omit.contains(k)));
    let prefs:Value=serde_json::from_str(source_preferences_json).unwrap_or_else(|_|serde_json::json!({"default":"flatpak","apps":{}}));
    let locks=system_flatpak_locks.into_iter().map(|s|normalize_id(&s)).collect();
    let host_os=host_os_keys.into_iter().map(|s|s.to_lowercase()).collect();
    let compat:std::collections::HashSet<String>=compat_keys.into_iter().map(|s|s.to_lowercase()).collect();
    let prefer_native=compat.iter().any(|s|matches!(s.as_str(),"arch"|"cachy"|"solus"|"fedora"|"nixos"));
    let prefer_nix=compat.iter().any(|s| s.as_str()=="nixos");
    let prefer_nix_gregos=compat.iter().any(|s| s.as_str()=="gregos");
    let steamos=compat.iter().any(|key| matches!(key.as_str(), "steamos"|"dakota"|"gnomeos"|"kde-linux"));
    let suse=compat.iter().any(|key| key.as_str()=="suse");
    let first=collapse_source_groups_rs(vals,&category_paths,&cfg,&prefs,&locks,&host_os,prefer_native,prefer_nix,prefer_nix_gregos,steamos,suse,false);
    let selected=collapse_source_groups_rs(first,&category_paths,&cfg,&prefs,&locks,&host_os,prefer_native,prefer_nix,prefer_nix_gregos,steamos,suse,true);
    let entries=adapt_appstream_maps_values(selected,category_paths,category_config_json,lang,curated_ids,curated_packages,curated_names,overlays_json,native_badge);

    let runtime_entries: Vec<RuntimeAppStreamEntry> = entries.into_iter().filter_map(RuntimeAppStreamEntry::from_value).collect();
    write_binary_catalog_cache(cache_path, cache_key, &runtime_entries);
    Ok(AppStreamCatalog::from_entries(runtime_entries, cache_key.to_string()))
    })
}



/// Hash filesystem metadata for an already-discovered source inventory.
///
/// Python owns source-root discovery/inventory policy. Rust performs the hot warm-start
/// path: stat every remembered file/directory and feed path + mtime + size directly
/// into SHA-256 without constructing thousands of Python tuples or JSON-serializing
/// them first. Missing paths are ignored, matching the previous `_path_state()` loop.
#[pyfunction]
pub(crate) fn source_metadata_fingerprint(paths: Vec<String>) -> String {
    use sha2::{Digest, Sha256};
    use std::os::unix::fs::MetadataExt;

    let mut paths = paths;
    paths.sort_unstable();
    paths.dedup();

    let mut hasher = Sha256::new();
    for path in paths {
        let Ok(metadata) = fs::metadata(&path) else {
            continue;
        };

        let mtime_ns = (metadata.mtime() as i128)
            .saturating_mul(1_000_000_000i128)
            .saturating_add(metadata.mtime_nsec() as i128);

        // Length-prefix the path so concatenated records are unambiguous.
        let bytes = path.as_bytes();
        hasher.update((bytes.len() as u64).to_le_bytes());
        hasher.update(bytes);
        hasher.update(mtime_ns.to_le_bytes());
        hasher.update(metadata.size().to_le_bytes());
    }

    format!("{:x}", hasher.finalize())
}

#[cfg(test)]
mod category_resolution_tests {
    use super::*;

    fn paths() -> Vec<String> {
        [
            "game", "game/action", "game/emu", "sys", "sys/sysadm", "utils", "utils/archive",
            "network", "network/remote", "devs", "devs/txt", "devs/ides",
            "media", "media/players", "creative", "creative/audio",
            "creative/draw", "edu", "edu/tech",
        ]
        .into_iter()
        .map(str::to_string)
        .collect()
    }

    fn config() -> Value {
        serde_json::json!({
            "main": {
                "Game": ["game"],
                "Emulator": ["emu", "game"],
                "Development": ["devs"],
                "Graphics": ["creative"],
                "AudioVideo": ["media"],
                "Network": ["network"],
                "Education": ["edu"],
                "System": ["sysadm"],
                "ConsoleOnly": ["utils"],
                "Utility": ["utils"]
            },
            "additional": {
                "PackageManager": ["sysadm"],
                "FileManager": ["archive"],
                "RemoteAccess": ["remote"],
                "TextEditor": ["txt"]
            },
            "expressions": [
                [["System", "PackageManager"], ["sysadm"]],
                [["Game", "PackageManager"], ["game"]],
                [["System", "FileManager"], ["archive"]],
                [["Game", "ActionGame"], ["action"]],
                [["Game", "Development", "IDE"], ["ides"]],
                [["Graphics", "2DGraphics"], ["draw"]],
                [["Game", "Graphics", "2DGraphics"], ["draw"]],
                [["Network", "RemoteAccess"], ["remote"]],
                [["AudioVideo", "Player"], ["players"]],
                [["AudioVideo", "Audio"], ["audio"]],
                [["Science", "DataVisualization"], ["tech"]]
            ],
            "standalone_priority": ["PackageManager", "RemoteAccess", "TextEditor"],
            "main_priority": [
                "Game", "Emulator", "Development", "AudioVideo", "Network",
                "Education", "System", "ConsoleOnly", "Utility"
            ],
            "generic_main_categories": ["ConsoleOnly", "Utility"]
        })
    }

    fn resolve(categories: &[&str]) -> Option<String> {
        resolve_category_rs(&serde_json::json!(categories), &paths(), &config())
    }

    #[test]
    fn game_main_beats_unrelated_expression_and_purpose_tags() {
        assert_eq!(resolve(&["Game", "Qt", "PackageManager"]), Some("game".into()));
        assert_eq!(resolve(&["Game", "System", "PackageManager"]), Some("game".into()));
        assert_eq!(resolve(&["System", "PackageManager"]), Some("sys/sysadm".into()));
        assert_eq!(resolve(&["Game", "System", "FileManager"]), Some("game".into()));
        assert_eq!(resolve(&["System", "FileManager"]), Some("utils/archive".into()));
    }

    #[test]
    fn generic_main_and_missing_main_still_use_standalone_purpose_tags() {
        assert_eq!(resolve(&["Utility", "PackageManager"]), Some("sys/sysadm".into()));
        assert_eq!(resolve(&["PackageManager"]), Some("sys/sysadm".into()));
    }

    #[test]
    fn expressions_refine_the_preferred_main_without_crossing_domains() {
        assert_eq!(resolve(&["Game", "ActionGame"]), Some("game/action".into()));
        assert_eq!(resolve(&["Game", "Development", "IDE"]), Some("devs/ides".into()));
        assert_eq!(resolve(&["Game", "Graphics", "2DGraphics"]), Some("creative/draw".into()));
        assert_eq!(resolve(&["Game", "Network", "RemoteAccess"]), Some("game".into()));
        assert_eq!(resolve(&["AudioVideo", "Player"]), Some("media/players".into()));
        assert_eq!(resolve(&["AudioVideo", "Audio"]), Some("creative/audio".into()));
        assert_eq!(resolve(&["Education", "Science", "DataVisualization"]), Some("edu/tech".into()));
    }

    #[test]
    fn standalone_tags_can_refine_a_main_category_path() {
        assert_eq!(resolve(&["Development", "TextEditor"]), Some("devs/txt".into()));
    }

    #[test]
    fn console_only_is_a_generic_utility_category_not_a_game() {
        assert_eq!(resolve(&["ConsoleOnly"]), Some("utils".into()));
        assert_eq!(resolve(&["Game", "ConsoleOnly"]), Some("game".into()));
    }

    #[test]
    fn nix_components_use_the_mapped_category_hint() {
        let mut component = serde_json::json!({
            "id": "nix:firefox", "name": "firefox", "summary": "Web browser",
            "packages": ["firefox"], "categories": [], "source": "nix",
            "nix_category": "devs"
        })
        .as_object()
        .unwrap()
        .clone();
        assert_eq!(
            resolve_component_category_rs(&component, &paths(), &config()),
            Some("devs".into())
        );
        component.insert("nix_category".into(), Value::String("missing".into()));
        assert_eq!(
            resolve_component_category_rs(&component, &paths(), &config()),
            Some("nix".into())
        );
        component.remove("nix_category");
        assert_eq!(
            resolve_component_category_rs(&component, &paths(), &config()),
            Some("nix".into())
        );
        // A merged Nix card can carry the group's AppStream categories while
        // keeping its Nix install identity.
        component.insert("categories".into(), serde_json::json!(["AudioVideo"]));
        assert_eq!(
            resolve_component_category_rs(&component, &paths(), &config()),
            Some("media".into())
        );
    }

    #[test]
    fn nix_entries_are_spread_evenly_through_a_category() {
        let mut values = Vec::new();
        for index in 0..12 {
            values.push(serde_json::json!({
                "id": format!("org.example.App{index}"),
                "name": format!("App {index}"),
                "category": "utils",
                "appstream_source": "flatpak",
                "is_appstream_entry": true,
                "review_rating": 90.0,
                "review_count": 10 + index,
            }));
        }
        for index in 0..4 {
            values.push(serde_json::json!({
                "id": format!("nix:nix-app-{index}"),
                "name": format!("nix-app-{index}"),
                "category": "utils",
                "appstream_source": "nix",
                "is_appstream_entry": true,
            }));
        }
        rank_browse_values(&mut values, &[]);
        let positions: Vec<usize> = values
            .iter()
            .enumerate()
            .filter(|(_, value)| value.get("appstream_source").and_then(Value::as_str) == Some("nix"))
            .map(|(index, _)| index)
            .collect();
        assert_eq!(positions.len(), 4, "{values:?}");
        // Four cohort slots over sixteen rows must start in the first quarter
        // and finish in the last quarter, rather than stacking at the bottom.
        assert!(positions[0] < values.len() / 4, "{positions:?}");
        assert!(
            positions[3] >= values.len() * 3 / 4,
            "{positions:?}"
        );
    }
}

#[cfg(test)]
mod appimage_source_tests {
    use super::*;

    fn component(id: &str, name: &str, source: &str, categories: &[&str]) -> serde_json::Map<String, Value> {
        serde_json::json!({
            "id": id, "name": name, "summary": format!("{} summary", name),
            "packages": [name], "categories": categories, "source": source
        })
        .as_object()
        .unwrap()
        .clone()
    }

    fn flatpak_component(id: &str, remote: &str, scope: &str, installation: &str) -> serde_json::Map<String, Value> {
        serde_json::json!({
            "id": id, "name": "App", "summary": "App summary",
            "packages": [id], "categories": ["Utility"], "source": "flatpak",
            "origin": remote, "verified": false,
            "flatpak_remote": remote, "flatpak_scope": scope,
            "flatpak_installation": installation
        })
        .as_object()
        .unwrap()
        .clone()
    }

    fn collapse(entries: Vec<serde_json::Map<String, Value>>, prefs: Value) -> Vec<serde_json::Map<String, Value>> {
        let paths: Vec<String> = vec!["/scripts/creative/audio".into(), "/scripts/devs".into()];
        let cfg = serde_json::json!({"main": {"Game": ("game",)}, "additional": {}});
        let locks: std::collections::HashSet<String> = Default::default();
        let host_os: std::collections::HashSet<String> = Default::default();
        let first = collapse_source_groups_rs(entries, &paths, &cfg, &prefs, &locks, &host_os, false, false, false, false, false, false);
        collapse_source_groups_rs(first, &paths, &cfg, &prefs, &locks, &host_os, false, false, false, false, false, true)
    }

    fn collapse_with_source_policy(
        entries: Vec<serde_json::Map<String, Value>>,
        prefs: Value,
        prefer_native: bool,
        prefer_nix: bool,
    ) -> Vec<serde_json::Map<String, Value>> {
        let paths: Vec<String> = vec!["/scripts/utility".into()];
        let cfg = serde_json::json!({"main": {"Utility": ("utils",)}, "additional": {}});
        let locks: std::collections::HashSet<String> = Default::default();
        let host_os: std::collections::HashSet<String> = Default::default();
        let first = collapse_source_groups_rs(entries, &paths, &cfg, &prefs, &locks, &host_os, prefer_native, prefer_nix, false, false, false, false);
        collapse_source_groups_rs(first, &paths, &cfg, &prefs, &locks, &host_os, prefer_native, prefer_nix, false, false, false, true)
    }

    fn nix_named_component(name: &str, attr: &str, scope: &str) -> serde_json::Map<String, Value> {
        serde_json::json!({
            "id": format!("nix:{attr}"), "name": name,
            "summary": format!("Nix {attr}"), "packages": [attr],
            "categories": [], "source": "nix", "nix_name": attr,
            "nix_pname": attr, "nix_api_name": name, "nix_scope": scope
        })
        .as_object()
        .unwrap()
        .clone()
    }

    fn raw_nix_component(attr: &str, description: &str, scope: &str) -> serde_json::Map<String, Value> {
        serde_json::json!({
            "id": format!("nix:{attr}"), "name": attr,
            "summary": description,
            "description_blocks": [{"type": "paragraph", "spans": [{"text": description}]}],
            "packages": [attr], "categories": [], "source": "nix",
            "nix_name": attr, "nix_pname": attr, "nix_api_name": "",
            "nix_scope": scope
        })
        .as_object()
        .unwrap()
        .clone()
    }

    fn brave_flatpak() -> serde_json::Map<String, Value> {
        serde_json::json!({
            "id": "com.brave.Browser", "name": "Brave",
            "summary": "Privacy-focused web browser",
            "description_blocks": [{"type": "paragraph", "spans": [{
                "text": "Brave blocks ads and trackers to protect your privacy while browsing."
            }]}],
            "packages": ["com.brave.Browser"],
            "categories": ["Network", "WebBrowser"], "source": "flatpak",
            "origin": "flathub", "flatpak_remote": "flathub",
            "flatpak_scope": "system", "flatpak_installation": "default",
            "verified": true, "developer": "Brave Software",
            "homepage": "https://brave.com", "license": "MPL-2.0",
            "icon": "https://example.invalid/brave.png",
            "screenshots": [{"images": [{"url": "https://example.invalid/brave-shot.png", "width": 1280, "height": 720}]}]
        })
        .as_object()
        .unwrap()
        .clone()
    }

    fn collapse_for_gregos(
        entries: Vec<serde_json::Map<String, Value>>,
        prefs: Value,
        prefer_nix_gregos: bool,
    ) -> Vec<serde_json::Map<String, Value>> {
        let paths: Vec<String> = vec![
            "/scripts/game".into(),
            "/scripts/devs".into(),
            "/scripts/devs/ides".into(),
            "/scripts/devs/tools".into(),
            "/scripts/devs/txt".into(),
            "/scripts/network".into(),
            "/scripts/network/browsers".into(),
            "/scripts/utils".into(),
        ];
        let cfg = serde_json::json!({
            "main": {"Game": ("game",), "Development": ("devs",), "Network": ("network",), "Utility": ("utils",)},
            "main_priority": ["Game", "Development", "Network", "Utility"],
            "additional": {"IDE": ("ides",), "Tool": ("tools",), "TextEditor": ("txt",), "WebBrowser": ("browsers",)},
            "standalone_priority": ["IDE", "Tool", "TextEditor", "WebBrowser"]
        });
        let locks: std::collections::HashSet<String> = Default::default();
        let host_os: std::collections::HashSet<String> = Default::default();
        let first = collapse_source_groups_rs(entries, &paths, &cfg, &prefs, &locks, &host_os, false, false, prefer_nix_gregos, false, false, false);
        collapse_source_groups_rs(first, &paths, &cfg, &prefs, &locks, &host_os, false, false, prefer_nix_gregos, false, false, true)
    }

    #[test]
    fn appimage_source_preference_is_honored() {
        let entries = vec![
            component("org.distro.App", "App", "native", &["Utility"]),
            component("appimage.community.app", "App", "appimage", &["Utility"]),
        ];
        // Explicit per-app preference for the AppImage source.
        let prefs = serde_json::json!({"default": "flatpak", "apps": {"app": {"all": "appimage"}}});
        let selected = collapse(entries.clone(), prefs);
        assert_eq!(selected.len(), 1);
        assert_eq!(selected[0]["source"], "appimage");
        // The unselected source stays reachable through source options.
        assert!(selected[0].get("_source_alternatives").is_some());
    }

    #[test]
    fn appimage_only_groups_pass_through_without_options() {
        let entries = vec![
            component("appimage.community.app", "App", "appimage", &["Utility"]),
        ];
        let prefs = serde_json::json!({"default": "flatpak", "apps": {}});
        let selected = collapse(entries, prefs);
        assert_eq!(selected.len(), 1);
        assert_eq!(selected[0]["source"], "appimage");
        assert!(selected[0].get("_source_alternatives").is_none());
    }

    fn nix_component(scope: &str) -> serde_json::Map<String, Value> {
        serde_json::json!({
            "id": format!("nix:app-{scope}"),
            "name": "App",
            "summary": "App summary",
            "packages": ["app"],
            "categories": ["Utility"],
            "source": "nix",
            "nix_name": "app",
            "nix_api_name": "app",
            "nix_scope": scope,
            "nix_scopes": [scope]
        })
        .as_object()
        .unwrap()
        .clone()
    }

    #[test]
    fn nixos_prefers_the_nix_package_over_verified_flatpak() {
        let mut flatpak = flatpak_component("org.distro.App", "flathub", "user", "user");
        flatpak.insert("verified".into(), Value::Bool(true));
        let entries = vec![
            component("org.distro.App", "App", "native", &["Utility"]),
            flatpak,
            nix_component("system"),
        ];
        let prefs = serde_json::json!({"default": "flatpak", "apps": {}});
        let selected = collapse_with_source_policy(entries, prefs, true, true);
        assert_eq!(selected.len(), 1, "{selected:?}");
        assert_eq!(selected[0]["source"], "nix");
        assert_eq!(selected[0]["nix_scope"], "system");
        assert_eq!(
            selected[0].get("_source_recommended").and_then(Value::as_str),
            Some("nix:system")
        );
    }

    #[test]
    fn nixos_prefers_nix_over_category_native_policy() {
        let entries = vec![
            component("org.example.IDE", "IDE", "native", &["Development", "IDE"]),
            nix_named_component("IDE", "ide-app", "system"),
        ];
        let paths: Vec<String> = vec!["/scripts/devs".into(), "/scripts/devs/ides".into()];
        let cfg = serde_json::json!({
            "main": {"Development": ("devs",)},
            "main_priority": ["Development"],
            "additional": {"IDE": ("ides",)},
            "standalone_priority": ["IDE"]
        });
        let prefs = serde_json::json!({"default": "flatpak", "apps": {}});
        let locks: std::collections::HashSet<String> = Default::default();
        let host_os: std::collections::HashSet<String> = Default::default();
        let first = collapse_source_groups_rs(entries, &paths, &cfg, &prefs, &locks, &host_os, true, true, false, false, false, false);
        let selected = collapse_source_groups_rs(first, &paths, &cfg, &prefs, &locks, &host_os, true, true, false, false, false, true);
        assert_eq!(selected.len(), 1, "{selected:?}");
        assert_eq!(selected[0]["source"], "nix");
    }

    #[test]
    fn nix_preference_does_not_apply_without_nixos() {
        let entries = vec![
            component("org.distro.App", "App", "native", &["Utility"]),
            nix_component("home-manager"),
        ];
        let prefs = serde_json::json!({"default": "flatpak", "apps": {}});
        let selected = collapse_with_source_policy(entries, prefs, false, false);
        assert_eq!(selected.len(), 1, "{selected:?}");
        assert_eq!(selected[0]["source"], "native");
    }

    #[test]
    fn appimage_name_variants_attach_to_the_standard_entry_as_distinct_options() {
        let entries = vec![
            component("org.freecad.FreeCAD", "FreeCAD", "native", &["Utility"]),
            component("appimage.community.freecad-2", "FreeCAD 2", "appimage", &["Utility"]),
            component("appimage.community.freecad2", "FreeCAD2", "appimage", &["Utility"]),
            component("appimage.community.freecad-asm3", "FreeCAD-asm3", "appimage", &["Utility"]),
            component("org.prismlauncher.PrismLauncher", "Prism Launcher", "native", &["Utility"]),
            component("appimage.community.prismlauncher", "prismlauncher", "appimage", &["Utility"]),
        ];
        let prefs = serde_json::json!({"default": "flatpak", "apps": {}});
        let selected = collapse(entries, prefs);

        assert_eq!(selected.len(), 2, "{selected:?}");
        let freecad = selected.iter().find(|entry|entry.get("id").and_then(Value::as_str)==Some("org.freecad.FreeCAD")).unwrap();
        let freecad_options=freecad.get("_source_alternatives").and_then(Value::as_array).unwrap();
        assert_eq!(freecad_options.len(),3,"{freecad_options:?}");
        let freecad_keys:std::collections::HashSet<String>=freecad_options.iter()
            .filter_map(Value::as_object)
            .map(source_option_key_rs)
            .collect();
        assert_eq!(freecad_keys.len(),3,"{freecad_keys:?}");

        let prism = selected.iter().find(|entry|entry.get("id").and_then(Value::as_str)==Some("org.prismlauncher.PrismLauncher")).unwrap();
        assert_eq!(prism.get("_source_alternatives").and_then(Value::as_array).unwrap().len(),1);
    }

    #[test]
    fn same_name_unrelated_applications_do_not_merge() {
        let entries = vec![
            serde_json::json!({
                "id": "org.cutwire.Prism", "name": "Prism",
                "summary": "Trigger and mix live visuals",
                "description_blocks": [{"type": "paragraph", "spans": [{
                    "text": "Prism is a beginner-friendly live visuals app for triggering clips and compositing overlays in real time."
                }]}],
                "packages": ["org.cutwire.Prism"], "categories": ["AudioVideo"],
                "source": "flatpak", "origin": "flathub", "flatpak_remote": "flathub",
                "flatpak_scope": "system", "flatpak_installation": "default",
                "developer": "CutWire Studios", "verified": true
            })
            .as_object()
            .unwrap()
            .clone(),
            serde_json::json!({
                "id": "org.prismlauncher.PrismLauncher", "name": "Prism Launcher",
                "summary": "Custom Minecraft Launcher to easily manage multiple Minecraft installations at once",
                "description_blocks": [{"type": "paragraph", "spans": [{
                    "text": "Prism Launcher is a custom launcher for Minecraft that focuses on predictability, long term stability and simplicity."
                }]}],
                "packages": ["org.prismlauncher.PrismLauncher"], "categories": ["Game"],
                "source": "flatpak", "origin": "flathub", "flatpak_remote": "flathub",
                "flatpak_scope": "system", "flatpak_installation": "default",
                "developer": "Prism Launcher Contributors", "verified": true
            })
            .as_object()
            .unwrap()
            .clone(),
            serde_json::json!({
                "id": "appimage.community.prismlauncher", "name": "prismlauncher",
                "summary": "A custom launcher for Minecraft that allows you to easily manage multiple installations of Minecraft at once.",
                "packages": ["prismlauncher"], "categories": ["Game"],
                "source": "appimage", "origin": "appimage-community",
                "developer": "PrismLauncher"
            })
            .as_object()
            .unwrap()
            .clone(),
            serde_json::json!({
                "id": "io.github.Boof2015.Prism", "name": "Prism",
                "summary": "Real-time audio analysis and metering",
                "description_blocks": [{"type": "paragraph", "spans": [{
                    "text": "Prism is an audio analyzer and meter rack for scopes, loudness metering and capture."
                }]}],
                "packages": ["io.github.Boof2015.Prism"], "categories": ["AudioVideo"],
                "source": "flatpak", "origin": "flatpark", "flatpak_remote": "flatpark",
                "flatpak_scope": "system", "flatpak_installation": "default",
                "developer": "Boof2015", "verified": false
            })
            .as_object()
            .unwrap()
            .clone(),
            serde_json::json!({
                "id": "appimage.community.prism", "name": "Prism",
                "summary": "Every model.",
                "description_blocks": [{"type": "paragraph", "spans": [{
                    "text": "A cross-platform AI desktop chat client for any provider."
                }]}],
                "packages": ["Prism"], "categories": ["Utility"],
                "source": "appimage", "origin": "appimage-community",
                "developer": "IterationLabz"
            })
            .as_object()
            .unwrap()
            .clone(),
        ];
        let selected = collapse(entries, serde_json::json!({"default": "flatpak", "apps": {}}));
        assert_eq!(selected.len(), 4, "{selected:?}");

        let boof = selected
            .iter()
            .find(|entry| entry.get("id").and_then(Value::as_str) == Some("io.github.Boof2015.Prism"))
            .expect("Boof2015 Prism entry");
        assert!(boof.get("_source_alternatives").is_none(), "{boof:?}");

        let chat = selected
            .iter()
            .find(|entry| entry.get("id").and_then(Value::as_str) == Some("appimage.community.prism"))
            .expect("IterationLabz Prism entry");
        assert!(chat.get("_source_alternatives").is_none(), "{chat:?}");

        let cutwire = selected
            .iter()
            .find(|entry| entry.get("id").and_then(Value::as_str) == Some("org.cutwire.Prism"))
            .expect("CutWire Prism entry");
        assert!(
            cutwire.get("_source_alternatives").is_none(),
            "{cutwire:?}"
        );

        let prism = selected
            .iter()
            .find(|entry| {
                entry.get("id").and_then(Value::as_str)
                    == Some("org.prismlauncher.PrismLauncher")
            })
            .expect("Prism Launcher entry");
        let options = prism
            .get("_source_alternatives")
            .and_then(Value::as_array)
            .expect("Prism Launcher AppImage option");
        assert_eq!(options.len(), 1, "{options:?}");
        assert_eq!(
            options[0].get("id").and_then(Value::as_str),
            Some("appimage.community.prismlauncher")
        );
    }

    #[test]
    fn explicit_appimage_preference_selects_one_variant_and_keeps_the_rest_available() {
        let entries = vec![
            component("org.freecad.FreeCAD", "FreeCAD", "native", &["Utility"]),
            component("appimage.community.freecad2", "FreeCAD2", "appimage", &["Utility"]),
            component("appimage.community.freecad-asm3", "FreeCAD-asm3", "appimage", &["Utility"]),
        ];
        let prefs = serde_json::json!({
            "default": "flatpak",
            "apps": {"org.freecad.FreeCAD": "appimage"}
        });
        let selected = collapse(entries, prefs);

        assert_eq!(selected.len(),1,"{selected:?}");
        assert_eq!(selected[0]["source"],"appimage");
        assert_eq!(selected[0].get("_source_alternatives").and_then(Value::as_array).unwrap().len(),2);
    }

    #[test]
    fn unmatched_appimages_remain_separate_entries() {
        let entries = vec![
            component("org.freecad.FreeCAD", "FreeCAD", "native", &["Utility"]),
            component("appimage.community.freecad-tools", "FreeCAD Tools", "appimage", &["Utility"]),
            component("appimage.community.freecad-viewer", "FreeCAD Viewer", "appimage", &["Utility"]),
        ];
        let selected = collapse(entries, serde_json::json!({"default": "flatpak", "apps": {}}));
        assert_eq!(selected.len(),3,"{selected:?}");
        assert!(selected.iter().all(|entry|entry.get("_source_alternatives").is_none()));
    }

    #[test]
    fn nix_entries_merge_by_normalized_name() {
        let entries = vec![
            component("org.example.AddWater", "Add Water", "native", &["Utility"]),
            serde_json::json!({
                "id":"nix:addwater", "name":"Add Water", "summary":"Nix addwater",
                "packages":["addwater"], "categories":[], "source":"nix",
                "nix_name":"addwater", "nix_pname":"addwater", "nix_api_name":"Add Water",
                "nix_scope":"home-manager"
            }).as_object().unwrap().clone(),
            serde_json::json!({
                "id":"nix:addwater", "name":"Add Water", "summary":"Nix addwater",
                "packages":["addwater"], "categories":[], "source":"nix",
                "nix_name":"addwater", "nix_pname":"addwater", "nix_api_name":"Add Water",
                "nix_scope":"system"
            }).as_object().unwrap().clone(),
        ];
        let selected = collapse(entries, serde_json::json!({"default": "flatpak", "apps": {}}));
        assert_eq!(selected.len(), 1, "{selected:?}");
        assert_eq!(selected[0].get("source").and_then(Value::as_str), Some("native"));
        let options = selected[0]
            .get("_source_alternatives")
            .and_then(Value::as_array)
            .unwrap();
        let keys: std::collections::HashSet<String> =
            options.iter().filter_map(Value::as_object).map(source_option_key_rs).collect();
        assert_eq!(keys.len(), 2, "{keys:?}");
        assert!(keys.contains("nix:home-manager"));
        assert!(keys.contains("nix:system"));
    }

    #[test]
    fn nix_entries_merge_with_appstream_id_when_display_name_is_shortened() {
        let entries = vec![
            serde_json::json!({
                "id":"io.github.Faugus.faugus-launcher", "name":"Faugus",
                "summary":"Faugus summary", "packages":["io.github.Faugus.faugus-launcher"],
                "categories":["Game"], "source":"flatpak", "origin":"flathub",
                "flatpak_remote":"flathub", "flatpak_scope":"user",
                "flatpak_installation":"default", "verified":true
            }).as_object().unwrap().clone(),
            serde_json::json!({
                "id":"nix:faugus-launcher", "name":"Faugus Launcher",
                "summary":"Nix faugus-launcher", "packages":["faugus-launcher"],
                "categories":[], "source":"nix", "nix_name":"faugus-launcher",
                "nix_pname":"faugus-launcher", "nix_api_name":"Faugus Launcher",
                "nix_scope":"home-manager"
            }).as_object().unwrap().clone(),
        ];
        let selected = collapse(entries, serde_json::json!({"default": "flatpak", "apps": {}}));
        assert_eq!(selected.len(), 1, "{selected:?}");
        assert_eq!(
            selected[0].get("source").and_then(Value::as_str),
            Some("flatpak")
        );
        let options = selected[0]
            .get("_source_alternatives")
            .and_then(Value::as_array)
            .unwrap();
        let keys: std::collections::HashSet<String> =
            options.iter().filter_map(Value::as_object).map(source_option_key_rs).collect();
        assert_eq!(keys.len(), 1, "{keys:?}");
        assert!(keys.contains("nix:home-manager"));
    }

    #[test]
    fn catalog_sources_merge_generic_name_variants_without_crossing_variants() {
        let entries = vec![
            serde_json::json!({
                "id":"org.chromium.Chromium", "name":"Chromium Web Browser",
                "summary":"The web browser from Chromium project",
                "packages":["org.chromium.Chromium"], "categories":["Network","WebBrowser"],
                "source":"flatpak", "origin":"flathub", "flatpak_remote":"flathub",
                "flatpak_scope":"system", "flatpak_installation":"default", "verified":false
            }).as_object().unwrap().clone(),
            serde_json::json!({
                "id":"chromium-browser.desktop", "name":"chromium",
                "summary":"Chromium web browser", "packages":["chromium"],
                "categories":["Office"], "source":"snap", "origin":"snapcraft",
                "snap_name":"chromium", "snap_common_ids":["chromium-browser.desktop"]
            }).as_object().unwrap().clone(),
            nix_named_component("Chromium", "chromium", "system"),
            serde_json::json!({
                "id":"io.github.ungoogled_software.ungoogled_chromium",
                "name":"Ungoogled Chromium", "summary":"Chromium without Google",
                "packages":["io.github.ungoogled_software.ungoogled_chromium"],
                "categories":["Network","WebBrowser"], "source":"flatpak",
                "origin":"flathub", "flatpak_remote":"flathub",
                "flatpak_scope":"system", "flatpak_installation":"default", "verified":false
            }).as_object().unwrap().clone(),
            nix_named_component("Ungoogled Chromium", "ungoogled-chromium", "system"),
        ];
        let selected = collapse_for_gregos(
            entries,
            serde_json::json!({"default": "flatpak", "apps": {}}),
            false,
        );
        assert_eq!(selected.len(), 2, "{selected:?}");
        let chromium = selected.iter()
            .find(|entry| entry.get("id").and_then(Value::as_str) == Some("org.chromium.Chromium"))
            .expect("Chromium group");
        let chromium_sources: std::collections::HashSet<String> =
            std::iter::once(source_option_key_rs(chromium))
                .chain(
                    chromium.get("_source_alternatives")
                        .and_then(Value::as_array)
                        .into_iter()
                        .flatten()
                        .filter_map(Value::as_object)
                        .map(source_option_key_rs),
                )
                .collect();
        assert_eq!(chromium_sources.len(), 3, "{chromium_sources:?}");
        assert!(chromium_sources.contains("flatpak:system:default:flathub"));
        assert!(chromium_sources.contains("snap"));
        assert!(chromium_sources.contains("nix:system"));
        let ungoogled = selected.iter()
            .find(|entry| entry.get("name").and_then(Value::as_str) == Some("Ungoogled Chromium"))
            .expect("Ungoogled Chromium group");
        assert_ne!(
            ungoogled.get("id").and_then(Value::as_str),
            chromium.get("id").and_then(Value::as_str)
        );
    }

    #[test]
    fn gregos_prefers_nix_for_browsers() {
        let entries = vec![
            serde_json::json!({
                "id":"org.chromium.Chromium", "name":"Chromium Web Browser",
                "summary":"The web browser from Chromium project",
                "packages":["org.chromium.Chromium"], "categories":["Network","WebBrowser"],
                "source":"flatpak", "origin":"flathub", "flatpak_remote":"flathub",
                "flatpak_scope":"system", "flatpak_installation":"default", "verified":true
            }).as_object().unwrap().clone(),
            nix_named_component("Chromium", "chromium", "home-manager"),
        ];
        let selected = collapse_for_gregos(
            entries,
            serde_json::json!({"default": "flatpak", "apps": {}}),
            true,
        );
        assert_eq!(selected.len(), 1, "{selected:?}");
        assert_eq!(selected[0].get("source").and_then(Value::as_str), Some("nix"));
        assert_eq!(
            selected[0].get("nix_category").and_then(Value::as_str),
            Some("scripts/network/browsers")
        );
    }

    #[test]
    fn source_icon_falls_back_to_an_alternate_source() {
        let entries = vec![
            serde_json::json!({
                "id":"org.example.App", "name":"App", "summary":"App summary",
                "packages":["org.example.App"], "categories":["Utility"],
                "source":"flatpak", "origin":"flathub", "flatpak_remote":"flathub",
                "flatpak_scope":"system", "flatpak_installation":"default",
                "icon":"application-x-executable"
            }).as_object().unwrap().clone(),
            serde_json::json!({
                "id":"io.snapcraft.app", "name":"App", "summary":"App summary",
                "packages":["app"], "categories":["Utility"], "source":"snap",
                "origin":"snapcraft", "snap_name":"app",
                "icon":"https://example.invalid/app.png"
            }).as_object().unwrap().clone(),
        ];
        let selected = collapse(entries, serde_json::json!({"default": "flatpak", "apps": {}}));
        assert_eq!(selected.len(), 1, "{selected:?}");
        assert_eq!(selected[0].get("source").and_then(Value::as_str), Some("flatpak"));
        assert_eq!(
            selected[0].get("icon").and_then(Value::as_str),
            Some("https://example.invalid/app.png")
        );
    }

    #[test]
    fn source_icon_falls_back_from_a_generic_nix_icon() {
        let entries = vec![
            serde_json::json!({
                "id":"org.example.App", "name":"App", "summary":"App summary",
                "packages":["org.example.App"], "categories":["Game"],
                "source":"flatpak", "origin":"flathub", "flatpak_remote":"flathub",
                "flatpak_scope":"system", "flatpak_installation":"default",
                "icon":"https://example.invalid/app.png"
            }).as_object().unwrap().clone(),
            {
                let mut nix = nix_named_component("App", "app", "home-manager");
                nix.insert("icon".into(), Value::String("nix.svg".into()));
                nix
            },
        ];
        let selected = collapse_for_gregos(
            entries,
            serde_json::json!({"default": "flatpak", "apps": {}}),
            true,
        );
        assert_eq!(selected.len(), 1, "{selected:?}");
        assert_eq!(selected[0].get("source").and_then(Value::as_str), Some("nix"));
        assert_eq!(
            selected[0].get("icon").and_then(Value::as_str),
            Some("https://example.invalid/app.png")
        );
    }

    #[test]
    fn nix_adaptation_keeps_a_fallback_icon() {
        let paths: Vec<String> = vec!["/scripts/utils".into()];
        let cfg = serde_json::json!({
            "main": {"Utility": ("utils",)},
            "main_priority": ["Utility"],
            "additional": {}
        })
        .to_string();
        let mut fallback = nix_named_component("App", "app", "home-manager");
        fallback.insert(
            "icon".into(),
            Value::String("https://example.invalid/app.png".into()),
        );
        let values = adapt_appstream_maps_values(
            vec![fallback],
            paths.clone(),
            &cfg,
            "en",
            vec![],
            vec![],
            vec![],
            "{}",
            "",
        );
        assert_eq!(
            values[0].get("icon").and_then(Value::as_str),
            Some("https://example.invalid/app.png")
        );

        let mut generic = nix_named_component("Other", "other", "home-manager");
        generic.insert("icon".into(), Value::String("nix.svg".into()));
        let values = adapt_appstream_maps_values(
            vec![generic],
            paths,
            &cfg,
            "en",
            vec![],
            vec![],
            vec![],
            "{}",
            "",
        );
        assert_eq!(
            values[0].get("icon").and_then(Value::as_str),
            Some("nix.svg")
        );
    }

    #[test]
    fn gregos_prefers_nix_for_game_entries_only() {
        let game_entries = vec![
            component("org.example.Game", "Game", "native", &["Game"]),
            serde_json::json!({
                "id":"nix:game", "name":"Game", "summary":"Nix game",
                "packages":["game"], "categories":[], "source":"nix",
                "nix_name":"game", "nix_pname":"game", "nix_api_name":"Game",
                "nix_scope":"home-manager"
            }).as_object().unwrap().clone(),
        ];
        let selected = collapse_for_gregos(
            game_entries,
            serde_json::json!({"default": "flatpak", "apps": {}}),
            true,
        );
        assert_eq!(selected.len(), 1, "{selected:?}");
        assert_eq!(selected[0].get("source").and_then(Value::as_str), Some("nix"));
        assert_eq!(
            selected[0].get("nix_category").and_then(Value::as_str),
            Some("scripts/game")
        );

        let utility_entries = vec![
            flatpak_component("org.example.Tool", "flathub", "user", "default"),
            serde_json::json!({
                "id":"nix:app", "name":"App", "summary":"Nix app",
                "packages":["app"], "categories":[], "source":"nix",
                "nix_name":"app", "nix_pname":"app", "nix_api_name":"App",
                "nix_scope":"home-manager"
            }).as_object().unwrap().clone(),
        ];
        let selected = collapse_for_gregos(
            utility_entries,
            serde_json::json!({"default": "flatpak", "apps": {}}),
            true,
        );
        assert_eq!(selected.len(), 1, "{selected:?}");
        assert_eq!(
            selected[0].get("source").and_then(Value::as_str),
            Some("flatpak")
        );
    }

    #[test]
    fn gregos_prefers_nix_for_devs_ides_and_txt_entries() {
        let entries = vec![
            component("org.example.DevTool", "Dev Tool", "flatpak", &["Development"]),
            nix_named_component("Dev Tool", "dev-tool", "home-manager"),
            component(
                "org.example.TextEditor",
                "Text Editor",
                "flatpak",
                &["Development", "TextEditor"],
            ),
            nix_named_component("Text Editor", "text-editor", "home-manager"),
            component(
                "org.example.IDE",
                "IDE",
                "flatpak",
                &["Development", "IDE"],
            ),
            nix_named_component("IDE", "ide", "home-manager"),
            component(
                "org.example.DevUtility",
                "Dev Utility",
                "flatpak",
                &["Development", "Tool"],
            ),
            nix_named_component("Dev Utility", "dev-utility", "home-manager"),
        ];
        let selected = collapse_for_gregos(
            entries,
            serde_json::json!({"default": "flatpak", "apps": {}}),
            true,
        );
        assert_eq!(selected.len(), 4, "{selected:?}");
        let by_name: std::collections::HashMap<&str, &serde_json::Map<String, Value>> =
            selected.iter().map(|entry| (entry["name"].as_str().unwrap(), entry)).collect();
        assert_eq!(by_name["Dev Tool"]["source"], "nix");
        assert_eq!(by_name["Dev Tool"]["nix_category"], "scripts/devs");
        assert_eq!(by_name["Text Editor"]["source"], "nix");
        assert_eq!(by_name["Text Editor"]["nix_category"], "scripts/devs/txt");
        assert_eq!(by_name["IDE"]["source"], "nix");
        assert_eq!(by_name["IDE"]["nix_category"], "scripts/devs/ides");
        assert_eq!(by_name["Dev Utility"]["source"], "flatpak");
    }

    #[test]
    fn raw_nix_entries_merge_when_identity_and_description_agree() {
        let entries = vec![
            brave_flatpak(),
            raw_nix_component(
                "brave",
                "Privacy-oriented browser for Desktop and Laptop computers",
                "home-manager",
            ),
        ];
        let prefs = serde_json::json!({"default": "flatpak", "apps": {}});

        // The default Flatpak selection gains the Nix source option.
        let selected = collapse(entries.clone(), prefs.clone());
        assert_eq!(selected.len(), 1, "{selected:?}");
        assert_eq!(selected[0].get("id").and_then(Value::as_str), Some("com.brave.Browser"));
        let options = selected[0]
            .get("_source_alternatives")
            .and_then(Value::as_array)
            .unwrap();
        let nix_option = options
            .iter()
            .filter_map(Value::as_object)
            .find(|option| option.get("source").and_then(Value::as_str) == Some("nix"))
            .expect("Nix source option");
        assert_eq!(nix_option.get("name").and_then(Value::as_str), Some("Brave"));
        assert_eq!(
            nix_option.get("summary").and_then(Value::as_str),
            Some("Privacy-focused web browser")
        );
        assert_eq!(nix_option.get("packages").and_then(Value::as_array).map(Vec::len), Some(1));
        assert_eq!(nix_option["packages"][0], "brave");

        // On NixOS the Nix source is selected, but the card/page metadata still
        // comes from the richest provider (Flatpak here).
        let selected = collapse_with_source_policy(entries, prefs, false, true);
        assert_eq!(selected.len(), 1, "{selected:?}");
        let entry = &selected[0];
        assert_eq!(entry.get("source").and_then(Value::as_str), Some("nix"));
        assert_eq!(entry.get("id").and_then(Value::as_str), Some("nix:brave"));
        assert_eq!(entry.get("name").and_then(Value::as_str), Some("Brave"));
        assert_eq!(
            entry.get("summary").and_then(Value::as_str),
            Some("Privacy-focused web browser")
        );
        assert_eq!(entry.get("developer").and_then(Value::as_str), Some("Brave Software"));
        assert_eq!(entry.get("homepage").and_then(Value::as_str), Some("https://brave.com"));
        assert_eq!(entry.get("license").and_then(Value::as_str), Some("MPL-2.0"));
        assert_eq!(entry.get("icon").and_then(Value::as_str), Some("https://example.invalid/brave.png"));
        assert_eq!(
            entry.get("screenshots").and_then(Value::as_array).map(Vec::len),
            Some(1)
        );
        assert_eq!(entry["packages"][0], "brave");
        assert_eq!(entry.get("nix_name").and_then(Value::as_str), Some("brave"));
        assert_eq!(
            entry.get("metadata_description_format").and_then(Value::as_str),
            Some("appstream")
        );
    }

    #[test]
    fn source_metadata_ignores_an_unrelated_same_name_provider() {
        let entries = vec![
            serde_json::json!({
                "id": "io.github.mmp.Vice", "name": "Vice",
                "summary": "Air Traffic Control Simulator",
                "description_blocks": [{"type": "paragraph", "spans": [{
                    "text": "Vice is an air traffic control simulator focused on TRACON scenarios and simulated traffic."
                }]}],
                "packages": ["io.github.mmp.Vice"], "categories": ["Game"],
                "source": "flatpak", "origin": "flathub", "flatpak_remote": "flathub",
                "flatpak_scope": "system", "flatpak_installation": "default",
                "developer": "Matt Pharr", "verified": true,
                "icon": "https://example.invalid/atc.png",
                "screenshots": [{"images": [{"url": "https://example.invalid/atc.png", "width": 1, "height": 1}]}]
            })
            .as_object()
            .unwrap()
            .clone(),
            serde_json::json!({
                "id": "net.sf.VICE", "name": "VICE",
                "summary": "Versatile Commodore Emulator",
                "description_blocks": [{"type": "paragraph", "spans": [{
                    "text": "VICE is a free and cross platform emulator for Commodore 8-bit computers."
                }]}],
                "packages": ["net.sf.VICE"], "categories": ["Game"],
                "source": "flatpak", "origin": "flathub", "flatpak_remote": "flathub",
                "flatpak_scope": "system", "flatpak_installation": "default",
                "developer": "VICE", "verified": true,
                "icon": "https://example.invalid/vice.png"
            })
            .as_object()
            .unwrap()
            .clone(),
            raw_nix_component(
                "vice",
                "Emulators for a variety of 8-bit Commodore computers",
                "home-manager",
            ),
        ];
        let selected = collapse_with_source_policy(
            entries,
            serde_json::json!({"default": "flatpak", "apps": {}}),
            false,
            true,
        );
        let entry = selected
            .iter()
            .find(|entry| entry.get("source").and_then(Value::as_str) == Some("nix"))
            .expect("Nix selection");
        assert_eq!(entry.get("name").and_then(Value::as_str), Some("VICE"));
        assert_eq!(
            entry.get("developer").and_then(Value::as_str),
            Some("VICE")
        );
        assert_eq!(
            entry.get("icon").and_then(Value::as_str),
            Some("https://example.invalid/vice.png")
        );
        assert!(
            entry
                .get("description_blocks")
                .map(|value| value.to_string().contains("Commodore"))
                .unwrap_or(false),
            "{entry:?}"
        );
        let flatpak_options = entry
            .get("_source_alternatives")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .filter_map(Value::as_object)
            .filter(|option| option.get("source").and_then(Value::as_str) == Some("flatpak"))
            .collect::<Vec<_>>();
        assert_eq!(flatpak_options.len(), 1, "{entry:?}");
        assert_eq!(
            flatpak_options[0].get("id").and_then(Value::as_str),
            Some("net.sf.VICE")
        );
    }

    #[test]
    fn raw_nix_entries_without_matching_identity_stay_isolated() {
        let entries = vec![
            component("dev.qwery.AddWater", "Add Water", "native", &["Utility"]),
            raw_nix_component(
                "addwater",
                "Command line tool for adding water",
                "home-manager",
            ),
            component("org.gnome.Boxes.desktop", "Boxes", "native", &["Utility"]),
            raw_nix_component(
                "boxes",
                "Command line program which draws, removes, and repairs ASCII art boxes",
                "home-manager",
            ),
            // Element proves identity by developer/vendor, but the package is
            // the periodic-table CLI, not the Matrix messenger.
            serde_json::json!({
                "id": "im.riot.Riot", "name": "Element", "summary": "Matrix chat client",
                "description_blocks": [{"type": "paragraph", "spans": [{
                    "text": "Secure collaboration and messaging for Matrix."
                }]}],
                "packages": ["im.riot.Riot"], "categories": ["Network"],
                "source": "flatpak", "origin": "flathub", "flatpak_remote": "flathub",
                "flatpak_scope": "system", "flatpak_installation": "default",
                "developer": "Element Creations Ltd", "verified": true
            })
            .as_object()
            .unwrap()
            .clone(),
            raw_nix_component(
                "element",
                "Periodic table on the command line",
                "home-manager",
            ),
            // A shared brand word is not evidence: the nixpkgs package is the
            // Todoist CLI, not the desktop application.
            serde_json::json!({
                "id": "com.todoist.Todoist", "name": "Todoist", "summary": "Planner Calendar",
                "description_blocks": [{"type": "paragraph", "spans": [{
                    "text": "Todoist is a simple yet powerful task planner and habit tracker."
                }]}],
                "packages": ["com.todoist.Todoist"], "categories": ["Utility"],
                "source": "flatpak", "origin": "flathub", "flatpak_remote": "flathub",
                "flatpak_scope": "system", "flatpak_installation": "default",
                "developer": "Doist", "verified": true
            })
            .as_object()
            .unwrap()
            .clone(),
            raw_nix_component("todoist", "Todoist CLI Client", "home-manager"),
            // Different qualifier: the engine is not the launcher app.
            serde_json::json!({
                "id": "org.solarus_games.solarus.Launcher", "name": "Solarus Launcher",
                "summary": "Launcher for Solarus video games",
                "description_blocks": [{"type": "paragraph", "spans": [{
                    "text": "Solarus Launcher is a game launcher and manager for games built on the Solarus engine."
                }]}],
                "packages": ["org.solarus_games.solarus.Launcher"], "categories": ["Game"],
                "source": "flatpak", "origin": "flathub", "flatpak_remote": "flathub",
                "flatpak_scope": "system", "flatpak_installation": "default",
                "developer": "Solarus Labs", "verified": true
            })
            .as_object()
            .unwrap()
            .clone(),
            raw_nix_component("solarus", "Zelda-like ARPG game engine", "home-manager"),
        ];
        let selected = collapse(entries, serde_json::json!({"default": "flatpak", "apps": {}}));
        assert_eq!(selected.len(), 10, "{selected:?}");
        assert!(selected.iter().all(|entry| entry.get("_source_alternatives").is_none()));
    }

    #[test]
    fn raw_nix_entries_merge_through_a_shared_long_description() {
        let entries = vec![
            serde_json::json!({
                "id": "io.github.rocket.editor", "name": "Rocket", "summary": "Rocket Editor",
                "description_blocks": [{"type": "paragraph", "spans": [{
                    "text": "Rocket is a sync-tracker, a tool for synchronizing music and visuals in demoscene productions."
                }]}],
                "packages": ["io.github.rocket.editor"], "categories": ["Development"],
                "source": "flatpak", "origin": "flathub", "flatpak_remote": "flathub",
                "flatpak_scope": "system", "flatpak_installation": "default",
                "developer": "Rocket", "verified": true
            })
            .as_object()
            .unwrap()
            .clone(),
            raw_nix_component(
                "rocket",
                "Tool for synchronizing music and visuals in demoscene productions",
                "home-manager",
            ),
        ];
        let selected = collapse(entries, serde_json::json!({"default": "flatpak", "apps": {}}));
        assert_eq!(selected.len(), 1, "{selected:?}");
        let options = selected[0]
            .get("_source_alternatives")
            .and_then(Value::as_array)
            .unwrap();
        assert!(options.iter().any(|option| {
            option.get("appstream_source").and_then(Value::as_str) == Some("nix")
                || option.get("source").and_then(Value::as_str) == Some("nix")
        }));
    }

    #[test]
    fn source_metadata_borrows_the_richest_provider_for_any_selected_source() {
        let entries = vec![
            {
                let mut native = component("org.example.App", "App", "native", &["Utility"]);
                native.insert(
                    "description_blocks".into(),
                    serde_json::json!([{"type": "paragraph", "spans": [{
                        "text": "A privacy-focused web browser that blocks ads and trackers."
                    }]}]),
                );
                native
            },
            {
                let mut flatpak = brave_flatpak();
                flatpak.insert("id".into(), Value::String("org.example.App".into()));
                flatpak.insert("name".into(), Value::String("App".into()));
                flatpak.insert("verified".into(), Value::Bool(false));
                flatpak.insert(
                    "packages".into(),
                    serde_json::json!(["org.example.App"]),
                );
                flatpak
            },
        ];
        let selected = collapse(
            entries,
            serde_json::json!({"default": "native", "apps": {}}),
        );
        assert_eq!(selected.len(), 1, "{selected:?}");
        let entry = &selected[0];
        assert_eq!(entry.get("source").and_then(Value::as_str), Some("native"));
        assert_eq!(
            entry.get("summary").and_then(Value::as_str),
            Some("Privacy-focused web browser")
        );
        assert_eq!(entry.get("developer").and_then(Value::as_str), Some("Brave Software"));
        assert_eq!(entry.get("icon").and_then(Value::as_str), Some("https://example.invalid/brave.png"));
        assert!(entry.get("description_blocks").is_some());
        assert_eq!(entry.get("homepage").and_then(Value::as_str), Some("https://brave.com"));
    }

    #[test]
    fn appimage_preference_value_accepts_the_source() {
        let host_os: std::collections::HashSet<String> = Default::default();
        assert_eq!(preference_value_rs(&serde_json::json!("appimage"), &host_os), Some("appimage".into()));
        assert_eq!(preference_value_rs(&serde_json::json!({"all": "appimage"}), &host_os), Some("appimage".into()));
        assert_eq!(preference_value_rs(&serde_json::json!("bogus"), &host_os), None);
    }

    #[test]
    fn flatpak_source_option_keys_separate_remotes() {
        assert_eq!(
            source_option_key_rs(&flatpak_component("org.example.App", "flathub", "user", "user")),
            "flatpak:user:user:flathub"
        );
        assert_ne!(
            source_option_key_rs(&flatpak_component("org.example.App", "flathub", "user", "user")),
            source_option_key_rs(&flatpak_component("org.example.App", "flatpark", "user", "user"))
        );
        // Same-remote copies still coalesce for dedupe purposes.
        assert_eq!(
            source_option_key_rs(&flatpak_component("org.example.App", "flatpark", "user", "user")),
            source_option_key_rs(&flatpak_component("org.example.App", "flatpark", "user", "user"))
        );
    }

    #[test]
    fn multiple_flatpak_remotes_stay_selectable_with_stable_flathub_default() {
        let entries = vec![
            component("native.example", "Unrelated", "native", &["Office"]),
            flatpak_component("org.example.App", "flatpark", "user", "user"),
            flatpak_component("org.example.App", "flathub", "user", "user"),
        ];
        let prefs = serde_json::json!({"default": "flatpak", "apps": {}});
        let selected = collapse(entries, prefs);
        assert_eq!(selected.len(), 2, "{selected:?}");

        let app = selected.iter()
            .find(|entry| entry.get("id").and_then(Value::as_str) == Some("org.example.App"))
            .unwrap();
        assert_eq!(app.get("source").and_then(Value::as_str), Some("flatpak"));
        // The default selection stays the established remote even when the
        // FlatPark copy arrived first in the group.
        assert_eq!(
            app.get("flatpak_remote").and_then(Value::as_str),
            Some("flathub"),
            "{app:?}"
        );
        // Both remotes remain reachable through the source selector.
        let remote_keys: Vec<String> = std::iter::once(app.clone())
            .chain(
                app.get("_source_alternatives").and_then(Value::as_array)
                    .unwrap()
                    .iter()
                    .filter_map(|v| v.as_object().cloned()),
            )
            .map(|m| source_option_key_rs(&m))
            .collect();
        assert!(remote_keys.contains(&"flatpak:user:user:flathub".to_string()), "{remote_keys:?}");
        assert!(remote_keys.contains(&"flatpak:user:user:flatpark".to_string()), "{remote_keys:?}");
    }

    #[test]
    fn flatpark_system_scope_options_keep_scope_labeling_data() {
        let groups = vec![
            flatpak_component("org.example.App", "flathub", "user", "user"),
            flatpak_component("org.example.App", "flatpark", "system", "default"),
        ];
        let prefs = serde_json::json!({"default": "flatpak", "apps": {}});
        let selected = collapse(groups, prefs);
        assert_eq!(selected.len(), 1, "{selected:?}");
        let keys: Vec<String> = std::iter::once(selected[0].clone())
            .chain(
                selected[0].get("_source_alternatives").and_then(Value::as_array)
                    .unwrap()
                    .iter()
                    .filter_map(|v| v.as_object().cloned()),
            )
            .map(|m| source_option_key_rs(&m))
            .collect();
        assert!(keys.contains(&"flatpak:user:user:flathub".to_string()), "{keys:?}");
        assert!(keys.contains(&"flatpak:system:default:flatpark".to_string()), "{keys:?}");
    }
}

#[cfg(test)]
mod featured_eligibility_tests {
    use super::*;

    fn entry(source: &str, category: &str, rating: Option<f64>) -> RuntimeAppStreamEntry {
        RuntimeAppStreamEntry {
            category: category.into(),
            appstream_id: format!("{source}.example"),
            name: "Example".into(),
            canonical_name: "Example".into(),
            source: source.into(),
            package_names: vec!["example".into()],
            search_packages: vec!["example".into()],
            nix_packages: Vec::new(),
            description_lower: String::new(),
            developer_lower: String::new(),
            is_new: false,
            review_rating: rating,
            review_subscore: None,
            category_review_score: None,
            homebrew_install_count: 0,
            payload: Vec::new(),
        }
    }

    #[test]
    fn categorized_nix_packages_are_featured_without_reviews() {
        assert!(featured_entry_eligible(&entry("nix", "media", None)));
        assert!(featured_entry_eligible(&entry("nix", "devs/ides", None)));
    }

    #[test]
    fn the_nix_fallback_category_stays_out_of_featured() {
        assert!(!featured_entry_eligible(&entry("nix", "nix", None)));
        assert!(!featured_entry_eligible(&entry("nix", "", None)));
    }

    #[test]
    fn other_sources_keep_the_review_gate() {
        assert!(featured_entry_eligible(&entry("flatpak", "media", Some(70.0))));
        assert!(!featured_entry_eligible(&entry("flatpak", "media", Some(69.9))));
        assert!(!featured_entry_eligible(&entry("native", "media", None)));
        assert!(!featured_entry_eligible(&entry("homebrew", "homebrew", Some(100.0))));
    }
}

#[cfg(test)]
mod omission_key_tests {
    use super::*;

    #[test]
    fn snap_entries_answer_to_io_snapcraft_keys() {
        let item = serde_json::json!({
            "id": "io.snapcraft.firefox", "name": "Firefox", "source": "snap",
            "snap_name": "firefox", "snap_id": "bugPu8dGvZXa3p7X", "packages": ["firefox"]
        }).as_object().unwrap().clone();
        let keys = omission_keys_rs(&item);
        assert!(keys.contains(&"io.snapcraft.firefox".to_string()), "{:?}", keys);
        assert!(keys.contains(&"firefox".to_string()));
    }

    #[test]
    fn homebrew_entries_answer_to_homebrew_formula_keys() {
        let item = serde_json::json!({
            "id": "homebrew:wget", "name": "wget", "source": "homebrew", "packages": ["wget"]
        }).as_object().unwrap().clone();
        let keys = omission_keys_rs(&item);
        assert!(keys.contains(&"homebrew.wget".to_string()), "{:?}", keys);
        assert!(keys.contains(&"wget".to_string()));
    }

    #[test]
    fn native_entries_gain_no_omission_extras() {
        let item = serde_json::json!({
            "id": "org.distro.App", "name": "App", "source": "native", "packages": ["app"]
        }).as_object().unwrap().clone();
        let keys = omission_keys_rs(&item);
        assert!(!keys.iter().any(|k| k.starts_with("io.snapcraft.") || k.starts_with("homebrew.")), "{:?}", keys);
    }
}

#[cfg(test)]
mod homebrew_binary_tests {
    use super::*;

    #[test]
    fn snapshot_validation_rejects_empty_and_malformed_rows() {
        let path = std::env::temp_dir().join(format!("lt-brew-validation-{}-{}", std::process::id(),
            std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        for (text, expected) in [("[]", false), ("{", false), ("[{}]", false),
                                 ("[{\"name\":\" \"}]", false), ("[{\"name\":\"gh\"}]", true)] {
            fs::write(&path, text).unwrap();
            assert_eq!(validate_homebrew_snapshot_rs(path.to_str().unwrap(), 1024), expected);
        }
        assert!(!validate_homebrew_snapshot_rs(path.to_str().unwrap(), 1));
        fs::remove_file(path).unwrap();
    }

    #[test]
    fn reused_metadata_keeps_latest_homebrew_counts() {
        let mut old = serde_json::json!({"source":"homebrew", "_metadata_hash":"same"}).as_object().unwrap().clone();
        let mut current = old.clone();
        current.insert("homebrew_install_count".into(), Value::Number(321.into()));
        update_reused_metadata(&mut old, &current);
        assert_eq!(old.get("homebrew_install_count"), Some(&Value::Number(321.into())));
        current.insert("homebrew_install_count".into(), Value::Number(654.into()));
        update_reused_metadata(&mut old, &current);
        assert_eq!(old.get("homebrew_install_count"), Some(&Value::Number(654.into())));
    }


    #[test]
    fn missing_published_counts_require_republication() {
        let previous = serde_json::json!({"identity":"homebrew:gh", "source":"homebrew", "name":"gh"}).as_object().unwrap().clone();
        let mut current = previous.clone();
        current.insert("homebrew_install_count".into(), Value::Number(100.into()));
        let mut generation = AppStreamGeneration { previous: vec![previous], entries: vec![current.clone()], extensions: vec![] };
        assert!(!homebrew_counts_match(&generation.entries, &generation.previous));
        generation.previous = vec![current];
        assert!(homebrew_counts_match(&generation.entries, &generation.previous));
    }

    #[test]
    fn homebrew_category_indexes_popular_entries_first() {
        let entries = vec![
            serde_json::json!({"name":"zeta","category":"homebrew","appstream_source":"homebrew","homebrew_install_count":100}),
            serde_json::json!({"name":"alpha","category":"homebrew","appstream_source":"homebrew","homebrew_install_count":100}),
            serde_json::json!({"name":"unranked","category":"homebrew","appstream_source":"homebrew"}),
            serde_json::json!({"name":"popular","category":"homebrew","appstream_source":"homebrew","homebrew_install_count":500}),
        ];
        let catalog = AppStreamCatalog::from_values(entries, "test".into());
        let names: Vec<_> = catalog.by_category["homebrew"].iter()
            .map(|&index| catalog.entries[index].name.as_str()).collect();
        assert_eq!(names, vec!["popular", "alpha", "zeta", "unranked"]);
    }

    #[test]
    fn source_binary_rebuilds_after_corruption_and_source_change() {
        let directory = std::env::temp_dir().join(format!("linuxtoys-brew-{}-{}",
            std::process::id(), std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        fs::create_dir_all(&directory).unwrap();
        let path = directory.join("formula.json");
        fs::write(&path, r#"[{"name":"wget","desc":"Downloader"}]"#).unwrap();
        let source = path.to_str().unwrap();
        let first = load_homebrew_formulae(source, "x86_64").unwrap();
        assert_eq!(first.len(), 1);
        let binary = path.with_extension("x86_64.bin");
        assert!(binary.is_file());
        let modified = fs::metadata(&binary).unwrap().modified().unwrap();
        assert_eq!(load_homebrew_formulae(source, "x86_64").unwrap(), first);
        assert_eq!(fs::metadata(&binary).unwrap().modified().unwrap(), modified);
        fs::write(&binary, b"").unwrap();
        assert_eq!(load_homebrew_formulae(source, "x86_64").unwrap(), first);
        assert!(fs::metadata(&binary).unwrap().len() > 0);
        fs::write(&binary, b"corrupt").unwrap();
        assert_eq!(load_homebrew_formulae(source, "x86_64").unwrap(), first);
        fs::write(&path, r#"[{"name":"git","desc":"Version control system"}]"#).unwrap();
        let updated = load_homebrew_formulae(source, "x86_64").unwrap();
        assert_eq!(updated[0].get("name").and_then(Value::as_str), Some("git"));
        load_homebrew_formulae(source, "arm64").unwrap();
        assert!(path.with_extension("arm64.bin").is_file());
        fs::write(&path, b"[]").unwrap();
        assert!(load_homebrew_formulae(source, "x86_64").is_err());
        fs::remove_dir_all(directory).unwrap();
    }
}
