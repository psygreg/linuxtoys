use pyo3::prelude::*;
use pyo3::types::PyBytes;

fn source_pixel(
    pixels: &[u8],
    width: usize,
    height: usize,
    rowstride: usize,
    channels: usize,
    has_alpha: bool,
    x: isize,
    y: isize,
) -> (f64, f64, f64, f64) {
    if x < 0 || y < 0 || x as usize >= width || y as usize >= height || channels < 3 {
        return (0.0, 0.0, 0.0, 0.0);
    }
    let offset = y as usize * rowstride + x as usize * channels;
    if offset + 2 >= pixels.len() {
        return (0.0, 0.0, 0.0, 0.0);
    }
    let alpha = if has_alpha && channels >= 4 && offset + 3 < pixels.len() {
        pixels[offset + 3] as f64 / 255.0
    } else {
        1.0
    };
    (
        pixels[offset] as f64,
        pixels[offset + 1] as f64,
        pixels[offset + 2] as f64,
        alpha,
    )
}

fn corner_coverage(x: usize, y: usize, width: usize, height: usize, radius: f64) -> f64 {
    if radius <= 0.0 {
        return 1.0;
    }
    let px = x as f64 + 0.5;
    let py = y as f64 + 0.5;
    let right = width as f64 - px;
    let bottom = height as f64 - py;

    let dx = if px < radius {
        radius - px
    } else if right < radius {
        radius - right
    } else {
        0.0
    };
    let dy = if py < radius {
        radius - py
    } else if bottom < radius {
        radius - bottom
    } else {
        0.0
    };
    if dx == 0.0 || dy == 0.0 {
        return 1.0;
    }
    let distance = (dx * dx + dy * dy).sqrt();
    (radius + 0.5 - distance).clamp(0.0, 1.0)
}

/// Compose a supersampled icon onto a transparent category-card canvas, reduce it
/// to final size, apply opacity, and clip the final alpha to rounded card corners.
///
/// `source_pixels` is the already-rasterized GdkPixbuf returned by GTK. Keeping SVG
/// decoding on the GTK side preserves theme/scaling behavior while moving the
/// deterministic per-pixel transformation into Rust.
#[pyfunction]
#[pyo3(signature = (
    source_pixels,
    source_width,
    source_height,
    source_rowstride,
    source_channels,
    source_has_alpha,
    target_width,
    target_height,
    icon_x,
    icon_y,
    supersample=2,
    opacity=0.46,
    radius=10.0
))]
pub(crate) fn render_category_watermark<'py>(
    py: Python<'py>,
    source_pixels: &[u8],
    source_width: usize,
    source_height: usize,
    source_rowstride: usize,
    source_channels: usize,
    source_has_alpha: bool,
    target_width: usize,
    target_height: usize,
    icon_x: isize,
    icon_y: isize,
    supersample: usize,
    opacity: f64,
    radius: f64,
) -> PyResult<Bound<'py, PyBytes>> {
    if target_width == 0 || target_height == 0 || supersample == 0 {
        return Ok(PyBytes::new(py, &[]));
    }
    if source_channels < 3 || source_rowstride < source_width.saturating_mul(source_channels) {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "invalid source pixbuf geometry",
        ));
    }
    let required = source_rowstride.saturating_mul(source_height);
    if source_pixels.len() < required {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "source pixel buffer is smaller than its geometry",
        ));
    }

    let opacity = opacity.clamp(0.0, 1.0);
    let radius = radius.clamp(
        0.0,
        (target_width.min(target_height) as f64) / 2.0,
    );
    let ss = supersample as isize;
    let icon_x_ss = icon_x.saturating_mul(ss);
    let icon_y_ss = icon_y.saturating_mul(ss);
    let samples = (supersample * supersample) as f64;

    let mut output = vec![0u8; target_width * target_height * 4];

    // A box reduction is exact for the integer 2x supersampling used by LinuxToys
    // and avoids constructing the large transparent intermediate canvas entirely.
    for y in 0..target_height {
        for x in 0..target_width {
            let mut alpha_sum = 0.0;
            let mut red_premul = 0.0;
            let mut green_premul = 0.0;
            let mut blue_premul = 0.0;

            for sy in 0..supersample {
                for sx in 0..supersample {
                    let canvas_x = (x * supersample + sx) as isize;
                    let canvas_y = (y * supersample + sy) as isize;
                    let source_x = canvas_x - icon_x_ss;
                    let source_y = canvas_y - icon_y_ss;
                    let (r, g, b, source_alpha) = source_pixel(
                        source_pixels,
                        source_width,
                        source_height,
                        source_rowstride,
                        source_channels,
                        source_has_alpha,
                        source_x,
                        source_y,
                    );
                    let alpha = source_alpha * opacity;
                    alpha_sum += alpha;
                    red_premul += r * alpha;
                    green_premul += g * alpha;
                    blue_premul += b * alpha;
                }
            }

            let averaged_alpha = alpha_sum / samples;
            let coverage = corner_coverage(x, y, target_width, target_height, radius);
            let final_alpha = averaged_alpha * coverage;
            let offset = (y * target_width + x) * 4;

            if alpha_sum > 0.0 {
                output[offset] = (red_premul / alpha_sum).round().clamp(0.0, 255.0) as u8;
                output[offset + 1] =
                    (green_premul / alpha_sum).round().clamp(0.0, 255.0) as u8;
                output[offset + 2] =
                    (blue_premul / alpha_sum).round().clamp(0.0, 255.0) as u8;
            }
            output[offset + 3] = (final_alpha * 255.0).round().clamp(0.0, 255.0) as u8;
        }
    }

    Ok(PyBytes::new(py, &output))
}
