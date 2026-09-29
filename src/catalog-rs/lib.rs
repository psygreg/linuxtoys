use pyo3::prelude::*;

mod repo;
mod appstream;
mod popularity;
mod featured;
mod search;
mod scripts;
mod snap_ratings;

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
    m.add_function(wrap_pyfunction!(appstream::build_appstream_catalog_index, m)?)?;
    m.add_function(wrap_pyfunction!(appstream::source_metadata_fingerprint, m)?)?;
    m.add_class::<appstream::AppStreamGeneration>()?;
    m.add_class::<appstream::AppStreamCatalog>()?;
    m.add_function(wrap_pyfunction!(popularity::review_subscores, m)?)?;
    m.add_function(wrap_pyfunction!(popularity::featured_weighted_sample, m)?)?;
    m.add_function(wrap_pyfunction!(popularity::session_random_score, m)?)?;
    m.add_function(wrap_pyfunction!(popularity::score_for_item, m)?)?;
    m.add_function(wrap_pyfunction!(featured::featured_large_count, m)?)?;
    m.add_function(wrap_pyfunction!(featured::featured_layout_plan, m)?)?;
    m.add_function(wrap_pyfunction!(featured::app_page_featured_rank, m)?)?;
    m.add_function(wrap_pyfunction!(search::build_search_index, m)?)?;
    m.add_function(wrap_pyfunction!(search::search_index, m)?)?;
    m.add_function(wrap_pyfunction!(scripts::build_script_tree_index, m)?)?;
    m.add_function(wrap_pyfunction!(snap_ratings::snap_bulk_ratings, m)?)?;
    m.add_function(wrap_pyfunction!(snap_ratings::snap_user_vote, m)?)?;
    m.add_function(wrap_pyfunction!(snap_ratings::submit_snap_vote, m)?)?;
    Ok(())
}
