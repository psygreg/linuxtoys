use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs;
use std::io::Write;

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

fn normalize_id(value: &str) -> String {
    value.trim().strip_suffix(".desktop").or_else(|| value.trim().strip_suffix(".Desktop")).unwrap_or(value.trim()).to_lowercase()
}

#[pyfunction]
pub(crate) fn load_appstream_catalog(py: Python<'_>, path: &str) -> PyResult<Vec<Py<PyAny>>> {
    let content = match fs::read_to_string(path) {
        Ok(v) => v,
        Err(_) => return Ok(Vec::new()),
    };
    let parsed: Value = match serde_json::from_str(&content) {
        Ok(v) => v,
        Err(_) => return Ok(Vec::new()),
    };
    let Some(values) = parsed.as_array() else {
        return Ok(Vec::new());
    };
    let mut out = Vec::with_capacity(values.len());
    for value in values {
        if value.is_object() {
            out.push(json_to_py(py, value)?);
        }
    }
    Ok(out)
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
fn resolve_category_rs(cats:&Value, paths:&[String], cfg:&Value)->Option<String>{
    let set:std::collections::HashSet<&str>=cats.as_array()?.iter().filter_map(Value::as_str).collect(); let mut exact=std::collections::HashSet::new(); let mut by:std::collections::HashMap<String,Vec<String>>=std::collections::HashMap::new();
    for p in paths{let p=p.replace('\\',"/").trim_matches('/').to_string();if p.is_empty()||p=="lists"{continue} exact.insert(p.clone());by.entry(p.rsplit('/').next().unwrap_or(&p).into()).or_default().push(p)}
    for v in by.values_mut(){v.sort_by_key(|p|(p.matches('/').count(),p.clone()))}
    let o=cfg.as_object()?;
    if set.contains("Emulator"){if let Some(v)=first_category(&serde_json::json!(["emu"]),&exact,&by){return Some(v)}}
    if let Some(rules)=o.get("expressions").and_then(Value::as_array){for r in rules{let a=r.as_array()?;let req=a.get(0)?.as_array()?;if req.iter().filter_map(Value::as_str).all(|x|set.contains(x)){if let Some(v)=first_category(a.get(1)?,&exact,&by){return Some(v)}}}}
    for pair in [("standalone_priority","additional"),("main_priority","main")] {if let Some(pr)=o.get(pair.0).and_then(Value::as_array){for k in pr.iter().filter_map(Value::as_str){if set.contains(k){if let Some(c)=o.get(pair.1).and_then(Value::as_object).and_then(|m|m.get(k)){if let Some(v)=first_category(c,&exact,&by){return Some(v)}}}}}}
    None
}
fn flatten_blocks(v:&Value)->String{let Some(a)=v.as_array()else{return String::new()};let mut blocks=Vec::new();for b in a{let Some(m)=b.as_object()else{continue};if m.get("type").and_then(Value::as_str)==Some("paragraph"){if let Some(sp)=m.get("spans").and_then(Value::as_array){blocks.push(sp.iter().filter_map(|s|s.get("text").and_then(Value::as_str)).collect::<Vec<_>>().join(" ").trim().to_string())}}else if let Some(items)=m.get("items").and_then(Value::as_array){blocks.push(items.iter().filter_map(|i|i.as_array()).map(|sp|sp.iter().filter_map(|s|s.get("text").and_then(Value::as_str)).collect::<Vec<_>>().join(" ").trim().to_string()).collect::<Vec<_>>().join("\n"))}}blocks.into_iter().filter(|s|!s.is_empty()).collect::<Vec<_>>().join("\n\n")}
fn clean_screens(v:Option<&Value>)->Value{let mut out=Vec::new();if let Some(a)=v.and_then(Value::as_array){for s in a{if let Some(m)=s.as_object(){let mut imgs=Vec::new();if let Some(ia)=m.get("images").and_then(Value::as_array){for i in ia{let Some(im)=i.as_object()else{continue};let url=im.get("url").and_then(Value::as_str).unwrap_or("").trim();if url.is_empty(){continue}imgs.push(serde_json::json!({"url":url,"width":im.get("width").and_then(Value::as_i64).unwrap_or(0).max(0),"height":im.get("height").and_then(Value::as_i64).unwrap_or(0).max(0)}))}}if !imgs.is_empty(){out.push(serde_json::json!({"images":imgs}))}}else if let Some(p)=s.as_str(){if !p.trim().is_empty(){out.push(Value::String(p.trim().into()))}}}}Value::Array(out)}

fn adapt_appstream_maps_values(components:Vec<serde_json::Map<String,Value>>, category_paths:Vec<String>, category_config_json:&str, lang:&str, curated_ids:Vec<String>, curated_packages:Vec<String>, curated_names:Vec<String>, overlays_json:&str, native_badge:&str)->Vec<Value>{
    let cfg:Value=serde_json::from_str(category_config_json).unwrap_or(Value::Null);let overlays:Value=serde_json::from_str(overlays_json).unwrap_or_else(|_|serde_json::json!({}));let ov=overlays.as_object();let ids:std::collections::HashSet<String>=curated_ids.into_iter().map(|s|s.to_lowercase()).collect();let pkgs:std::collections::HashSet<String>=curated_packages.into_iter().map(|s|s.to_lowercase()).collect();let names:std::collections::HashSet<String>=curated_names.into_iter().map(|s|s.to_lowercase()).collect();let mut out=Vec::new();
    for m in components {let id=m.get("id").and_then(Value::as_str).unwrap_or("");if id.is_empty()||ids.contains(&id.to_lowercase()){continue}if m.get("name").and_then(Value::as_str).is_some_and(|n|names.contains(&n.to_lowercase())){continue}if m.get("packages").and_then(Value::as_array).is_some_and(|a|a.iter().filter_map(Value::as_str).any(|p|pkgs.contains(&p.to_lowercase()))){continue}
        let Some(category)=resolve_category_rs(m.get("categories").unwrap_or(&Value::Null),&category_paths,&cfg) else{continue};let packages:Vec<String>=m.get("packages").and_then(Value::as_array).into_iter().flatten().filter_map(Value::as_str).map(str::to_string).collect();if packages.is_empty(){continue}
        let (name,_)=localized(&m,"localized_names",lang,m.get("name").cloned().unwrap_or(Value::String(String::new())));let(summary,_)=localized(&m,"localized_summaries",lang,m.get("summary").cloned().unwrap_or(Value::String(String::new())));let(dev,_)=localized(&m,"localized_developers",lang,m.get("developer").cloned().unwrap_or(Value::String(String::new())));let(blocks,bloc)=localized(&m,"localized_descriptions",lang,m.get("description_blocks").cloned().unwrap_or_else(||Value::Array(vec![])));let shots=clean_screens(m.get("screenshots"));let source=m.get("source").and_then(Value::as_str).unwrap_or("native");let flat=source=="flatpak";let origin=m.get("origin").and_then(Value::as_str).unwrap_or("");let scope=m.get("flatpak_scope").and_then(Value::as_str).unwrap_or("");let long=flatten_blocks(&blocks);
        let mut e=serde_json::Map::new();macro_rules! s { ($k:expr, $v:expr) => {{ let _ = e.insert($k.into(), Value::String($v.to_string())); }} }
        s!("id",id);e.insert("name".into(),name);s!("appstream_canonical_name",m.get("name").and_then(Value::as_str).unwrap_or(id));e.insert("description".into(),summary);s!("description_tag","");e.insert("description_localized".into(),Value::Bool(has_localized(&m,"localized_summaries",lang)));s!("long_description",long);e.insert("long_description_blocks".into(),blocks);s!("long_description_locale",bloc);s!("long_description_tag","");s!("long_description_format","appstream");e.insert("screenshots".into(),shots.clone());
        for(k,src)in [("homepage_url","homepage"),("donate","donation"),("donate_url","donation"),("license","license")]{s!(k,m.get(src).and_then(Value::as_str).unwrap_or(""));}e.insert("developer".into(),dev);s!("icon",m.get("icon").and_then(Value::as_str).unwrap_or("application-x-executable"));s!("category",category);s!("type",if flat{"flathub"}else{"native"});e.insert("package-name".into(),if flat{Value::String(packages.first().cloned().unwrap_or_else(||id.into()))}else{Value::Array(packages.iter().cloned().map(Value::String).collect())});s!("repo",if origin.is_empty(){"appstream"}else{origin});for(k,v)in [("revert","yes"),("reboot","no")]{s!(k,v)}for k in ["is_script","is_repo_entry","is_appstream_entry"]{e.insert(k.into(),Value::Bool(true));}e.insert("is_subcategory".into(),Value::Bool(false));s!("appstream_id",id);s!("appstream_launchable",m.get("launchable").and_then(Value::as_str).unwrap_or(""));s!("appstream_source",source);s!("appstream_origin",origin);for k in ["flatpak_remote","flatpak_scope","flatpak_installation"]{s!(k,m.get(k).and_then(Value::as_str).unwrap_or(""));}e.insert("overrides".into(),if flat&&scope=="system"{serde_json::json!({"skip-user":true})}else{serde_json::json!({})});for k in ["popularity_metric","review_rating","review_count"]{e.insert(k.into(),m.get(k).cloned().unwrap_or(Value::Null));}s!("appstream_version",m.get("version").and_then(Value::as_str).unwrap_or(""));s!("repo_app_id",id);e.insert("is_new".into(),Value::Bool(false));e.insert("is_verified".into(),Value::Bool(flat&&m.get("verified").and_then(Value::as_bool).unwrap_or(false)));s!("native_distro_badge",if flat{""}else{native_badge});s!("appstream_badge",if flat{"distros/flathub.webp"}else{""});e.insert("has_app_page".into(),Value::Bool(!long.is_empty()||shots.as_array().is_some_and(|a|!a.is_empty())));s!("path",format!("appstream://{source}/{id}"));
        if let Some(overlay)=ov.and_then(|o|o.get(&normalize_id(id))).and_then(Value::as_object){for(k,v)in overlay{e.insert(k.clone(),v.clone());}if overlay.get("purchase_options").is_some()||overlay.get("subscription_options").is_some(){e.insert("has_app_page".into(),Value::Bool(true));}}
        if let Some(alts)=m.get("_source_alternatives").and_then(Value::as_array){let mut opts=vec![Value::Object(e.clone())];for a in alts{if let Value::Object(am)=a{let nested=adapt_appstream_maps_values(vec![am.clone()],category_paths.clone(),category_config_json,lang,vec![],vec![],vec![],overlays_json,native_badge);if let Some(n)=nested.into_iter().next(){opts.push(n);}}}if opts.len()>1{e.insert("source_options".into(),Value::Array(opts));s!("recommended_source",m.get("_source_recommended").and_then(Value::as_str).unwrap_or(source));}}
        out.push(Value::Object(e));
    }
    out.sort_by_key(|x|x.get("name").and_then(Value::as_str).unwrap_or("").to_lowercase());out
}

fn source_option_key_rs(item: &serde_json::Map<String, Value>) -> String {
    let source = item.get("source").and_then(Value::as_str).unwrap_or("native");
    if source != "flatpak" { return source.to_string(); }
    let scope = item.get("flatpak_scope").and_then(Value::as_str).unwrap_or("");
    let installation = item.get("flatpak_installation").and_then(Value::as_str).unwrap_or("");
    format!("flatpak:{scope}:{installation}")
}
fn component_identity_rs(item:&serde_json::Map<String,Value>)->(String,String){
    (normalize_id(item.get("id").and_then(Value::as_str).unwrap_or("")), item.get("name").and_then(Value::as_str).unwrap_or("").trim().to_lowercase())
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
        for mut c in candidates {let k=source_option_key_rs(&c);if !seen.insert(k){continue}c.remove("_source_alternatives");c.remove("_source_recommended");out.push(c)} }
    out
}
fn with_source_options_rs(selected:&serde_json::Map<String,Value>,group:&[serde_json::Map<String,Value>])->serde_json::Map<String,Value>{
    let flat:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str)==Some("flatpak")).collect();
    let native:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str).unwrap_or("native")=="native").collect();
    let mut candidates:Vec<&serde_json::Map<String,Value>>=if is_verified_flatpak_rs(selected){flat}else{native.into_iter().chain(flat).collect()};
    let mut seen=std::collections::HashSet::new();candidates.retain(|m|seen.insert(source_option_key_rs(m)));if candidates.len()<2{return selected.clone()}
    let sk=source_option_key_rs(selected);let alts:Vec<Value>=candidates.into_iter().filter(|m|source_option_key_rs(m)!=sk).map(|m|Value::Object(m.clone())).collect();let mut r=selected.clone();if !alts.is_empty(){r.insert("_source_alternatives".into(),Value::Array(alts));r.insert("_source_recommended".into(),Value::String(sk));}r
}
fn inherit_popularity_rs(natives:&mut [serde_json::Map<String,Value>],flat:&[serde_json::Map<String,Value>]){
    if let Some(d)=flat.iter().find(|m|m.get("popularity_metric").is_some_and(|v|!v.is_null())) {for n in natives {for k in ["popularity_metric","popularity_downloads"]{n.insert(k.into(),d.get(k).cloned().unwrap_or(Value::Null));}}}
}
fn group_prefers_dev_native_rs(group:&[serde_json::Map<String,Value>],paths:&[String],cfg:&Value,steamos:bool)->bool{
    !steamos&&group.iter().any(|m|resolve_category_rs(m.get("categories").unwrap_or(&Value::Null),paths,cfg).is_some_and(|c|matches!(c.rsplit('/').next(),Some("devs"|"ides"))))
}
fn preference_rs(item:&serde_json::Map<String,Value>,prefs:&Value,host_os:&std::collections::HashSet<String>)->String{
    let Some(o)=prefs.as_object()else{return "flatpak".into()};let default=o.get("default").and_then(Value::as_str).unwrap_or("flatpak");let apps=o.get("apps").and_then(Value::as_object);
    let id=item.get("id").and_then(Value::as_str).unwrap_or("");let name=item.get("name").and_then(Value::as_str).unwrap_or("");let Some(v)=apps.and_then(|a|a.get(id).or_else(||a.get(name)))else{return default.into()};
    if let Some(s)=v.as_str(){return if matches!(s,"native"|"flatpak"){s.into()}else{"flatpak".into()}}
    if let Some(m)=v.as_object(){for(k,v)in m{if k!="all"&&host_os.contains(&k.to_lowercase()){if let Some(s)=v.as_str(){return s.into()}}}return m.get("all").and_then(Value::as_str).unwrap_or(default).into()} default.into()
}
fn collapse_source_groups_rs(components:Vec<serde_json::Map<String,Value>>,paths:&[String],cfg:&Value,prefs:&Value,locks:&std::collections::HashSet<String>,host_os:&std::collections::HashSet<String>,prefer_native_host:bool,steamos:bool,by_name_pass:bool)->Vec<serde_json::Map<String,Value>>{
    let mut groups:std::collections::BTreeMap<String,Vec<serde_json::Map<String,Value>>>=std::collections::BTreeMap::new();let mut pass=Vec::new();
    for m in components {let(id,name)=component_identity_rs(&m);let key=if by_name_pass{if name.is_empty(){None}else{Some(name)}}else if !id.is_empty(){Some(format!("id:{id}"))}else if !name.is_empty(){Some(format!("name:{name}"))}else{None};if let Some(k)=key{groups.entry(k).or_default().push(m)}else{pass.push(m)}}
    let mut out=pass;
    for (_,raw) in groups {let mut group=if by_name_pass{expand_source_group_rs(&raw)}else{raw};if let Some(l)=locked_system_flatpak_rs(&group,locks){out.push(l);continue}
        let mut flat:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str)==Some("flatpak")).cloned().collect();let mut natives:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str).unwrap_or("native")=="native").cloned().collect();flat.sort_by_key(|m|(m.get("flatpak_scope").and_then(Value::as_str).unwrap_or("")!="user",m.get("flatpak_installation").and_then(Value::as_str).unwrap_or("").to_string()));group=natives.iter().cloned().chain(flat.iter().cloned()).collect();
        if natives.is_empty()&&flat.len()>1{out.push(with_source_options_rs(&flat[0],&group));continue}let sources:std::collections::HashSet<_>=group.iter().map(|m|m.get("source").and_then(Value::as_str).unwrap_or("native")).collect();if sources.len()<2{out.extend(group);continue}
        if !natives.is_empty()&&group_prefers_dev_native_rs(&group,paths,cfg,steamos){inherit_popularity_rs(&mut natives,&flat);out.extend(natives.iter().map(|m|with_source_options_rs(m,&group)));continue}
        if let Some(v)=flat.iter().find(|m|is_verified_flatpak_rs(m)){out.push(with_source_options_rs(v,&group));continue}if prefer_native_host&&!natives.is_empty(){out.extend(natives.iter().map(|m|with_source_options_rs(m,&group)));continue}
        let pref=preference_rs(&group[0],prefs,host_os);let mut selected:Vec<_>=group.iter().filter(|m|m.get("source").and_then(Value::as_str).unwrap_or("native")==pref).cloned().collect();if selected.is_empty(){selected=group.clone()}if selected.first().and_then(|m|m.get("source")).and_then(Value::as_str)==Some("flatpak"){selected.truncate(1)}out.extend(selected.iter().map(|m|with_source_options_rs(m,&group)));
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
fn release_count_last_year_rs(component:&XmlNode, now:i64)->i64 {
    use chrono::{DateTime,NaiveDate}; let cutoff=now-365*24*60*60; let mut count=0;
    if let Some(releases)=component.child("releases") { for r in releases.children_named("release") { let mut ts=r.attrs.get("timestamp").and_then(|v|v.parse::<f64>().ok()).map(|v|v as i64); if ts.is_none(){if let Some(d)=r.attrs.get("date"){ts=DateTime::parse_from_rfc3339(&d.replace('Z',"+00:00")).ok().map(|x|x.timestamp()).or_else(||NaiveDate::parse_from_str(d,"%Y-%m-%d").ok().and_then(|x|x.and_hms_opt(0,0,0)).map(|x|x.and_utc().timestamp()));}} if ts.is_some_and(|v|v>=cutoff&&v<=now){count+=1} } } count
}
fn flatpak_icon_rs(component:&XmlNode,dir:&str,id:&str)->String{
    if let Some(icon)=component.children_named("icon").find(|n|n.attrs.get("type").map(String::as_str)==Some("cached")){let name=icon.text_trimmed();for size in ["128x128","64x64"]{let p=std::path::Path::new(dir).join("icons").join(size).join(&name);if p.is_file(){return p.to_string_lossy().into_owned()}}}
    for size in ["128x128","64x64"]{for ext in ["png","svg"]{let p=std::path::Path::new(dir).join("icons").join(size).join(format!("{id}.{ext}"));if p.is_file(){return p.to_string_lossy().into_owned()}}} "application-x-executable".into()
}
fn launchable_rs(c:&XmlNode,id:&str)->String{for n in c.children_named("launchable"){let v=n.text_trimmed();if !v.is_empty()&&(n.attrs.get("type").map(String::as_str)==Some("desktop-id")||v.ends_with(".desktop")){return v}}if id.ends_with(".desktop"){id.into()}else{String::new()}}

