use pyo3::prelude::*;
use std::collections::hash_map::DefaultHasher;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::sync::{Mutex, OnceLock};
use std::time::{SystemTime, UNIX_EPOCH};

const SCORE_MAX: i64 = 999;
const REVIEW_CONFIDENCE_COUNT: f64 = 10.0;

const SCORE_MIN: i64 = 0;

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

/// Resolve a direct browse score. AppStream uses its Bayesian ODRS subscore.
#[pyfunction]
pub(crate) fn score_for_item(
    key: &str,
    known_popular: bool,
    kind: u8,
    review_score: Option<i64>,
) -> i64 {
    if known_popular || kind == 3 {
        return SCORE_MAX;
    }
    if kind == 1 {
        return review_score.unwrap_or(SCORE_MIN).clamp(SCORE_MIN, SCORE_MAX);
    }
    generated_session_score(key, SCORE_MIN, SCORE_MAX)
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
