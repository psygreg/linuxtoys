use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::sync::OnceLock;

#[derive(Clone)]
struct SmallRng(u64);

impl SmallRng {
    fn new(seed: u64) -> Self {
        Self(if seed == 0 { 0x9E37_79B9_7F4A_7C15 } else { seed })
    }

    fn next_u64(&mut self) -> u64 {
        // xorshift64*: tiny, deterministic, and dependency-free. Python supplies
        // the session-random seed; Rust only expands it for one layout plan.
        let mut x = self.0;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.0 = x;
        x.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }

    fn unit(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 * (1.0 / ((1u64 << 53) as f64))
    }

    fn shuffle<T>(&mut self, values: &mut [T]) {
        for i in (1..values.len()).rev() {
            let j = (self.next_u64() as usize) % (i + 1);
            values.swap(i, j);
        }
    }
}

fn weighted_sample(indices: &[usize], weights: &[f64], count: usize, rng: &mut SmallRng) -> Vec<usize> {
    let mut pool: Vec<(usize, f64)> = indices
        .iter()
        .copied()
        .zip(weights.iter().copied())
        .map(|(index, weight)| {
            (index, if weight.is_finite() && weight > 0.0 { weight } else { 0.0 })
        })
        .collect();

    let mut selected = Vec::with_capacity(count.min(pool.len()));
    for _ in 0..count.min(pool.len()) {
        let total: f64 = pool.iter().map(|(_, weight)| *weight).sum();
        if total <= 0.0 || !total.is_finite() {
            break;
        }
        let target = rng.unit() * total;
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
        selected.push(pool.remove(position).0);
    }
    selected
}

fn occupied_cells(position: (i32, i32)) -> [(i32, i32); 2] {
    [(position.0, position.1), (position.0, position.1 + 1)]
}

fn overlaps(position: (i32, i32), chosen: &[(i32, i32)]) -> bool {
    chosen.iter().any(|&(column, row)| {
        position.0 == column && !(position.1 + 1 < row || row + 1 < position.1)
    })
}

fn find_layout(
    candidates: &[(i32, i32)],
    count: usize,
    rng: &mut SmallRng,
) -> Option<Vec<(i32, i32)>> {
    let mut candidates = candidates.to_vec();
    rng.shuffle(&mut candidates);

    fn search(
        candidates: &[(i32, i32)],
        count: usize,
        index: usize,
        chosen: &mut Vec<(i32, i32)>,
    ) -> bool {
        if chosen.len() == count {
            return true;
        }
        if candidates.len().saturating_sub(index) < count.saturating_sub(chosen.len()) {
            return false;
        }
        for candidate_index in index..candidates.len() {
            let candidate = candidates[candidate_index];
            if overlaps(candidate, chosen) {
                continue;
            }
            chosen.push(candidate);
            if search(candidates, count, candidate_index + 1, chosen) {
                return true;
            }
            chosen.pop();
        }
        false
    }

    let mut chosen = Vec::with_capacity(count);
    if search(&candidates, count, 0, &mut chosen) {
        Some(chosen)
    } else {
        None
    }
}

fn choose_large_positions(
    rows: i32,
    columns: i32,
    count: usize,
    previous: &[(i32, i32)],
    rng: &mut SmallRng,
) -> Vec<(i32, i32)> {
    if count == 0 || rows < 2 || columns <= 0 {
        return Vec::new();
    }

    let previous_set: HashSet<(i32, i32)> = previous.iter().copied().collect();
    let all_positions: Vec<(i32, i32)> = (0..columns)
        .flat_map(|column| (0..rows - 1).map(move |row| (column, row)))
        .collect();
    let fresh_positions: Vec<(i32, i32)> = all_positions
        .iter()
        .copied()
        .filter(|position| !previous_set.contains(position))
        .collect();

    let mut layouts = Vec::new();
    for _ in 0..32 {
        if let Some(layout) = find_layout(&fresh_positions, count, rng) {
            layouts.push(layout);
        }
    }
    if layouts.is_empty() {
        for _ in 0..32 {
            if let Some(layout) = find_layout(&all_positions, count, rng) {
                layouts.push(layout);
            }
        }
    }
    if layouts.is_empty() {
        return Vec::new();
    }

    let previous_cells: HashSet<(i32, i32)> = previous
        .iter()
        .flat_map(|&position| occupied_cells(position))
        .collect();

    let changed = |layout: &[(i32, i32)]| -> usize {
        let cells: HashSet<(i32, i32)> = layout
            .iter()
            .flat_map(|&position| occupied_cells(position))
            .collect();
        previous_cells.symmetric_difference(&cells).count()
    };

    let best_cost = layouts.iter().map(|layout| changed(layout)).min().unwrap_or(0);
    let mut best: Vec<Vec<(i32, i32)>> = layouts
        .into_iter()
        .filter(|layout| changed(layout) == best_cost)
        .collect();
    let pick = (rng.next_u64() as usize) % best.len();
    best.swap_remove(pick)
}

