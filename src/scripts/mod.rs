use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

#[derive(Default)]
struct TreeIndex {
    directories: Vec<DirectoryData>,
    all_scripts: Vec<String>,
    script_data: Vec<ScriptData>,
}

struct DirectoryData {
    path: String,
    dirs: Vec<String>,
    scripts: Vec<String>,
    files: Vec<String>,
    entries: Vec<(String, String)>,
}

struct ScriptData {
    path: String,
    mtime_ns: u128,
    size: u64,
    content: String,
    header_lines: Vec<String>,
    headers: HashMap<String, String>,
}

fn skip_directory(name: &str) -> bool {
    name.starts_with('.') || name == "lists"
}

fn path_string(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

fn parse_script(path: &Path) -> Option<ScriptData> {
    let metadata = fs::metadata(path).ok()?;
    let content = fs::read_to_string(path).unwrap_or_default();
    let mtime_ns = metadata
        .modified()
        .ok()
        .and_then(|time| time.duration_since(UNIX_EPOCH).ok())
        .map(|duration| duration.as_nanos())
        .unwrap_or(0);

    let mut header_lines = Vec::new();
    let mut headers = HashMap::new();
    for line in content.lines() {
        if !line.starts_with('#') {
            break;
        }
        header_lines.push(line.to_string());
        if let Some(rest) = line.strip_prefix("# ") {
            if let Some((key, value)) = rest.trim().split_once(':') {
                headers.insert(key.trim().to_lowercase(), value.trim().to_string());
            }
        }
    }

    Some(ScriptData {
        path: path_string(path),
        mtime_ns,
        size: metadata.len(),
        content,
        header_lines,
        headers,
    })
}

fn scan_directory(path: &Path, index: &mut TreeIndex) {
    let read_dir = match fs::read_dir(path) {
        Ok(value) => value,
        Err(_) => return,
    };

    let mut child_dirs: Vec<(String, PathBuf)> = Vec::new();
    let mut script_names = Vec::new();
    let mut files = Vec::new();
    let mut entries = Vec::new();

    for entry in read_dir.flatten() {
        let name = entry.file_name().to_string_lossy().into_owned();
        let file_type = match entry.file_type() {
            Ok(value) => value,
            Err(_) => continue,
        };

        if file_type.is_dir() {
            if skip_directory(&name) {
                continue;
            }
            child_dirs.push((name.clone(), entry.path()));
            entries.push(("dir".to_string(), name));
            continue;
        }

        if !file_type.is_file() {
            continue;
        }

        files.push(name.clone());
        if name.ends_with(".sh") {
            script_names.push(name.clone());
            entries.push(("script".to_string(), name));
        }
    }

    let directory_path = path_string(path);
    index.directories.push(DirectoryData {
        path: directory_path,
        dirs: child_dirs.iter().map(|(name, _)| name.clone()).collect(),
        scripts: script_names.clone(),
        files,
        entries,
    });

    // Match the previous Python index: scripts in this directory are recorded
    // before descending into children.
    for file_name in script_names {
        let script_path = path.join(&file_name);
        let script_path_string = path_string(&script_path);
        index.all_scripts.push(script_path_string.clone());
        if let Some(data) = parse_script(&script_path) {
            index.script_data.push(data);
        }
    }

    for (_, child_path) in child_dirs {
        scan_directory(&child_path, index);
    }
}

#[pyfunction]
pub(crate) fn build_script_tree_index(py: Python<'_>, root_path: &str) -> PyResult<PyObject> {
    let root = PathBuf::from(root_path);
    let mut index = TreeIndex::default();

    if root.is_dir() {
        scan_directory(&root, &mut index);
    }

    let result = PyDict::new(py);
    result.set_item("root", path_string(&root))?;

    let directories = PyDict::new(py);
    for directory in index.directories {
        let value = PyDict::new(py);
        value.set_item("dirs", directory.dirs)?;
        value.set_item("scripts", directory.scripts)?;
        value.set_item("files", directory.files)?;
        value.set_item("entries", directory.entries)?;
        directories.set_item(directory.path, value)?;
    }
    result.set_item("directories", directories)?;
    result.set_item("all_scripts", index.all_scripts)?;

    let script_data = PyList::empty(py);
    for data in index.script_data {
        let value = PyDict::new(py);
        value.set_item("path", data.path)?;
        value.set_item("signature", (data.mtime_ns, data.size))?;
        value.set_item("content", data.content)?;
        value.set_item("header_lines", data.header_lines)?;
        value.set_item("headers", data.headers)?;
        script_data.append(value)?;
    }
    result.set_item("script_data", script_data)?;

    Ok(result.into())
}
