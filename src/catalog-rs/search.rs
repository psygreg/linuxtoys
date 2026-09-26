use pyo3::prelude::*;

#[derive(Clone, Debug)]
struct SearchRow {
    name: String,
    description: String,
    developer: String,
    aliases: Vec<String>,
    packages: Vec<String>,
    is_new: bool,
    is_official: bool,
}

#[pyclass]
pub(crate) struct SearchIndex {
    rows: Vec<SearchRow>,
}

#[pyfunction]
pub(crate) fn build_search_index(
    rows: Vec<(String, String, String, Vec<String>, Vec<String>, bool, bool)>,
) -> SearchIndex {
    SearchIndex {
        rows: rows.into_iter().map(|(name, description, developer, aliases, packages, is_new, is_official)| SearchRow {
            name, description, developer, aliases, packages, is_new, is_official,
        }).collect(),
    }
}

#[pyfunction]
pub(crate) fn search_index(
    index: PyRef<'_, SearchIndex>,
    query: &str,
    translated_new: &str,
    translated_official: &str,
) -> Vec<(usize, i64)> {
    let mut out = Vec::new();

    for (row_index, row) in index.rows.iter().enumerate() {
        let mut score = 0i64;

        if (query == "new" || query == translated_new) && row.is_new {
            score += 90;
        }
        if (query == "official" || query == translated_official) && row.is_official {
            score += 90;
        }

        if query == row.name {
            score += 100;
        } else if row.name.starts_with(query) {
            score += 80;
        } else if row.name.contains(query) {
            score += 60;
        }

        if row.aliases.iter().any(|alias| alias.contains(query)) {
            score += 60;
        }

        if row.packages.iter().any(|package| package == query) {
            score += 90;
        } else if row.packages.iter().any(|package| package.starts_with(query)) {
            score += 70;
        } else if row.packages.iter().any(|package| package.contains(query)) {
            score += 50;
        }

        if query == row.developer {
            score += 55;
        } else if row.developer.starts_with(query) {
            score += 45;
        } else if row.developer.contains(query) {
            score += 40;
        }

        if row.description.contains(query) {
            score += 30;
        }

        // Python len() counts Unicode code points, matching Rust chars().count().
        if score > 0 && row.name.chars().count() < 20 {
            score += 5;
        }

        if score > 0 {
            out.push((row_index, score));
        }
    }

    out
}