/// Large-card allowance for a settled Featured grid.
///
/// Base behavior is preserved, with the newer density bonuses:
/// >4 rows: flat +2 and +1 per two columns
/// >6 rows: another +1 per two columns.
#[pyfunction]
pub(crate) fn featured_large_count(rows: i32, columns: i32, eligible_count: usize) -> usize {
    let rows = rows.max(0);
    let columns = columns.max(0);
    let mut max_large = if rows >= 9 {
        3.max(columns)
    } else {
        3.min(rows / 2)
    };

    if rows > 4 {
        max_large += 2;
        max_large += columns / 2;
    }
    if rows > 6 {
        max_large += columns / 2;
    }

    (max_large.max(0) as usize).min(eligible_count)
}

/// Plan the complete card assignment for one already-selected Featured set.
///
/// `candidates` contains `(localized_description, curated_linuxtoys)`.
/// Returned tuples are `(candidate_index, column, row, is_large)`.
#[pyfunction]
pub(crate) fn featured_layout_plan(
    candidates: Vec<(bool, bool)>,
    rows: i32,
    columns: i32,
    large_count: usize,
    previous_large_positions: Vec<(i32, i32)>,
    seed: u64,
) -> Vec<(usize, i32, i32, bool)> {
    if candidates.is_empty() || rows <= 0 || columns <= 0 {
        return Vec::new();
    }

    let mut rng = SmallRng::new(seed);
    let mut large_positions = choose_large_positions(
        rows,
        columns,
        large_count.min(candidates.len()),
        &previous_large_positions,
        &mut rng,
    );
    let wanted_large = large_positions.len();

    let mut localized = Vec::new();
    let mut nonlocalized = Vec::new();
    for (index, (is_localized, _)) in candidates.iter().copied().enumerate() {
        if is_localized {
            localized.push(index);
        } else {
            nonlocalized.push(index);
        }
    }

    let weights_for = |indices: &[usize]| -> Vec<f64> {
        indices
            .iter()
            .map(|&index| if candidates[index].1 { 0.15 } else { 1.0 })
            .collect()
    };

    // Localization is a hard preference. Non-localized candidates only backfill
    // when the localized pool cannot satisfy every available large position.
    let localized_count = wanted_large.min(localized.len());
    let mut large_indices = weighted_sample(
        &localized,
        &weights_for(&localized),
        localized_count,
        &mut rng,
    );
    let missing = wanted_large.saturating_sub(large_indices.len());
    if missing > 0 {
        large_indices.extend(weighted_sample(
            &nonlocalized,
            &weights_for(&nonlocalized),
            missing,
            &mut rng,
        ));
    }

    rng.shuffle(&mut large_indices);
    rng.shuffle(&mut large_positions);

    let large_set: HashSet<usize> = large_indices.iter().copied().collect();
    let occupied: HashSet<(i32, i32)> = large_positions
        .iter()
        .flat_map(|&position| occupied_cells(position))
        .collect();

    let mut normal_indices: Vec<usize> = (0..candidates.len())
        .filter(|index| !large_set.contains(index))
        .collect();
    rng.shuffle(&mut normal_indices);

    let free_cells: Vec<(i32, i32)> = (0..rows)
        .flat_map(|row| (0..columns).map(move |column| (column, row)))
        .filter(|position| !occupied.contains(position))
        .collect();

    let mut plan = Vec::with_capacity(candidates.len());
    for (index, (column, row)) in large_indices.into_iter().zip(large_positions) {
        plan.push((index, column, row, true));
    }
    for (index, (column, row)) in normal_indices.into_iter().zip(free_cells) {
        plan.push((index, column, row, false));
    }
    plan
}

const EXACT_CATEGORY_AFFINITY: f64 = 0.90;
const SHARED_BUCKET_AFFINITY: f64 = 0.65;

type AffinityTable = HashMap<String, HashMap<String, f64>>;
static MYKET_AFFINITY: OnceLock<AffinityTable> = OnceLock::new();

fn category_basename(category: &str) -> String {
    category
        .trim()
        .replace('\\', "/")
        .trim_matches('/')
        .rsplit('/')
        .next()
        .unwrap_or("")
        .to_lowercase()
}

