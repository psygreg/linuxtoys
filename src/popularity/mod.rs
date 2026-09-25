use pyo3::prelude::*;

const SCORE_MAX: i64 = 999;
const REVIEW_CONFIDENCE_COUNT: f64 = 10.0;

#[pyfunction]
pub(crate) fn review_subscores(rows: Vec<(Option<f64>, Option<i64>)>) -> Vec<Option<i64>> {
    let valid: Vec<(usize, f64, i64)> = rows
        .iter()
        .enumerate()
        .filter_map(|(index, (rating, count))| {
            let rating = (*rating)?;
            let count = (*count)?;
            if count > 0 && (0.0..=100.0).contains(&rating) {
                Some((index, rating, count))
            } else {
                None
            }
        })
        .collect();

    let mut out = vec![None; rows.len()];
    if valid.is_empty() {
        return out;
    }

    let total_reviews: i64 = valid.iter().map(|(_, _, count)| *count).sum();
    let prior = if total_reviews > 0 {
        valid.iter().map(|(_, rating, count)| rating * (*count as f64)).sum::<f64>()
            / total_reviews as f64
    } else {
        50.0
    };

    for (index, rating, count) in valid {
        let count = count as f64;
        let weighted = ((count * rating) + (REVIEW_CONFIDENCE_COUNT * prior))
            / (count + REVIEW_CONFIDENCE_COUNT);
        out[index] = Some(((weighted / 100.0) * SCORE_MAX as f64).round() as i64);
    }
    out
}

fn section_for_rank(index: usize, count: usize) -> i64 {
    if count == 1 {
        5
    } else if count < 10 {
        ((index as f64) * 9.0 / ((count - 1) as f64)).round() as i64
    } else {
        ((index * 10) / count).min(9) as i64
    }
}

#[pyfunction]
pub(crate) fn metric_rank_sections(mut rows: Vec<(usize, f64, String)>) -> Vec<(usize, i64)> {
    rows.sort_by(|a, b| {
        a.1.total_cmp(&b.1).then_with(|| a.2.cmp(&b.2))
    });
    let count = rows.len();
    rows.into_iter()
        .enumerate()
        .map(|(rank, (index, _, _))| (index, section_for_rank(rank, count)))
        .collect()
}

#[pyfunction]
pub(crate) fn native_rank_sections(
    rows: Vec<(usize, Option<i64>, String, f64)>,
) -> Vec<(usize, i64)> {
    if rows.is_empty() {
        return Vec::new();
    }

    let mut reviewed: Vec<(i64, String, usize)> = Vec::new();
    let mut unreviewed: Vec<(f64, usize)> = Vec::new();
    for (index, review, key, order) in rows {
        if let Some(review) = review {
            reviewed.push((review, key, index));
        } else {
            unreviewed.push((order, index));
        }
    }
    reviewed.sort_by(|a, b| a.0.cmp(&b.0).then_with(|| a.1.cmp(&b.1)));
    unreviewed.sort_by(|a, b| a.0.total_cmp(&b.0));

    let ranked_reviewed: Vec<usize> = reviewed.into_iter().map(|(_, _, index)| index).collect();
    let ranked_unknown: Vec<usize> = unreviewed.into_iter().map(|(_, index)| index).collect();
    let total = ranked_reviewed.len() + ranked_unknown.len();

    let ranked = if ranked_reviewed.is_empty() {
        ranked_unknown
    } else if ranked_unknown.is_empty() {
        ranked_reviewed
    } else {
        let unknown_len = ranked_unknown.len();
        let mut ranked = Vec::with_capacity(total);
        let mut reviewed_i = 0usize;
        let mut unknown_i = 0usize;
        for index in 0..total {
            let expected_unknown = ((index + 1) * unknown_len) / total;
            if unknown_i < expected_unknown {
                ranked.push(ranked_unknown[unknown_i]);
                unknown_i += 1;
            } else if reviewed_i < ranked_reviewed.len() {
                ranked.push(ranked_reviewed[reviewed_i]);
                reviewed_i += 1;
            } else {
                ranked.push(ranked_unknown[unknown_i]);
                unknown_i += 1;
            }
        }
        ranked
    };

    ranked.into_iter()
        .enumerate()
        .map(|(rank, index)| (index, section_for_rank(rank, total)))
        .collect()
}

#[pyfunction]
pub(crate) fn flathub_metric(downloads: i64, releases_last_year: i64) -> f64 {
    let downloads = downloads.max(0) as f64;
    let releases = releases_last_year.max(1) as f64;
    downloads / releases
}
