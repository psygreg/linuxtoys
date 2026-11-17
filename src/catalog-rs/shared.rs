//! Helpers shared across the catalog-rs modules: the JSON→Python boundary,
//! the canonical AppStream ID normalization and the weighted-draw core used
//! by the featured-grid samplers.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde_json::Value;

/// Convert a ``serde_json`` value into plain Python objects
/// (``None``/``bool``/``int``/``float``/``str``/``list``/``dict``).
pub(crate) fn json_to_py(py: Python<'_>, value: &Value) -> PyResult<Py<PyAny>> {
    Ok(match value {
        Value::Null => py.None(),
        Value::Bool(v) => v.into_pyobject(py)?.to_owned().unbind().into_any(),
        Value::Number(v) => {
            if let Some(i) = v.as_i64() {
                i.into_pyobject(py)?.to_owned().unbind().into_any()
            } else if let Some(u) = v.as_u64() {
                u.into_pyobject(py)?.to_owned().unbind().into_any()
            } else {
                v.as_f64()
                    .unwrap_or(0.0)
                    .into_pyobject(py)?
                    .to_owned()
                    .unbind()
                    .into_any()
            }
        }
        Value::String(v) => v.into_pyobject(py)?.to_owned().unbind().into_any(),
        Value::Array(values) => {
            let list = PyList::empty(py);
            for v in values {
                list.append(json_to_py(py, v)?)?;
            }
            list.unbind().into_any()
        }
        Value::Object(values) => {
            let dict = PyDict::new(py);
            for (k, v) in values {
                dict.set_item(k, json_to_py(py, v)?)?;
            }
            dict.unbind().into_any()
        }
    })
}

/// Canonical AppStream ID normalization shared by the repo and appstream
/// pipelines: trim, drop a ``.desktop``/``.Desktop`` suffix, lowercase.
pub(crate) fn normalize_appstream_id(value: &str) -> String {
    let value = value.trim();
    let value = value
        .strip_suffix(".desktop")
        .or_else(|| value.strip_suffix(".Desktop"))
        .unwrap_or(value);
    value.trim().to_lowercase()
}

/// Weighted single draw over a ``(index, weight)`` pool: returns the pool
/// position to remove, or ``None`` when the pool has no positive weight left.
/// ``unit`` must be in ``[0, 1)``.
pub(crate) fn weighted_pick(pool: &[(usize, f64)], unit: f64) -> Option<usize> {
    let total: f64 = pool.iter().map(|(_, weight)| *weight).sum();
    if total <= 0.0 || !total.is_finite() {
        return None;
    }
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
    chosen.or_else(|| pool.iter().rposition(|(_, weight)| *weight > 0.0))
}