fn normalize_flatpak_component_rs(component:&XmlNode, source:&serde_json::Map<String,Value>, eol:&std::collections::HashSet<String>, now:i64)->Option<serde_json::Map<String,Value>>{
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
    ins!("identity",Value::String(format!("flatpak:{scope}:{installation}:{remote}:{id}")));ins!("_metadata_hash",Value::String(raw_hash));ins!("id",Value::String(id.clone()));ins!("name",Value::String(name));ins!("summary",Value::String(summary));ins!("description_blocks",default_description_rs(component));ins!("localized_names",Value::Object(localized_names));ins!("localized_summaries",Value::Object(localized_summaries));ins!("localized_descriptions",Value::Object(localized_desc));ins!("localized_developers",Value::Object(localized_devs));ins!("packages",Value::Array(vec![Value::String(app_id)]));ins!("categories",Value::Array(categories));ins!("launchable",Value::String(launchable_rs(component,&id)));ins!("icon",Value::String(flatpak_icon_rs(component,dir,&id)));ins!("screenshots",Value::Array(screenshots));ins!("homepage",Value::String(url_of("homepage")));ins!("donation",Value::String(url_of("donation")));ins!("license",Value::String(default_localized_text_rs(component,"project_license")));ins!("developer",Value::String(developer));ins!("verified",Value::Bool(verified));ins!("origin",Value::String(remote.into()));ins!("source",Value::String("flatpak".into()));ins!("version",Value::String(version));ins!("flatpak_remote",Value::String(remote.into()));ins!("flatpak_scope",Value::String(scope.into()));ins!("flatpak_installation",Value::String(installation.into()));ins!("_releases_last_year",Value::Number(release_count_last_year_rs(component,now).into()));Some(m)
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

#[pyfunction]
pub(crate) fn normalize_native_appstream_components(py: Python<'_>, components: &Bound<'_, PyList>) -> PyResult<Vec<Py<PyAny>>> {
    let mut out = Vec::with_capacity(components.len());
    for obj in components.iter() {
        let Value::Object(map) = py_to_json(&obj)? else { continue; };
        if let Some(normalized) = normalize_native_payload_rs(map) {
            out.push(json_to_py(py, &Value::Object(normalized))?);
        }
    }
    Ok(out)
}

#[pyfunction]
pub(crate) fn parse_flatpak_appstream_source(py:Python<'_>, path:&str, source_json:&str, eol_ids:Vec<String>, now:i64)->PyResult<Vec<Py<PyAny>>>{
    use std::io::Read; let mut bytes=Vec::new(); if path.ends_with(".gz"){let file=match fs::File::open(path){Ok(v)=>v,Err(_)=>return Ok(vec![])};let mut gz=flate2::read::GzDecoder::new(file);if gz.read_to_end(&mut bytes).is_err(){return Ok(vec![])}}else{bytes=match fs::read(path){Ok(v)=>v,Err(_)=>return Ok(vec![])}};
    let root=match parse_xml_tree(&bytes){Ok(v)=>v,Err(_)=>return Ok(vec![])};let mut source:serde_json::Map<String,Value>=serde_json::from_str::<Value>(source_json).ok().and_then(|v|v.as_object().cloned()).unwrap_or_default();if source.get("media_baseurl").and_then(Value::as_str).unwrap_or("").is_empty(){if let Some(v)=root.attrs.get("media_baseurl").or_else(||root.attrs.get("media-baseurl")){source.insert("media_baseurl".into(),Value::String(v.clone()));}}
    let eol:std::collections::HashSet<String>=eol_ids.into_iter().collect();let mut out=Vec::new();for c in root.children_named("component"){if let Some(m)=normalize_flatpak_component_rs(c,&source,&eol,now){out.push(json_to_py(py,&Value::Object(m))?);}}Ok(out)
}



#[pyfunction]
pub(crate) fn reconcile_appstream_components(
    py: Python<'_>,
    previous: &Bound<'_, PyList>,
    current: &Bound<'_, PyList>,
) -> PyResult<Vec<Py<PyAny>>> {
    // Reconciliation is deliberately data-only: Python decides whether the
    // previous catalog is schema-compatible, while Rust indexes it and reuses
    // unchanged normalized entries by identity + metadata hash.
    let mut previous_by_identity: std::collections::HashMap<String, serde_json::Map<String, Value>> =
        std::collections::HashMap::with_capacity(previous.len());
    for obj in previous.iter() {
        let Value::Object(map) = py_to_json(&obj)? else { continue; };
        let identity = map.get("identity").and_then(Value::as_str).unwrap_or("");
        if !identity.is_empty() {
            previous_by_identity.insert(identity.to_string(), map);
        }
    }

    let mut reconciled: Vec<serde_json::Map<String, Value>> = Vec::with_capacity(current.len());
    for obj in current.iter() {
        let Value::Object(map) = py_to_json(&obj)? else { continue; };
        let identity = map.get("identity").and_then(Value::as_str).unwrap_or("");
        let metadata_hash = map.get("_metadata_hash").and_then(Value::as_str).unwrap_or("");
        let source = map.get("source").and_then(Value::as_str).unwrap_or("");

        let reused = if !identity.is_empty() && !metadata_hash.is_empty() {
            previous_by_identity.get(identity).filter(|old| {
                old.get("source").and_then(Value::as_str).unwrap_or("") == source
                    && old.get("_metadata_hash").and_then(Value::as_str).unwrap_or("") == metadata_hash
            }).cloned()
        } else {
            None
        };
        reconciled.push(reused.unwrap_or(map));
    }

    // Keep publication deterministic without another Python-wide sort pass.
    reconciled.sort_by(|a, b| {
        let an = a.get("name").and_then(Value::as_str).unwrap_or("").to_lowercase();
        let bn = b.get("name").and_then(Value::as_str).unwrap_or("").to_lowercase();
        an.cmp(&bn).then_with(|| {
            a.get("id").and_then(Value::as_str).unwrap_or("")
                .cmp(b.get("id").and_then(Value::as_str).unwrap_or(""))
        })
    });

    let mut out = Vec::with_capacity(reconciled.len());
    for map in reconciled {
        out.push(json_to_py(py, &Value::Object(map))?);
    }
    Ok(out)
}

#[pyfunction]
pub(crate) fn build_appstream_catalog(
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
) -> PyResult<Vec<Py<PyAny>>> {
    let content = match fs::read_to_string(path) { Ok(v) => v, Err(_) => return Ok(Vec::new()) };
    let parsed: Value = match serde_json::from_str(&content) { Ok(v) => v, Err(_) => return Ok(Vec::new()) };
    let Some(values) = parsed.as_array() else { return Ok(Vec::new()); };
    let omit: std::collections::HashSet<String> = omit_keys.into_iter().map(|s| s.trim().to_lowercase()).collect();
    let mut vals = Vec::with_capacity(values.len());
    for value in values {
        let Some(m) = value.as_object() else { continue; };
        if !m.get("packages").and_then(Value::as_array).is_some_and(|a| !a.is_empty()) { continue; }
        let mut keys = Vec::new();
        if let Some(id)=m.get("id").and_then(Value::as_str) { keys.push(normalize_id(id)); }
        if let Some(id)=m.get("flatpak_id").and_then(Value::as_str) { keys.push(normalize_id(id)); }
        if let Some(name)=m.get("name").and_then(Value::as_str) { keys.push(name.trim().to_lowercase()); }
        if let Some(pkgs)=m.get("packages").and_then(Value::as_array) { for p in pkgs.iter().filter_map(Value::as_str) { keys.push(p.trim().to_lowercase()); } }
        if keys.iter().any(|k| omit.contains(k)) { continue; }
        vals.push(m.clone());
    }
    let cfg:Value=serde_json::from_str(category_config_json).unwrap_or(Value::Null);
    let prefs:Value=serde_json::from_str(source_preferences_json).unwrap_or_else(|_|serde_json::json!({"default":"flatpak","apps":{}}));
    let locks=system_flatpak_locks.into_iter().map(|s|normalize_id(&s)).collect();
    let host_os=host_os_keys.into_iter().map(|s|s.to_lowercase()).collect();
    let compat:std::collections::HashSet<String>=compat_keys.into_iter().map(|s|s.to_lowercase()).collect();
    let prefer_native=compat.iter().any(|s|matches!(s.as_str(),"arch"|"cachy"|"solus"|"fedora"));
    let steamos=compat.contains("steamos");
    let first=collapse_source_groups_rs(vals,&category_paths,&cfg,&prefs,&locks,&host_os,prefer_native,steamos,false);
    let selected=collapse_source_groups_rs(first,&category_paths,&cfg,&prefs,&locks,&host_os,prefer_native,steamos,true);
    let result = adapt_appstream_maps_values(selected,category_paths,category_config_json,lang,curated_ids,curated_packages,curated_names,overlays_json,native_badge);
    result.iter().map(|value| json_to_py(py, value)).collect()
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
    description_lower: String,
    developer_lower: String,
    is_new: bool,
    review_rating: Option<f64>,
    review_subscore: Option<i64>,
    category_popularity_score: Option<i64>,
    category_native_score: Option<i64>,
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
        let description_lower = value.get("description").and_then(Value::as_str).unwrap_or("").to_lowercase();
        let developer_lower = value.get("developer").and_then(Value::as_str).unwrap_or("").to_lowercase();
        let is_new = value.get("is_new").and_then(Value::as_bool).unwrap_or(false);
        let review_rating = value.get("review_rating").and_then(Value::as_f64);
        let review_subscore = value.get("review_subscore").and_then(Value::as_i64);
        let category_popularity_score = value.get("_category_popularity_score").and_then(Value::as_i64);
        let category_native_score = value.get("_category_native_score").and_then(Value::as_i64);
        let payload = rmp_serde::to_vec_named(&value).ok()?;
        Some(Self {
            category, appstream_id, name, canonical_name, source, package_names,
            search_packages, description_lower, developer_lower, is_new,
            review_rating, review_subscore, category_popularity_score,
            category_native_score, payload,
        })
    }

    fn decode(&self) -> Option<Value> {
        rmp_serde::from_slice(&self.payload).ok()
    }
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
                "native" => Some(&mut by_native_package),
                _ => None,
            };
            if let Some(target) = target {
                for package in &entry.package_names { target.entry(package.clone()).or_default().push(index); }
            }
        }
        Self { entries, by_category, by_id, by_name, by_removable_name, by_native_package, by_flatpak_package, cache_key }
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

    fn search(&self, py: Python<'_>, query: &str, translated_new: &str, translated_official: &str) -> PyResult<Vec<(Py<PyAny>, i64)>> {
        let query = query.trim().to_lowercase();
        if query.is_empty() { return Ok(Vec::new()); }
        let translated_new = translated_new.trim().to_lowercase();
        let _translated_official = translated_official.trim().to_lowercase();
        let mut matches = Vec::new();

        for (index, entry) in self.entries.iter().enumerate() {
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
            let Some(rating) = entry.review_rating.filter(|rating| *rating >= 70.0) else {
                continue;
            };
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
                "review_rating": rating,
                "review_subscore": entry.review_subscore,
                "_category_popularity_score": entry.category_popularity_score,
                "_category_native_score": entry.category_native_score,
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

    fn installed_entries(&self, py: Python<'_>, native_packages: Vec<String>, flatpak_ids: Vec<String>, executed_names: Vec<String>) -> PyResult<Vec<Py<PyAny>>> {
        let mut indices = std::collections::HashSet::new();
        for package in native_packages {
            let key = package.trim().to_lowercase();
            if let Some(matches) = self.by_native_package.get(&key) { indices.extend(matches.iter().copied()); }
        }
        for app_id in flatpak_ids {
            let key = app_id.trim().to_lowercase();
            if let Some(matches) = self.by_flatpak_package.get(&key) { indices.extend(matches.iter().copied()); }
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

const RUNTIME_CACHE_SCHEMA: u32 = 4;

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
    cache_path: &str,
    cache_key: &str,
    force_rebuild: bool,
) -> PyResult<AppStreamCatalog> {
    // A warm cache is immediately usable even when its key is stale.  Normal UI
    // callers keep using that last complete snapshot while the refresh worker
    // rebuilds the new generation with force_rebuild=true.  Publication below is
    // atomic, so readers can only ever observe a complete old or new cache.
    if !force_rebuild {
        if let Some(payload) = load_binary_catalog_cache(cache_path) {
            return Ok(AppStreamCatalog::from_entries(payload.entries, payload.key));
        }
    } else if let Some(payload) = load_binary_catalog_cache(cache_path) {
        if payload.key == cache_key {
            return Ok(AppStreamCatalog::from_entries(payload.entries, payload.key));
        }
    }

    let content = match fs::read_to_string(path) { Ok(v) => v, Err(_) => return Ok(AppStreamCatalog::from_values(Vec::new(), cache_key.to_string())) };
    let parsed: Value = match serde_json::from_str(&content) { Ok(v) => v, Err(_) => return Ok(AppStreamCatalog::from_values(Vec::new(), cache_key.to_string())) };
    let Some(values) = parsed.as_array() else { return Ok(AppStreamCatalog::from_values(Vec::new(), cache_key.to_string())); };
    let omit: std::collections::HashSet<String> = omit_keys.into_iter().map(|s| s.trim().to_lowercase()).collect();
    let mut vals = Vec::with_capacity(values.len());
    for value in values {
        let Some(m) = value.as_object() else { continue; };
        if !m.get("packages").and_then(Value::as_array).is_some_and(|a| !a.is_empty()) { continue; }
        let mut keys = Vec::new();
        if let Some(id)=m.get("id").and_then(Value::as_str) { keys.push(normalize_id(id)); }
        if let Some(id)=m.get("flatpak_id").and_then(Value::as_str) { keys.push(normalize_id(id)); }
        if let Some(name)=m.get("name").and_then(Value::as_str) { keys.push(name.trim().to_lowercase()); }
        if let Some(pkgs)=m.get("packages").and_then(Value::as_array) { for p in pkgs.iter().filter_map(Value::as_str) { keys.push(p.trim().to_lowercase()); } }
        if keys.iter().any(|k| omit.contains(k)) { continue; }
        vals.push(m.clone());
    }
    let cfg:Value=serde_json::from_str(category_config_json).unwrap_or(Value::Null);
    let prefs:Value=serde_json::from_str(source_preferences_json).unwrap_or_else(|_|serde_json::json!({"default":"flatpak","apps":{}}));
    let locks=system_flatpak_locks.into_iter().map(|s|normalize_id(&s)).collect();
    let host_os=host_os_keys.into_iter().map(|s|s.to_lowercase()).collect();
    let compat:std::collections::HashSet<String>=compat_keys.into_iter().map(|s|s.to_lowercase()).collect();
    let prefer_native=compat.iter().any(|s|matches!(s.as_str(),"arch"|"cachy"|"solus"|"fedora"));
    let steamos=compat.contains("steamos");
    let first=collapse_source_groups_rs(vals,&category_paths,&cfg,&prefs,&locks,&host_os,prefer_native,steamos,false);
    let selected=collapse_source_groups_rs(first,&category_paths,&cfg,&prefs,&locks,&host_os,prefer_native,steamos,true);
    let entries=adapt_appstream_maps_values(selected,category_paths,category_config_json,lang,curated_ids,curated_packages,curated_names,overlays_json,native_badge);

    let runtime_entries: Vec<RuntimeAppStreamEntry> = entries.into_iter().filter_map(RuntimeAppStreamEntry::from_value).collect();
    write_binary_catalog_cache(cache_path, cache_key, &runtime_entries);
    Ok(AppStreamCatalog::from_entries(runtime_entries, cache_key.to_string()))
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
