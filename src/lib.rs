use pyo3::prelude::*;

mod repo;
mod appstream;
mod popularity;
mod search;
mod scripts;

#[pymodule]
fn _catalog_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(repo::file_signature, m)?)?;
    m.add_function(wrap_pyfunction!(repo::repo_app_id, m)?)?;
    m.add_function(wrap_pyfunction!(repo::normalize_appstream_overlay_id, m)?)?;
    m.add_function(wrap_pyfunction!(repo::scan_repo_tree, m)?)?;
    m.add_function(wrap_pyfunction!(repo::load_json_entries, m)?)?;
    m.add_function(wrap_pyfunction!(repo::load_markdown_text, m)?)?;
    m.add_function(wrap_pyfunction!(repo::safe_join_below, m)?)?;
    m.add_function(wrap_pyfunction!(repo::prefilter_repo_entries, m)?)?;
    m.add_function(wrap_pyfunction!(repo::build_repo_catalog, m)?)?;
    m.add_function(wrap_pyfunction!(appstream::load_appstream_catalog, m)?)?;
    m.add_function(wrap_pyfunction!(appstream::normalize_native_appstream_components, m)?)?;
    m.add_function(wrap_pyfunction!(appstream::parse_flatpak_appstream_source, m)?)?;
    m.add_function(wrap_pyfunction!(appstream::reconcile_appstream_components, m)?)?;
    m.add_function(wrap_pyfunction!(appstream::build_appstream_catalog, m)?)?;
    m.add_function(wrap_pyfunction!(popularity::review_subscores, m)?)?;
    m.add_function(wrap_pyfunction!(popularity::metric_rank_sections, m)?)?;
    m.add_function(wrap_pyfunction!(popularity::native_rank_sections, m)?)?;
    m.add_function(wrap_pyfunction!(popularity::flathub_metric, m)?)?;
    m.add_function(wrap_pyfunction!(search::build_search_index, m)?)?;
    m.add_function(wrap_pyfunction!(search::search_index, m)?)?;
    m.add_function(wrap_pyfunction!(scripts::build_script_tree_index, m)?)?;
    Ok(())
}