fn myket_categories(category: &str) -> &'static [&'static str] {
    match category_basename(category).as_str() {
        // Media / communication.
        "audio" => &["Audio and Music"],
        "players" => &["Audio and Music", "Photography and Video"],
        "photo" | "video" | "rec" | "viewer" => &["Photography and Video"],
        "tv" => &["Entertainment", "Photography and Video"],
        "browsers" | "chat" => &["Social"],
        "network" => &["Social", "Utility"],
        "p2p" => &["Utility"],
        "remote" => &["Business", "Utility"],

        // Productivity / system.
        "document" | "planning" => &["Business"],
        "fin" => &["Financial"],
        "geo" => &["Travel and Exploration"],
        "archive" | "sec" | "sys" | "sysadm" | "txt" | "utils" | "utilities" => &["Utility"],

        // Education / health.
        "edu" | "education" | "science" | "nature" => &["Educational"],
        "langs" => &["Educational", "Book"],
        "math" => &["Educational", "Intellectual"],
        "tech" => &["Educational", "Utility"],
        "health" => &["Fitness and Wellness", "Medical and Health"],

        // Games.
        "game" | "games" | "emu" => &["Entertainment"],
        "action" => &["Thrilling", "Adventure"],
        "classic" => &["Intellectual", "Word", "Family"],
        "kids" => &["Family"],
        "sim" => &["Simulation", "Role-Playing"],
        "sports" => &["Sports"],
        "strategy" => &["Strategy"],
        _ => &[],
    }
}

fn load_myket_affinity(path: &str) -> AffinityTable {
    let Ok(content) = fs::read_to_string(path) else {
        return HashMap::new();
    };
    let Ok(value) = serde_json::from_str::<serde_json::Value>(&content) else {
        return HashMap::new();
    };
    let Some(rows) = value.get("affinity").and_then(serde_json::Value::as_object) else {
        return HashMap::new();
    };

    rows.iter()
        .map(|(source, row)| {
            let values = row
                .as_object()
                .map(|entries| {
                    entries.iter()
                        .filter_map(|(target, value)| {
                            value.as_f64().map(|score| (target.clone(), score))
                        })
                        .collect::<HashMap<_, _>>()
                })
                .unwrap_or_default();
            (source.clone(), values)
        })
        .collect()
}

fn category_affinity(source_category: &str, target_category: &str, table: &AffinityTable) -> f64 {
    let source = source_category.trim().replace('\\', "/");
    let source = source.trim_matches('/');
    let target = target_category.trim().replace('\\', "/");
    let target = target.trim_matches('/');

    if source.is_empty() || target.is_empty() {
        return 0.0;
    }
    if source.eq_ignore_ascii_case(target) {
        return EXACT_CATEGORY_AFFINITY;
    }

    let source_myket = myket_categories(source);
    let target_myket = myket_categories(target);
    if source_myket.is_empty() || target_myket.is_empty() {
        return 0.0;
    }

    let shared_bucket = source_myket
        .iter()
        .any(|source_name| target_myket.contains(source_name));
    let mut best = if shared_bucket {
        SHARED_BUCKET_AFFINITY
    } else {
        0.0
    };

    for source_name in source_myket {
        let Some(row) = table.get(*source_name) else {
            continue;
        };
        for target_name in target_myket {
            if let Some(score) = row.get(*target_name) {
                if score.is_finite() {
                    best = best.max(*score);
                }
            }
        }
    }

    best.clamp(0.0, 1.0)
}

/// Rank already-eligible app-page Featured candidates.
///
/// Each candidate is `(category, bayesian_odrs_score)`. Myket category affinity
/// remains authoritative; Bayesian ODRS quality is the secondary criterion, then
/// per-call randomness breaks exact ties. The raw star average is deliberately not
/// part of ranking because Python has already applied the >= 3.5-star eligibility gate.
#[pyfunction]
pub(crate) fn app_page_featured_rank(
    source_category: &str,
    candidates: Vec<(String, f64)>,
    count: usize,
    seed: u64,
    affinity_path: &str,
) -> Vec<usize> {
    if candidates.is_empty() || count == 0 {
        return Vec::new();
    }

    let table = MYKET_AFFINITY.get_or_init(|| load_myket_affinity(affinity_path));
    let mut rng = SmallRng::new(seed);
    let mut ranked: Vec<(usize, f64, f64, f64)> = candidates
        .into_iter()
        .enumerate()
        .map(|(index, (category, bayesian_score))| {
            (
                index,
                category_affinity(source_category, &category, table),
                if bayesian_score.is_finite() { bayesian_score } else { 0.0 },
                rng.unit(),
            )
        })
        .collect();

    ranked.sort_by(|a, b| {
        b.1.total_cmp(&a.1)
            .then_with(|| b.2.total_cmp(&a.2))
            .then_with(|| a.3.total_cmp(&b.3))
            .then_with(|| a.0.cmp(&b.0))
    });
    ranked.truncate(count.min(ranked.len()));
    ranked.into_iter().map(|entry| entry.0).collect()
}
