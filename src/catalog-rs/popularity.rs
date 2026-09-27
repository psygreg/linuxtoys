use pyo3::prelude::*;
use std::collections::HashMap;
use std::hash::{DefaultHasher, Hash, Hasher};
use std::sync::{Mutex, OnceLock};
use std::time::{SystemTime, UNIX_EPOCH};

const SCORE_MAX: i64 = 999;
const REVIEW_CONFIDENCE_COUNT: f64 = 10.0;

const SCORE_MIN: i64 = 0;
const TOP_SECTION_MIN: i64 = 900;

static SESSION_SCORES: OnceLock<Mutex<HashMap<String, i64>>> = OnceLock::new();
static SESSION_SEED: OnceLock<u64> = OnceLock::new();

fn session_seed() -> u64 {
    *SESSION_SEED.get_or_init(|| {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|duration| {
                (duration.as_nanos() as u64)
                    ^ (std::process::id() as u64).rotate_left(17)
            })
            .unwrap_or(0x6a09e667f3bcc909)
    })
}

fn generated_session_score(key: &str, low: i64, high: i64) -> i64 {
    let low = low.min(high);
    let high = high.max(low);
    let scores = SESSION_SCORES.get_or_init(|| Mutex::new(HashMap::new()));
    let mut scores = scores.lock().unwrap_or_else(|poisoned| poisoned.into_inner());

    if let Some(score) = scores.get(key) {
        return *score;
    }

    let mut hasher = DefaultHasher::new();
    session_seed().hash(&mut hasher);
    key.hash(&mut hasher);
    let span = (high - low + 1) as u64;
    let score = low + (hasher.finish() % span) as i64;
    scores.insert(key.to_owned(), score);
    score
}

/// Session-stable random score used by Python's remaining category-distribution
/// code. The first range requested for a key wins, matching the previous
/// `_SESSION_SCORES` dictionary semantics.
#[pyfunction]
pub(crate) fn session_random_score(key: &str, low: i64, high: i64) -> i64 {
    generated_session_score(key, low, high)
}

/// Resolve the effective 0..999 popularity score for one already-classified item.
///
/// `kind`: 1 = Flatpak AppStream, 2 = native AppStream, 3 = curated LinuxToys,
/// 0 = other. Known-popular overrides every kind.
#[pyfunction]
pub(crate) fn score_for_item(
    key: &str,
    known_popular: bool,
    kind: u8,
    category_popularity_score: Option<i64>,
    category_native_score: Option<i64>,
) -> i64 {
    if known_popular {
        return generated_session_score(key, TOP_SECTION_MIN, SCORE_MAX);
    }

    match kind {
        1 => category_popularity_score
            .map(|value| value.clamp(SCORE_MIN, SCORE_MAX))
            .unwrap_or_else(|| {
                generated_session_score(key, SCORE_MIN, TOP_SECTION_MIN - 1)
            }),
        2 => {
            if let Some(value) = category_popularity_score {
                return value.clamp(SCORE_MIN, SCORE_MAX);
            }
            category_native_score
                .map(|value| value.clamp(SCORE_MIN, SCORE_MAX))
                .unwrap_or_else(|| generated_session_score(key, SCORE_MIN, SCORE_MAX))
        }
        3 => generated_session_score(key, TOP_SECTION_MIN, SCORE_MAX),
        _ => generated_session_score(key, SCORE_MIN, TOP_SECTION_MIN - 1),
    }
}

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


/// Sequential weighted sampling without replacement using weights computed once
/// by Python and random unit draws supplied by Python's existing RNG.
#[pyfunction]
pub(crate) fn featured_weighted_sample(
    weights: Vec<f64>,
    draws: Vec<f64>,
    count: usize,
) -> Vec<usize> {
    let mut pool: Vec<(usize, f64)> = weights
        .into_iter()
        .enumerate()
        .map(|(index, weight)| {
            let weight = if weight.is_finite() && weight > 0.0 { weight } else { 0.0 };
            (index, weight)
        })
        .collect();

    let wanted = count.min(pool.len()).min(draws.len());
    let mut selected = Vec::with_capacity(wanted);

    for draw in draws.into_iter().take(wanted) {
        let total: f64 = pool.iter().map(|(_, weight)| *weight).sum();
        if total <= 0.0 || !total.is_finite() {
            break;
        }

        let unit = if draw.is_finite() {
            draw.clamp(0.0, 1.0 - f64::EPSILON)
        } else {
            0.0
        };
        let target = unit * total;
        let mut cumulative = 0.0;
        let mut chosen = None;

        for (position, (_, weight)) in pool.iter().enumerate() {
            cumulative += *weight;
            if *weight > 0.0 && target < cumulative {
                chosen = Some(position);
                break;
            }
        }

        let position = chosen.or_else(|| pool.iter().rposition(|(_, weight)| *weight > 0.0));
        let Some(position) = position else { break; };
        let (original_index, _) = pool.remove(position);
        selected.push(original_index);
    }

    selected
}
