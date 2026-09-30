use gdk::prelude::*;
use gdk_pixbuf::Pixbuf;
use glib::translate::{from_glib_none, ToGlibPtr};
use gtk::prelude::*;
use std::cell::RefCell;
use std::collections::{hash_map::DefaultHasher, HashMap};
use std::ffi::{c_char, CStr};
use std::fs;
use std::hash::{Hash, Hasher};
use std::io::{Read, Write};
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};
use std::sync::{Mutex, OnceLock};
use std::time::Duration;

#[derive(Clone, Hash, Eq, PartialEq)]
struct PixbufKey {
    path: String,
    mtime_ns: u128,
    len: u64,
    width: i32,
    height: i32,
}

thread_local! {
    static PIXBUF_CACHE: RefCell<HashMap<PixbufKey, Pixbuf>> =
        RefCell::new(HashMap::new());
}

fn cstr(ptr: *const c_char) -> String {
    if ptr.is_null() { return String::new(); }
    unsafe { CStr::from_ptr(ptr) }.to_string_lossy().into_owned()
}

fn load_scaled(path: &str, width: i32, height: i32) -> Option<Pixbuf> {
    if path.is_empty() { return None; }
    let meta = fs::metadata(path).ok()?;
    let mtime_ns = meta.modified().ok()?.duration_since(std::time::UNIX_EPOCH).ok()?.as_nanos();
    let key = PixbufKey { path: path.to_owned(), mtime_ns, len: meta.len(), width, height };

    if let Some(pixbuf) = PIXBUF_CACHE.with(|cache| cache.borrow().get(&key).cloned()) {
        return Some(pixbuf);
    }

    let pixbuf = Pixbuf::from_file_at_scale(path, width, height, true).ok()?;
    PIXBUF_CACHE.with(|cache| {
        let mut cache = cache.borrow_mut();
        cache.retain(|k, _| !(k.path == path && k.width == width && k.height == height && k != &key));
        cache.insert(key, pixbuf.clone());
    });
    Some(pixbuf)
}

const REMOTE_ICON_LIMIT: u64 = 4 * 1024 * 1024;

static REMOTE_ICON_FETCHES: OnceLock<Mutex<HashMap<String, Option<bool>>>> = OnceLock::new();

thread_local! {
    static REMOTE_IMAGE_BINDINGS: RefCell<HashMap<usize, String>> = RefCell::new(HashMap::new());
}

fn remote_fetches() -> &'static Mutex<HashMap<String, Option<bool>>> {
    REMOTE_ICON_FETCHES.get_or_init(|| Mutex::new(HashMap::new()))
}

fn is_remote_image(value: &str) -> bool {
    value.starts_with("https://") || value.starts_with("http://") || value.starts_with("/v2/")
}

fn remote_icon_cache_dir() -> PathBuf {
    if let Some(cache) = std::env::var_os("XDG_CACHE_HOME").filter(|v| !v.is_empty()) {
        return PathBuf::from(cache).join("linuxtoys/appstream/icons");
    }
    if let Some(home) = std::env::var_os("HOME").filter(|v| !v.is_empty()) {
        return PathBuf::from(home).join(".cache/linuxtoys/appstream/icons");
    }
    std::env::temp_dir().join("linuxtoys/appstream/icons")
}

fn remote_icon_path(source: &str) -> PathBuf {
    let mut hasher = DefaultHasher::new();
    source.hash(&mut hasher);
    remote_icon_cache_dir().join(format!("{:016x}.img", hasher.finish()))
}

fn fetch_http_icon(source: &str) -> Result<Vec<u8>, String> {
    let response = ureq::get(source)
        .set("User-Agent", "LinuxToys AppStream")
        .timeout(Duration::from_secs(20))
        .call()
        .map_err(|error| error.to_string())?;
    let mut reader = response.into_reader().take(REMOTE_ICON_LIMIT + 1);
    let mut data = Vec::new();
    reader.read_to_end(&mut data).map_err(|error| error.to_string())?;
    if data.is_empty() || data.len() as u64 > REMOTE_ICON_LIMIT {
        return Err("remote icon is empty or exceeds size limit".to_string());
    }
    Ok(data)
}

fn fetch_snapd_icon(source: &str) -> Result<Vec<u8>, String> {
    let mut stream = UnixStream::connect("/run/snapd.socket").map_err(|error| error.to_string())?;
    stream.set_read_timeout(Some(Duration::from_secs(20))).ok();
    stream.set_write_timeout(Some(Duration::from_secs(20))).ok();
    write!(
        stream,
        "GET {} HTTP/1.1\r\nHost: localhost\r\nAccept: */*\r\nConnection: close\r\n\r\n",
        source
    ).map_err(|error| error.to_string())?;

    let mut response = Vec::new();
    stream.read_to_end(&mut response).map_err(|error| error.to_string())?;
    let header_end = response.windows(4).position(|window| window == b"\r\n\r\n")
        .ok_or_else(|| "invalid snapd icon response".to_string())?;
    let header = std::str::from_utf8(&response[..header_end]).map_err(|error| error.to_string())?;
    let status = header.lines().next().unwrap_or_default();
    if !status.contains(" 200 ") {
        return Err(format!("snapd icon request failed: {status}"));
    }
    let data = response[(header_end + 4)..].to_vec();
    if data.is_empty() || data.len() as u64 > REMOTE_ICON_LIMIT {
        return Err("snapd icon is empty or exceeds size limit".to_string());
    }
    Ok(data)
}

fn fetch_remote_icon(source: &str) -> Result<Vec<u8>, String> {
    if source.starts_with("https://") || source.starts_with("http://") {
        fetch_http_icon(source)
    } else if source.starts_with("/v2/") {
        fetch_snapd_icon(source)
    } else {
        Err("unsupported remote icon source".to_string())
    }
}

fn bind_remote_image(image: &gtk::Image, source: &str, size: i32) {
    let source = source.to_string();
    let target = remote_icon_path(&source);
    let key = widget_key(image);

    REMOTE_IMAGE_BINDINGS.with(|bindings| {
        bindings.borrow_mut().insert(key, source.clone());
    });

    if target.is_file() {
        if let Some(pixbuf) = load_scaled(target.to_string_lossy().as_ref(), size, size) {
            image.set_from_pixbuf(Some(&pixbuf));
            return;
        }
        let _ = fs::remove_file(&target);
    }

    let should_spawn = {
        let mut fetches = remote_fetches().lock().unwrap_or_else(|poisoned| poisoned.into_inner());
        match fetches.get(&source).copied() {
            Some(None) => false,
            _ => {
                fetches.insert(source.clone(), None);
                true
            }
        }
    };

    if should_spawn {
        let worker_source = source.clone();
        let worker_target = target.clone();
        std::thread::spawn(move || {
            let success = (|| -> Result<(), String> {
                let data = fetch_remote_icon(&worker_source)?;
                if let Some(parent) = worker_target.parent() {
                    fs::create_dir_all(parent).map_err(|error| error.to_string())?;
                }
                let tmp = worker_target.with_extension("tmp");
                fs::write(&tmp, data).map_err(|error| error.to_string())?;
                fs::rename(&tmp, &worker_target).map_err(|error| error.to_string())?;
                Ok(())
            })().is_ok();
            let mut fetches = remote_fetches().lock().unwrap_or_else(|poisoned| poisoned.into_inner());
            fetches.insert(worker_source, Some(success));
        });
    }

    let image = image.clone();
    glib::timeout_add_local(Duration::from_millis(75), move || {
        let still_bound = REMOTE_IMAGE_BINDINGS.with(|bindings| {
            bindings.borrow().get(&key).map(String::as_str) == Some(source.as_str())
        });
        if !still_bound {
            return glib::ControlFlow::Break;
        }

        let state = remote_fetches()
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .get(&source)
            .copied()
            .flatten();
        match state {
            None => glib::ControlFlow::Continue,
            Some(false) => glib::ControlFlow::Break,
            Some(true) => {
                if let Some(pixbuf) = load_scaled(target.to_string_lossy().as_ref(), size, size) {
                    image.set_from_pixbuf(Some(&pixbuf));
                }
                glib::ControlFlow::Break
            }
        }
    });
}

fn set_image_source(image: &gtk::Image, icon_path: &str, icon_name: &str, size: i32) {
    let key = widget_key(image);
    REMOTE_IMAGE_BINDINGS.with(|bindings| {
        bindings.borrow_mut().remove(&key);
    });

    if !icon_path.is_empty() && Path::new(icon_path).exists() {
        if let Some(pixbuf) = load_scaled(icon_path, size, size) {
            image.set_from_pixbuf(Some(&pixbuf));
            return;
        }
    }

    if is_remote_image(icon_name) {
        image.set_from_icon_name(Some("application-x-executable"), gtk::IconSize::Dialog);
        image.set_pixel_size(size);
        bind_remote_image(image, icon_name, size);
        return;
    }

    let name = if icon_name.is_empty() { "application-x-executable" } else { icon_name };
    image.set_from_icon_name(Some(name), gtk::IconSize::Dialog);
    image.set_pixel_size(size);
}

fn image(icon_path: &str, icon_name: &str, size: i32) -> gtk::Image {
    let img = gtk::Image::new();
    set_image_source(&img, icon_path, icon_name, size);
    img
}


#[derive(Clone)]
struct CategoryWatermarkState {
    drawing: gtk::DrawingArea,
    pixbuf: Option<Pixbuf>,
    icon_path: String,
    pending_width: i32,
    pending_height: i32,
    rendered_width: i32,
    rendered_height: i32,
    render_scheduled: bool,
}

thread_local! {
    static CATEGORY_WATERMARKS: RefCell<HashMap<usize, CategoryWatermarkState>> =
        RefCell::new(HashMap::new());
}

fn widget_key<W: IsA<gtk::Widget>>(widget: &W) -> usize {
    let ptr: *mut gtk::ffi::GtkWidget = widget.as_ref().to_glib_none().0;
    ptr as usize
}

fn corner_coverage(x: usize, y: usize, width: usize, height: usize, radius: f64) -> f64 {
    if radius <= 0.0 { return 1.0; }
    let px = x as f64 + 0.5;
    let py = y as f64 + 0.5;
    let right = width as f64 - px;
    let bottom = height as f64 - py;
    let dx = if px < radius { radius - px } else if right < radius { radius - right } else { 0.0 };
    let dy = if py < radius { radius - py } else if bottom < radius { radius - bottom } else { 0.0 };
    if dx == 0.0 || dy == 0.0 { return 1.0; }
    let distance = (dx * dx + dy * dy).sqrt();
    (radius + 0.5 - distance).clamp(0.0, 1.0)
}

fn category_watermark_pixbuf(path: &str, width: i32, height: i32) -> Option<Pixbuf> {
    if width <= 0 || height <= 0 || path.is_empty() || !Path::new(path).exists() {
        return None;
    }

    let supersample = 2usize;
    let icon_size = ((height as f64 * 1.70).round() as i32).max(1);
    let icon_size_ss = icon_size.saturating_mul(supersample as i32);
    let icon_x = (-height as f64 * 0.42).round() as isize;
    let icon_y = ((height - icon_size) as f64 / 2.0).round() as isize;
    let source = Pixbuf::from_file_at_scale(path, icon_size_ss, icon_size_ss, true).ok()?;

    let sw = source.width().max(0) as usize;
    let sh = source.height().max(0) as usize;
    let stride = source.rowstride().max(0) as usize;
    let channels = source.n_channels().max(0) as usize;
    let has_alpha = source.has_alpha();
    if channels < 3 || stride < sw.saturating_mul(channels) { return None; }

    let bytes = source.read_pixel_bytes();
    let pixels = bytes.as_ref();
    if pixels.len() < stride.saturating_mul(sh) { return None; }

    let tw = width as usize;
    let th = height as usize;
    let mut output = vec![0u8; tw.saturating_mul(th).saturating_mul(4)];
    let ss = supersample as isize;
    let icon_x_ss = icon_x.saturating_mul(ss);
    let icon_y_ss = icon_y.saturating_mul(ss);
    let samples = (supersample * supersample) as f64;

    for y in 0..th {
        for x in 0..tw {
            let mut alpha_sum = 0.0;
            let mut red_premul = 0.0;
            let mut green_premul = 0.0;
            let mut blue_premul = 0.0;

            for sy in 0..supersample {
                for sx in 0..supersample {
                    let source_x = (x * supersample + sx) as isize - icon_x_ss;
                    let source_y = (y * supersample + sy) as isize - icon_y_ss;
                    if source_x < 0 || source_y < 0 ||
                       source_x as usize >= sw || source_y as usize >= sh {
                        continue;
                    }
                    let offset = source_y as usize * stride + source_x as usize * channels;
                    if offset + 2 >= pixels.len() { continue; }
                    let alpha = if has_alpha && channels >= 4 && offset + 3 < pixels.len() {
                        pixels[offset + 3] as f64 / 255.0
                    } else { 1.0 };
                    alpha_sum += alpha;
                    red_premul += pixels[offset] as f64 * alpha;
                    green_premul += pixels[offset + 1] as f64 * alpha;
                    blue_premul += pixels[offset + 2] as f64 * alpha;
                }
            }

            let alpha = (alpha_sum / samples) * corner_coverage(x, y, tw, th, 10.0);
            let out = (y * tw + x) * 4;
            if alpha_sum > 0.0 {
                output[out] = (red_premul / alpha_sum).round().clamp(0.0, 255.0) as u8;
                output[out + 1] = (green_premul / alpha_sum).round().clamp(0.0, 255.0) as u8;
                output[out + 2] = (blue_premul / alpha_sum).round().clamp(0.0, 255.0) as u8;
            }
            output[out + 3] = (alpha * 255.0).round().clamp(0.0, 255.0) as u8;
        }
    }

    let bytes = glib::Bytes::from_owned(output);
    Some(Pixbuf::from_bytes(
        &bytes, gdk_pixbuf::Colorspace::Rgb, true, 8,
        width, height, width.saturating_mul(4),
    ))
}

fn register_category_watermark(
    surface: &gtk::Widget,
    drawing: &gtk::DrawingArea,
    icon_path: String,
) {
    let key = widget_key(surface);
    CATEGORY_WATERMARKS.with(|states| {
        states.borrow_mut().insert(key, CategoryWatermarkState {
            drawing: drawing.clone(),
            pixbuf: None,
            icon_path,
            pending_width: 0,
            pending_height: 0,
            rendered_width: 0,
            rendered_height: 0,
            render_scheduled: false,
        });
    });

    surface.connect_size_allocate(move |widget, allocation| {
        let should_schedule = CATEGORY_WATERMARKS.with(|states| {
            let mut states = states.borrow_mut();
            let Some(state) = states.get_mut(&key) else { return false; };
            let width = allocation.width();
            let height = allocation.height();
            let changed = state.pending_width != width || state.pending_height != height;
            state.pending_width = width;
            state.pending_height = height;

            if changed && !state.render_scheduled {
                state.render_scheduled = true;
                true
            } else {
                false
            }
        });

        if should_schedule {
            // Startup/language transitions still use their explicit cooperative
            // barriers. For ordinary post-startup reallocations, coalesce repeated
            // size-allocate signals into one idle render so window resizing and
            // AppStream/Featured layout churn cannot leave a stale watermark or
            // synchronously rasterize every intermediate size.
            let widget = widget.clone();
            glib::idle_add_local_once(move || {
                CATEGORY_WATERMARKS.with(|states| {
                    if let Some(state) = states.borrow_mut().get_mut(&key) {
                        state.render_scheduled = false;
                    }
                });
                let _ = flush_category_surface(&widget);
            });
        }
    });

    surface.connect_destroy(move |_| {
        CATEGORY_WATERMARKS.with(|states| {
            states.borrow_mut().remove(&key);
        });
    });

    drawing.connect_draw(move |_drawing, cr| {
        let pixbuf = CATEGORY_WATERMARKS.with(|states| {
            states.borrow().get(&key).and_then(|state| state.pixbuf.clone())
        });
        if let Some(pixbuf) = pixbuf {
            cr.set_source_pixbuf(&pixbuf, 0.0, 0.0);
            let _ = cr.paint();
        }
        glib::Propagation::Proceed
    });
}

fn flush_category_surface(widget: &gtk::Widget) -> bool {
    let key = widget_key(widget);
    let request = CATEGORY_WATERMARKS.with(|states| {
        let states = states.borrow();
        let state = states.get(&key)?;
        if state.pending_width <= 0 || state.pending_height <= 0 ||
           (state.pixbuf.is_some() &&
            state.pending_width == state.rendered_width &&
            state.pending_height == state.rendered_height) {
            return None;
        }
        Some((state.icon_path.clone(), state.pending_width, state.pending_height))
    });

    let Some((path, width, height)) = request else { return false; };
    let Some(pixbuf) = category_watermark_pixbuf(&path, width, height) else { return false; };

    CATEGORY_WATERMARKS.with(|states| {
        if let Some(state) = states.borrow_mut().get_mut(&key) {
            state.pixbuf = Some(pixbuf);
            state.rendered_width = width;
            state.rendered_height = height;
            state.drawing.queue_draw();
        }
    });
    true
}

fn category_surface_has_pending_render(widget: &gtk::Widget) -> bool {
    let key = widget_key(widget);
    CATEGORY_WATERMARKS.with(|states| {
        let states = states.borrow();
        let Some(state) = states.get(&key) else { return false; };

        // A registered category surface is not ready until GTK has allocated it
        // and the allocation-sized watermark for that exact size exists.
        state.pending_width <= 0 ||
        state.pending_height <= 0 ||
        state.pixbuf.is_none() ||
        state.pending_width != state.rendered_width ||
        state.pending_height != state.rendered_height
    })
}

fn category_tree_has_pending_render(widget: &gtk::Widget) -> bool {
    if category_surface_has_pending_render(widget) {
        return true;
    }

    if let Ok(container) = widget.clone().downcast::<gtk::Container>() {
        for child in container.children() {
            if category_tree_has_pending_render(&child) {
                return true;
            }
        }
    }
    false
}

fn flush_category_tree(widget: &gtk::Widget, remaining: &mut usize, unlimited: bool) -> usize {
    let mut rendered = 0usize;
    if (unlimited || *remaining > 0) && flush_category_surface(widget) {
        rendered += 1;
        if !unlimited { *remaining = remaining.saturating_sub(1); }
    }
    if !unlimited && *remaining == 0 { return rendered; }

    if let Ok(container) = widget.clone().downcast::<gtk::Container>() {
        for child in container.children() {
            rendered += flush_category_tree(&child, remaining, unlimited);
            if !unlimited && *remaining == 0 { break; }
        }
    }
    rendered
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_has_pending_render_work(
    root: *mut gtk::ffi::GtkWidget,
) -> bool {
    if root.is_null() { return false; }
    ensure_gtk_initialized();
    let root: gtk::Widget = from_glib_none(root);
    category_tree_has_pending_render(&root)
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_flush_category_watermarks(
    root: *mut gtk::ffi::GtkWidget,
    max_count: usize,
) -> usize {
    if root.is_null() { return 0; }
    ensure_gtk_initialized();
    let root: gtk::Widget = from_glib_none(root);
    let unlimited = max_count == 0;
    let mut remaining = max_count;
    flush_category_tree(&root, &mut remaining, unlimited)
}

fn ensure_gtk_initialized() {
    if !gtk::is_initialized() {
        unsafe {
            gtk::set_initialized();
        }
    }
}


fn stack_remove_child(stack: &gtk::Stack, child: &gtk::Widget, destroy: bool) -> bool {
    if child.parent().as_ref() != Some(stack.upcast_ref::<gtk::Widget>()) {
        return false;
    }
    stack.remove(child);
    if destroy {
        unsafe {
            child.destroy();
        }
    }
    true
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_stack_add_scrolled_flowbox(
    stack: *mut gtk::ffi::GtkWidget,
    flowbox: *mut gtk::ffi::GtkWidget,
    name: *const c_char,
) -> bool {
    if stack.is_null() || flowbox.is_null() || name.is_null() {
        return false;
    }

    let stack: gtk::Stack = from_glib_none(stack as *mut gtk::ffi::GtkStack);
    let flowbox: gtk::FlowBox = from_glib_none(flowbox as *mut gtk::ffi::GtkFlowBox);
    let name = cstr(name);
    if name.is_empty() || stack.child_by_name(&name).is_some() {
        return false;
    }

    let scrolled = gtk::ScrolledWindow::new(None::<&gtk::Adjustment>, None::<&gtk::Adjustment>);
    scrolled.add(&flowbox);
    stack.add_named(&scrolled, &name);
    scrolled.show_all();
    true
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_stack_add_category_browser(
    stack: *mut gtk::ffi::GtkWidget,
    available_flowbox: *mut gtk::ffi::GtkWidget,
    installed_flowbox: *mut gtk::ffi::GtkWidget,
    name: *const c_char,
    available_label: *const c_char,
    installed_label: *const c_char,
) -> bool {
    if stack.is_null() || available_flowbox.is_null() || installed_flowbox.is_null()
        || name.is_null() || available_label.is_null() || installed_label.is_null()
    {
        return false;
    }

    let stack: gtk::Stack = from_glib_none(stack as *mut gtk::ffi::GtkStack);
    let available_flowbox: gtk::FlowBox =
        from_glib_none(available_flowbox as *mut gtk::ffi::GtkFlowBox);
    let installed_flowbox: gtk::FlowBox =
        from_glib_none(installed_flowbox as *mut gtk::ffi::GtkFlowBox);
    let name = cstr(name);
    if name.is_empty() || stack.child_by_name(&name).is_some() {
        return false;
    }

    available_flowbox.set_widget_name("linuxtoys-category-available-flowbox");
    installed_flowbox.set_widget_name("linuxtoys-category-installed-flowbox");

    let available_scroller =
        gtk::ScrolledWindow::new(None::<&gtk::Adjustment>, None::<&gtk::Adjustment>);
    available_scroller.set_policy(gtk::PolicyType::Never, gtk::PolicyType::Automatic);
    available_scroller.add(&available_flowbox);

    let installed_scroller =
        gtk::ScrolledWindow::new(None::<&gtk::Adjustment>, None::<&gtk::Adjustment>);
    installed_scroller.set_policy(gtk::PolicyType::Never, gtk::PolicyType::Automatic);
    installed_scroller.add(&installed_flowbox);

    let tabs = gtk::Stack::new();
    tabs.set_widget_name("linuxtoys-category-tabs");
    tabs.set_transition_type(gtk::StackTransitionType::None);
    tabs.set_transition_duration(140);
    tabs.add_titled(&available_scroller, "available", &cstr(available_label));
    tabs.add_titled(&installed_scroller, "installed", &cstr(installed_label));

    let switcher = gtk::StackSwitcher::new();
    switcher.set_widget_name("linuxtoys-category-switcher");
    switcher.style_context().add_class("category-footer-tabs");
    switcher.set_stack(Some(&tabs));
    switcher.set_halign(gtk::Align::Fill);
    switcher.set_hexpand(true);
    // Footer tabs are deliberately flush with the category view edges.
    switcher.set_margin_start(0);
    switcher.set_margin_end(0);
    switcher.set_margin_top(0);
    switcher.set_margin_bottom(0);
    for child in switcher.children() {
        child.set_hexpand(true);
        child.set_halign(gtk::Align::Fill);
    }

    let view = gtk::Box::new(gtk::Orientation::Vertical, 0);
    view.set_widget_name("linuxtoys-category-browser");
    // The selected category contents own the expanding body. Keep the switcher
    // outside either ScrolledWindow and pinned to the bottom as a fixed footer.
    view.pack_start(&tabs, true, true, 0);
    view.pack_end(&switcher, false, false, 0);
    stack.add_named(&view, &name);
    view.show_all();
    tabs.set_visible_child(&available_scroller);
    tabs.set_transition_type(gtk::StackTransitionType::Crossfade);
    true
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_stack_attach_child(
    stack: *mut gtk::ffi::GtkWidget,
    child: *mut gtk::ffi::GtkWidget,
    name: *const c_char,
    make_visible: u8,
) -> bool {
    if stack.is_null() || child.is_null() || name.is_null() {
        return false;
    }

    let stack: gtk::Stack = from_glib_none(stack as *mut gtk::ffi::GtkStack);
    let child: gtk::Widget = from_glib_none(child);
    let name = cstr(name);
    if name.is_empty() || stack.child_by_name(&name).is_some() {
        return false;
    }

    stack.add_named(&child, &name);
    child.show_all();
    if make_visible != 0 {
        stack.set_visible_child(&child);
    }
    true
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_stack_remove_child(
    stack: *mut gtk::ffi::GtkWidget,
    child: *mut gtk::ffi::GtkWidget,
    destroy: u8,
) -> bool {
    if stack.is_null() || child.is_null() {
        return false;
    }
    let stack: gtk::Stack = from_glib_none(stack as *mut gtk::ffi::GtkStack);
    let child: gtk::Widget = from_glib_none(child);
    stack_remove_child(&stack, &child, destroy != 0)
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_stack_remove_child_after_transition(
    stack: *mut gtk::ffi::GtkWidget,
    child: *mut gtk::ffi::GtkWidget,
    destroy: u8,
    extra_delay_ms: u32,
) -> bool {
    if stack.is_null() || child.is_null() {
        return false;
    }

    let stack: gtk::Stack = from_glib_none(stack as *mut gtk::ffi::GtkStack);
    let child: gtk::Widget = from_glib_none(child);
    if child.parent().as_ref() != Some(stack.upcast_ref::<gtk::Widget>()) {
        return false;
    }

    let delay_ms = stack
        .transition_duration()
        .max(1)
        .saturating_add(extra_delay_ms);

    glib::timeout_add_local_once(
        std::time::Duration::from_millis(delay_ms as u64),
        move || {
            let _ = stack_remove_child(&stack, &child, destroy != 0);
        },
    );
    true
}

#[no_mangle]
pub extern "C" fn lt_gui_abi_version() -> u32 { 18 }

#[no_mangle]
pub extern "C" fn lt_gui_clear_pixbuf_cache() {
    PIXBUF_CACHE.with(|cache| cache.borrow_mut().clear());
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_set_image_source(
    image: *mut gtk::ffi::GtkWidget,
    icon_path: *const c_char,
    icon_name: *const c_char,
    size: i32,
) -> bool {
    ensure_gtk_initialized();
    if image.is_null() { return false; }
    let widget: gtk::Widget = from_glib_none(image);
    let image = match widget.downcast::<gtk::Image>() {
        Ok(image) => image,
        Err(_) => return false,
    };
    set_image_source(&image, &cstr(icon_path), &cstr(icon_name), size.max(1));
    true
}

#[repr(C)]
pub struct LtGuiItemCardSpec {
    name: *const c_char,
    icon_path: *const c_char,
    icon_name: *const c_char,
    badge_path: *const c_char,
    bold: u8,
    removable: u8,
    checklist: u8,
    is_new: u8,
    category: u8,
}

unsafe fn create_item_card_from_spec(spec: &LtGuiItemCardSpec) -> Option<gtk::EventBox> {
    let name = cstr(spec.name);
    let icon_path = cstr(spec.icon_path);
    let icon_name = cstr(spec.icon_name);
    let badge_path = cstr(spec.badge_path);
    let bold = spec.bold != 0;
    let removable = spec.removable != 0;
    let checklist = spec.checklist != 0;
    let is_new = spec.is_new != 0;
    let category = spec.category != 0;

    let row = gtk::Box::new(gtk::Orientation::Horizontal, 12);
    row.set_size_request(128, 52);
    row.set_hexpand(false);
    row.set_halign(gtk::Align::Fill);

    // Keep the removal control in every ordinary installable card so installed
    // state can be changed in place after a transaction. Categories can never be
    // removable, so do not create or reserve a removal-control slot for them.
    if !category {
        let remove_button = gtk::Button::from_icon_name(
            Some("edit-delete-symbolic"),
            gtk::IconSize::Menu,
        );
        remove_button.style_context().add_class("installed-card-remove-left");
        remove_button.style_context().add_class("destructive-action");
        remove_button.set_size_request(24, 24);
        remove_button.set_relief(gtk::ReliefStyle::None);
        remove_button.set_can_focus(true);
        remove_button.set_widget_name("linuxtoys-native-remove");
        row.pack_start(&remove_button, false, false, 0);
        if removable {
            row.style_context().add_class("installed-card");
        } else {
            remove_button.set_no_show_all(true);
            remove_button.hide();
        }
    }

    if checklist {
        let check = gtk::CheckButton::new();
        check.set_can_focus(false);
        check.set_widget_name("linuxtoys-native-check");
        if !removable { check.set_margin_start(22); }
        row.pack_start(&check, false, false, 0);
    }

    let label = gtk::Label::new(Some(&name));
    label.set_widget_name("linuxtoys-native-name");
    if !removable && !checklist {
        if category {
            label.set_margin_end(46);
        } else {
            label.set_margin_start(22);
        }
    }
    label.set_line_wrap(true);
    label.set_justify(gtk::Justification::Center);
    label.set_halign(gtk::Align::Center);
    label.set_valign(gtk::Align::Center);
    label.set_max_width_chars(28);
    label.set_width_chars(4);
    label.set_hexpand(false);
    if bold {
        let escaped = glib::markup_escape_text(&name);
        label.set_markup(&format!("<b>{escaped}</b>"));
    }

    let icon = image(&icon_path, &icon_name, 38);
    icon.set_widget_name("linuxtoys-native-icon");
    icon.set_halign(gtk::Align::End);
    icon.set_valign(gtk::Align::Center);

    if category {
        // Mirror the ordinary card geometry: reserve the 38 px icon slot on the
        // left, keep its 20 px packing, and shift the old 22 px label compensation
        // to the right. The real category artwork is supplied by Python's
        // allocation-sized watermark layer.
        let slot = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        slot.set_widget_name("linuxtoys-native-category-slot");
        slot.set_size_request(38, 38);
        slot.set_halign(gtk::Align::Start);
        slot.set_valign(gtk::Align::Center);
        row.pack_start(&slot, false, false, 20);
        row.pack_start(&label, true, true, 0);

        // Keep the image alive and discoverable for the common Python/native API,
        // but do not parent/show it on category cards.
        icon.set_no_show_all(true);
        icon.hide();
    } else {
        row.pack_start(&label, true, true, 0);
        row.pack_start(&icon, false, false, 20);
    }

    if category {
        row.set_hexpand(true);
        row.set_halign(gtk::Align::Fill);
    }

    let surface: gtk::Widget = if category {
        // Reproduce the former Python wrapper structurally: the painted card is
        // a GtkGrid, with an allocation-neutral drawing layer behind the original
        // foreground surface. Unlike GtkImage, DrawingArea has no pixbuf-derived
        // preferred size, so it cannot disturb FlowBox column sizing.
        let card_surface = gtk::Grid::new();
        card_surface.set_widget_name("linuxtoys-native-surface");
        card_surface.style_context().add_class("script-item");
        if is_new { card_surface.style_context().add_class("script-item-new"); }
        card_surface.set_margin_top(4);
        card_surface.set_margin_start(4);
        card_surface.set_margin_end(4);

        let drawing = gtk::DrawingArea::new();
        drawing.set_widget_name("linuxtoys-native-category-watermark");

        // Draw into the parent window instead of creating an input-owning
        // GdkWindow over the whole category card. This preserves the GtkGrid
        // as the CSS-painted surface while letting the outer EventBox receive
        // pointer enter/leave events reliably.
        drawing.set_has_window(false);

        drawing.set_hexpand(true);
        drawing.set_vexpand(true);
        drawing.set_halign(gtk::Align::Fill);
        drawing.set_valign(gtk::Align::Fill);

        // Keep the Rust-built row hierarchy exactly as before, but strip the
        // paint role from this inner foreground container just as Python did.
        let foreground = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        foreground.pack_start(&row, true, true, 0);
        foreground.set_hexpand(true);
        foreground.set_halign(gtk::Align::Fill);

        card_surface.attach(&drawing, 0, 0, 1, 1);
        card_surface.attach(&foreground, 0, 0, 1, 1);

        let surface_widget: gtk::Widget = card_surface.clone().upcast();
        register_category_watermark(&surface_widget, &drawing, icon_path.clone());
        surface_widget
    } else {
        let ordinary_surface = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        ordinary_surface.pack_start(&row, true, true, 0);
        ordinary_surface.set_widget_name("linuxtoys-native-surface");
        ordinary_surface.style_context().add_class("script-item");
        if is_new { ordinary_surface.style_context().add_class("script-item-new"); }
        ordinary_surface.set_margin_top(4);
        ordinary_surface.set_margin_start(4);
        ordinary_surface.set_margin_end(4);
        ordinary_surface.upcast::<gtk::Widget>()
    };

    let overlay = gtk::Overlay::new();
    overlay.set_widget_name("linuxtoys-native-overlay");
    overlay.add(&surface);
    if !badge_path.is_empty() {
        if let Some(pixbuf) = load_scaled(&badge_path, 20, 20) {
            let badge = gtk::Image::from_pixbuf(Some(&pixbuf));
            badge.set_widget_name("linuxtoys-native-badge");
            badge.set_halign(gtk::Align::End);
            badge.set_valign(gtk::Align::Start);
            overlay.add_overlay(&badge);
        }
    }

    let event_box = gtk::EventBox::new();
    event_box.add(&overlay);
    event_box.set_events(
        event_box.events()
            | gdk::EventMask::ENTER_NOTIFY_MASK
            | gdk::EventMask::LEAVE_NOTIFY_MASK
            | gdk::EventMask::BUTTON_PRESS_MASK
            | gdk::EventMask::BUTTON_RELEASE_MASK,
    );
    event_box.show_all();
    Some(event_box)
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_flowbox_add_item_cards(
    flowbox: *mut gtk::ffi::GtkWidget,
    specs: *const LtGuiItemCardSpec,
    count: usize,
) -> usize {
    ensure_gtk_initialized();

    if flowbox.is_null() || specs.is_null() {
        return 0;
    }

    let widget: gtk::Widget = from_glib_none(flowbox);
    let flowbox = match widget.downcast::<gtk::FlowBox>() {
        Ok(flowbox) => flowbox,
        Err(_) => return 0,
    };
    let specs = std::slice::from_raw_parts(specs, count);

    // Construct the whole batch before mutating the FlowBox. This keeps Python's
    // fallback safe: a failed native batch can never leave a partial prefix behind.
    let mut cards = Vec::with_capacity(count);
    for spec in specs {
        match create_item_card_from_spec(spec) {
            Some(card) => cards.push(card),
            None => return 0,
        }
    }

    for card in cards {
        flowbox.add(&card);
    }
    count
}



#[repr(C)]
pub struct LtGuiSearchGroupSpec {
    category_name: *const c_char,
    show_header: u8,
    result_count: usize,
}

fn search_group_columns(viewport_width: i32, result_count: usize) -> u32 {
    if viewport_width <= 1 {
        return 2.min(result_count.max(1) as u32).max(1);
    }
    let usable_width = (viewport_width - 64).max(1);
    let columns_by_width = (usable_width / 144).max(1);
    let columns_by_count = (result_count as i32).clamp(1, 5);
    columns_by_width.min(columns_by_count).clamp(1, 5) as u32
}

#[no_mangle]
pub extern "C" fn lt_gui_search_viewport_capacity(width: i32, height: i32) -> usize {
    let width = width.max(1);
    let height = height.max(1);
    let columns = (((width - 64).max(1) + 16) / 148).clamp(1, 5);
    let rows = ((height + 67) / 68).max(1);
    columns.saturating_mul(rows) as usize
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_search_results_begin(
    root: *mut gtk::ffi::GtkWidget,
) -> bool {
    ensure_gtk_initialized();
    if root.is_null() { return false; }

    let widget: gtk::Widget = from_glib_none(root);
    let container = match widget.downcast::<gtk::Container>() {
        Ok(container) => container,
        Err(_) => return false,
    };

    for child in container.children() {
        container.remove(&child);
    }

    let results = gtk::Box::new(gtk::Orientation::Vertical, 0);
    results.set_widget_name("linuxtoys-search-results-container");
    results.set_margin_top(8);
    results.set_margin_bottom(4);
    container.add(&results);
    results.show();
    true
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_search_ensure_group(
    root: *mut gtk::ffi::GtkWidget,
    group_index: usize,
    spec: *const LtGuiSearchGroupSpec,
    viewport_width: i32,
) -> bool {
    ensure_gtk_initialized();
    if root.is_null() || spec.is_null() { return false; }

    let root_widget: gtk::Widget = from_glib_none(root);
    let results = match named_descendant(&root_widget, "linuxtoys-search-results-container")
        .and_then(|w| w.downcast::<gtk::Box>().ok())
    {
        Some(results) => results,
        None => return false,
    };

    let flowbox_name = format!("linuxtoys-search-group-{group_index}");
    if named_descendant(&root_widget, &flowbox_name).is_some() {
        return true;
    }

    let spec = &*spec;
    if spec.show_header != 0 {
        let header = gtk::Label::new(None);
        header.set_widget_name(&format!("linuxtoys-search-header-{group_index}"));
        header.set_markup(&format!(
            "<big><b>{}</b></big>",
            glib::markup_escape_text(&cstr(spec.category_name))
        ));
        header.set_halign(gtk::Align::Start);
        header.set_margin_top(12);
        header.set_margin_bottom(6);
        header.set_margin_start(32);
        header.style_context().add_class("title-2");
        results.pack_start(&header, false, false, 0);
        header.show();
    }

    let flowbox = gtk::FlowBox::new();
    flowbox.set_widget_name(&flowbox_name);
    flowbox.set_valign(gtk::Align::Start);
    flowbox.set_max_children_per_line(search_group_columns(viewport_width, spec.result_count));
    flowbox.set_activate_on_single_click(false);
    flowbox.set_selection_mode(gtk::SelectionMode::Single);
    flowbox.set_homogeneous(true);
    flowbox.set_margin_start(32);
    flowbox.set_margin_end(32);
    flowbox.set_margin_top(8);
    flowbox.set_margin_bottom(4);
    flowbox.set_column_spacing(16);
    flowbox.set_row_spacing(12);
    results.pack_start(&flowbox, false, false, 0);
    flowbox.show();
    true
}

#[repr(C)]
pub struct LtGuiFeaturedLargeCardSpec {
    name: *const c_char,
    description: *const c_char,
    icon_path: *const c_char,
    icon_name: *const c_char,
    badge_path: *const c_char,
    is_new: u8,
    height: i32,
}

unsafe fn create_featured_large_card_from_spec(
    spec: &LtGuiFeaturedLargeCardSpec,
) -> Option<gtk::EventBox> {
    let name = cstr(spec.name);
    let description = cstr(spec.description);
    let icon_path = cstr(spec.icon_path);
    let icon_name = cstr(spec.icon_name);
    let badge_path = cstr(spec.badge_path);
    let outer_height = if spec.height > 0 { spec.height } else { 116 };

    let icon = image(&icon_path, &icon_name, 64);
    icon.set_widget_name("linuxtoys-native-icon");
    icon.set_halign(gtk::Align::Center);
    icon.set_valign(gtk::Align::Center);

    let name_label = gtk::Label::new(None);
    name_label.set_widget_name("linuxtoys-native-name");
    name_label.set_markup(&format!(
        "<span size=\"large\"><b>{}</b></span>",
        glib::markup_escape_text(&name)
    ));
    name_label.set_line_wrap(true);
    name_label.set_lines(2);
    name_label.set_ellipsize(gtk::pango::EllipsizeMode::End);
    name_label.set_justify(gtk::Justification::Center);
    name_label.set_halign(gtk::Align::Fill);
    name_label.set_valign(gtk::Align::Center);
    name_label.set_hexpand(true);

    let description_label = gtk::Label::new(None);
    description_label.set_widget_name("linuxtoys-native-description");
    description_label.set_markup(&format!(
        "<span>{}</span>",
        glib::markup_escape_text(&description)
    ));
    description_label.set_line_wrap(true);
    description_label.set_line_wrap_mode(gtk::pango::WrapMode::WordChar);
    description_label.set_ellipsize(gtk::pango::EllipsizeMode::End);
    description_label.set_lines(3);
    description_label.set_justify(gtk::Justification::Center);
    description_label.set_halign(gtk::Align::Fill);
    description_label.set_valign(gtk::Align::Center);
    description_label.set_hexpand(true);
    description_label.set_vexpand(true);
    description_label.style_context().add_class("dim-label");

    let text_box = gtk::Box::new(gtk::Orientation::Vertical, 6);
    text_box.set_hexpand(true);
    text_box.set_vexpand(true);
    text_box.set_valign(gtk::Align::Fill);
    text_box.pack_start(&name_label, true, true, 0);
    text_box.pack_start(&description_label, true, true, 0);

    let row = gtk::Box::new(gtk::Orientation::Horizontal, 16);
    row.set_margin_top(12);
    row.set_margin_bottom(12);
    row.set_margin_start(16);
    row.set_margin_end(16);
    // `outer_height` is the complete EventBox height. The row contributes 24 px
    // of vertical margins and the card surface contributes another 4 px top margin.
    // Account for both here so the large card's natural request is exactly the
    // height of two ordinary rows plus the GtkGrid row spacing.
    row.set_size_request(108, (outer_height - 28).max(1));
    row.pack_start(&icon, false, false, 0);
    row.pack_start(&text_box, true, true, 0);

    let surface = gtk::Box::new(gtk::Orientation::Horizontal, 0);
    surface.set_widget_name("linuxtoys-native-surface");
    surface.style_context().add_class("script-item");
    if spec.is_new != 0 { surface.style_context().add_class("script-item-new"); }
    surface.set_margin_top(4);
    surface.set_margin_start(4);
    surface.set_margin_end(4);
    surface.pack_start(&row, true, true, 0);

    let overlay = gtk::Overlay::new();
    overlay.set_widget_name("linuxtoys-native-overlay");
    overlay.add(&surface);
    if !badge_path.is_empty() {
        if let Some(pixbuf) = load_scaled(&badge_path, 20, 20) {
            let badge = gtk::Image::from_pixbuf(Some(&pixbuf));
            badge.set_widget_name("linuxtoys-native-badge");
            badge.set_halign(gtk::Align::End);
            badge.set_valign(gtk::Align::Start);
            overlay.add_overlay(&badge);
        }
    }

    let event_box = gtk::EventBox::new();
    event_box.set_size_request(128, outer_height);
    event_box.add(&overlay);
    event_box.set_events(
        event_box.events()
            | gdk::EventMask::ENTER_NOTIFY_MASK
            | gdk::EventMask::LEAVE_NOTIFY_MASK
            | gdk::EventMask::BUTTON_PRESS_MASK
            | gdk::EventMask::BUTTON_RELEASE_MASK,
    );
    event_box.show_all();
    Some(event_box)
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_grid_attach_featured_large_card(
    grid: *mut gtk::ffi::GtkWidget,
    spec: *const LtGuiFeaturedLargeCardSpec,
    column: i32,
    row: i32,
) -> bool {
    ensure_gtk_initialized();
    if grid.is_null() || spec.is_null() { return false; }
    let widget: gtk::Widget = from_glib_none(grid);
    let grid = match widget.downcast::<gtk::Grid>() {
        Ok(grid) => grid,
        Err(_) => return false,
    };
    let card = match create_featured_large_card_from_spec(&*spec) {
        Some(card) => card,
        None => return false,
    };
    grid.attach(&card, column, row, 1, 2);
    true
}

#[repr(C)]
pub struct LtGuiGridPosition {
    column: i32,
    row: i32,
}

fn named_descendant(root: &gtk::Widget, name: &str) -> Option<gtk::Widget> {
    if root.widget_name().as_str() == name {
        return Some(root.clone());
    }
    if let Ok(container) = root.clone().downcast::<gtk::Container>() {
        for child in container.children() {
            if let Some(found) = named_descendant(&child, name) {
                return Some(found);
            }
        }
    }
    None
}

unsafe fn update_item_card_from_spec(
    event_box: &gtk::EventBox,
    spec: &LtGuiItemCardSpec,
) -> bool {
    // Featured ordinary cards never use checklist/remove controls. Refuse a
    // structural role change rather than trying to mutate the widget hierarchy.
    if spec.removable != 0 || spec.checklist != 0 {
        return false;
    }

    let root: gtk::Widget = event_box.clone().upcast();
    let label = match named_descendant(&root, "linuxtoys-native-name")
        .and_then(|w| w.downcast::<gtk::Label>().ok())
    {
        Some(label) => label,
        None => return false,
    };
    let icon = match named_descendant(&root, "linuxtoys-native-icon")
        .and_then(|w| w.downcast::<gtk::Image>().ok())
    {
        Some(icon) => icon,
        None => return false,
    };
    let surface = match named_descendant(&root, "linuxtoys-native-surface") {
        Some(surface) => surface,
        None => return false,
    };
    let overlay = match named_descendant(&root, "linuxtoys-native-overlay")
        .and_then(|w| w.downcast::<gtk::Overlay>().ok())
    {
        Some(overlay) => overlay,
        None => return false,
    };

    let name = cstr(spec.name);
    let icon_path = cstr(spec.icon_path);
    let icon_name = cstr(spec.icon_name);
    let badge_path = cstr(spec.badge_path);

    if spec.bold != 0 {
        let escaped = glib::markup_escape_text(&name);
        label.set_markup(&format!("<b>{escaped}</b>"));
    } else {
        label.set_text(&name);
    }

    set_image_source(&icon, &icon_path, &icon_name, 38);

    let style = surface.style_context();
    if spec.is_new != 0 {
        style.add_class("script-item-new");
    } else {
        style.remove_class("script-item-new");
    }

    if let Some(old_badge) = named_descendant(&root, "linuxtoys-native-badge") {
        overlay.remove(&old_badge);
    }
    if !badge_path.is_empty() {
        if let Some(pixbuf) = load_scaled(&badge_path, 20, 20) {
            let badge = gtk::Image::from_pixbuf(Some(&pixbuf));
            badge.set_widget_name("linuxtoys-native-badge");
            badge.set_halign(gtk::Align::End);
            badge.set_valign(gtk::Align::Start);
            overlay.add_overlay(&badge);
            badge.show();
        }
    }

    true
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_grid_attach_item_cards(
    grid: *mut gtk::ffi::GtkWidget,
    specs: *const LtGuiItemCardSpec,
    positions: *const LtGuiGridPosition,
    count: usize,
) -> usize {
    ensure_gtk_initialized();

    if grid.is_null() || specs.is_null() || positions.is_null() {
        return 0;
    }

    let widget: gtk::Widget = from_glib_none(grid);
    let grid = match widget.downcast::<gtk::Grid>() {
        Ok(grid) => grid,
        Err(_) => return 0,
    };
    let specs = std::slice::from_raw_parts(specs, count);
    let positions = std::slice::from_raw_parts(positions, count);

    let mut cards = Vec::with_capacity(count);
    for spec in specs {
        match create_item_card_from_spec(spec) {
            Some(card) => cards.push(card),
            None => return 0,
        }
    }

    for (card, position) in cards.into_iter().zip(positions.iter()) {
        grid.attach(&card, position.column, position.row, 1, 1);
    }
    count
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_update_item_card(
    card: *mut gtk::ffi::GtkWidget,
    spec: *const LtGuiItemCardSpec,
) -> bool {
    ensure_gtk_initialized();

    if card.is_null() || spec.is_null() {
        return false;
    }

    let widget: gtk::Widget = from_glib_none(card);
    let event_box = match widget.downcast::<gtk::EventBox>() {
        Ok(event_box) => event_box,
        Err(_) => return false,
    };
    update_item_card_from_spec(&event_box, &*spec)
}


#[repr(C)]
pub struct LtGuiInfosHeadSpec {
    execute_label: *const c_char,
    remove_label: *const c_char,
    report_label: *const c_char,
    show_terminal_controls: u8,
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_populate_infos_head(
    root: *mut gtk::ffi::GtkWidget,
    spec: *const LtGuiInfosHeadSpec,
) -> bool {
    ensure_gtk_initialized();

    if root.is_null() || spec.is_null() {
        return false;
    }

    let widget: gtk::Widget = from_glib_none(root);
    let root = match widget.downcast::<gtk::Box>() {
        Ok(root) => root,
        Err(_) => return false,
    };
    let spec = &*spec;

    let infos = gtk::Box::new(gtk::Orientation::Vertical, 4);
    infos.set_widget_name("linuxtoys-infos-vbox");

    let name = gtk::Label::new(None);
    name.set_widget_name("linuxtoys-infos-name");
    name.set_halign(gtk::Align::Start);

    let description = gtk::Label::new(None);
    description.set_widget_name("linuxtoys-infos-description");
    description.set_halign(gtk::Align::Start);
    description.set_xalign(0.0);
    description.set_line_wrap(true);
    description.set_line_wrap_mode(gtk::pango::WrapMode::WordChar);

    let repository = gtk::Label::new(None);
    repository.set_widget_name("linuxtoys-infos-repository");
    repository.set_halign(gtk::Align::Start);

    let header = gtk::Box::new(gtk::Orientation::Horizontal, 12);
    header.set_widget_name("linuxtoys-infos-header");
    header.set_margin_start(32);
    header.set_margin_top(12);
    header.set_margin_end(32);
    header.set_margin_bottom(5);

    let icon = gtk::Image::new();
    icon.set_widget_name("linuxtoys-infos-icon");
    icon.set_margin_end(20);
    header.pack_start(&icon, false, false, 0);

    infos.pack_start(&name, false, false, 0);
    infos.pack_start(&description, false, false, 0);
    infos.pack_start(&repository, false, false, 0);
    header.pack_start(&infos, true, true, 0);
    root.pack_start(&header, false, false, 0);

    let controls = gtk::Box::new(gtk::Orientation::Horizontal, 12);
    controls.set_widget_name("linuxtoys-infos-controls");

    let run = gtk::Button::with_label(&cstr(spec.execute_label));
    run.set_widget_name("linuxtoys-infos-run");
    run.set_image(Some(&gtk::Image::from_icon_name(
        Some("emblem-system-symbolic"),
        gtk::IconSize::Button,
    )));
    run.set_halign(gtk::Align::Start);
    run.set_size_request(125, 35);

    let remove = gtk::Button::with_label(&cstr(spec.remove_label));
    remove.set_widget_name("linuxtoys-infos-remove");
    remove.set_image(Some(&gtk::Image::from_icon_name(
        Some("edit-delete-symbolic"),
        gtk::IconSize::Button,
    )));
    remove.set_halign(gtk::Align::Start);
    remove.set_size_request(125, 35);

    let report = gtk::Button::with_label(&cstr(spec.report_label));
    report.set_widget_name("linuxtoys-infos-report");
    report.set_image(Some(&gtk::Image::from_icon_name(
        Some("dialog-warning-symbolic"),
        gtk::IconSize::Button,
    )));
    report.set_halign(gtk::Align::Start);
    report.set_size_request(150, 35);

    let progress = gtk::ProgressBar::new();
    progress.set_widget_name("linuxtoys-infos-progress");
    progress.set_show_text(true);
    progress.set_fraction(0.0);

    controls.pack_start(&run, false, false, 0);
    controls.pack_start(&remove, false, false, 0);
    controls.pack_start(&report, false, false, 0);
    controls.pack_start(&progress, true, true, 0);

    // Keep the controls parented even for app-page headers so Python can safely
    // reacquire the complete InfosHead API through the widget tree.  no-show-all
    // preserves the old show_terminal_controls=False behavior without leaving
    // Rust-owned, unparented widgets that the bridge cannot recover.
    infos.pack_start(&controls, false, false, 10);
    if spec.show_terminal_controls == 0 {
        controls.set_no_show_all(true);
        controls.hide();
    }

    true
}


#[repr(C)]
pub struct LtGuiAppPageHeaderSpec {
    aggregate_markup: *const c_char,
    install_label: *const c_char,
    open_label: *const c_char,
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_populate_app_page_header(
    overlay: *mut gtk::ffi::GtkWidget,
    infos_box: *mut gtk::ffi::GtkWidget,
    repo_label: *mut gtk::ffi::GtkWidget,
    spec: *const LtGuiAppPageHeaderSpec,
    show_aggregate: u8,
    show_rating: u8,
) -> bool {
    ensure_gtk_initialized();

    if overlay.is_null() || infos_box.is_null() || repo_label.is_null() || spec.is_null() {
        return false;
    }

    let overlay_widget: gtk::Widget = from_glib_none(overlay);
    let overlay = match overlay_widget.downcast::<gtk::Overlay>() {
        Ok(value) => value,
        Err(_) => return false,
    };
    let infos_widget: gtk::Widget = from_glib_none(infos_box);
    let infos = match infos_widget.downcast::<gtk::Box>() {
        Ok(value) => value,
        Err(_) => return false,
    };
    let repo_widget: gtk::Widget = from_glib_none(repo_label);
    let repo = match repo_widget.downcast::<gtk::Label>() {
        Ok(value) => value,
        Err(_) => return false,
    };
    let spec = &*spec;

    if show_aggregate != 0 {
        let aggregate = gtk::Label::new(None);
        aggregate.set_widget_name("linuxtoys-app-aggregate-rating");
        aggregate.set_markup(&cstr(spec.aggregate_markup));
        aggregate.set_halign(gtk::Align::End);
        aggregate.set_valign(gtk::Align::Start);
        aggregate.set_margin_top(16);
        aggregate.set_margin_end(32);
        aggregate.set_selectable(false);
        aggregate.set_can_focus(false);
        overlay.add_overlay(&aggregate);
    }

    if show_rating != 0 {
        if let Some(parent) = repo.parent() {
            if let Ok(container) = parent.downcast::<gtk::Container>() {
                container.remove(&repo);
            }
        }

        let row = gtk::Box::new(gtk::Orientation::Horizontal, 12);
        row.set_widget_name("linuxtoys-app-repository-rating-row");
        row.set_hexpand(true);
        row.set_halign(gtk::Align::Fill);
        row.set_valign(gtk::Align::Center);
        row.pack_start(&repo, false, false, 0);

        let spacer = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        spacer.set_hexpand(true);
        row.pack_start(&spacer, true, true, 0);

        let rating = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        rating.set_widget_name("linuxtoys-app-rating-control");
        rating.set_halign(gtk::Align::End);
        rating.set_valign(gtk::Align::Center);

        let provider = gtk::CssProvider::new();
        let _ = provider.load_from_data(
            b"button { min-width: 20px; min-height: 20px; padding: 1px 3px; margin: 0; }"
        );

        for stars in 1..=5 {
            let button = gtk::Button::with_label("☆");
            button.set_widget_name(&format!("linuxtoys-app-rating-{stars}"));
            button.set_relief(gtk::ReliefStyle::None);
            button.set_can_focus(false);
            button.set_size_request(24, 24);
            button.style_context().add_provider(
                &provider,
                gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
            );
            rating.pack_start(&button, false, false, 0);
        }

        row.pack_end(&rating, false, false, 0);
        infos.pack_start(&row, false, false, 0);
        infos.reorder_child(&row, 3);
    }

    let controls = gtk::Box::new(gtk::Orientation::Horizontal, 12);
    controls.set_widget_name("linuxtoys-app-actions");
    controls.set_hexpand(true);

    let install = gtk::Button::with_label(&cstr(spec.install_label));
    install.set_widget_name("linuxtoys-app-install");
    install.set_image(Some(&gtk::Image::from_icon_name(
        Some("emblem-system-symbolic"),
        gtk::IconSize::Button,
    )));
    install.set_size_request(125, 35);
    controls.pack_start(&install, false, false, 0);

    let open = gtk::Button::new();
    open.set_widget_name("linuxtoys-app-open");

    // Use an explicit child instead of Button::set_label() + set_image().
    // This keeps the icon visible consistently across GTK3 themes and matches
    // the Python _set_action_button_content() presentation.
    let open_content = gtk::Box::new(gtk::Orientation::Horizontal, 6);
    open_content.set_halign(gtk::Align::Center);
    open_content.set_valign(gtk::Align::Center);
    open_content.set_margin_start(8);
    open_content.set_margin_end(8);

    let open_icon = gtk::Image::from_icon_name(
        Some("media-playback-start-symbolic"),
        gtk::IconSize::Button,
    );
    let open_label = gtk::Label::new(Some(&cstr(spec.open_label)));
    open_content.pack_start(&open_icon, false, false, 0);
    open_content.pack_start(&open_label, false, false, 0);
    open.add(&open_content);

    open.set_no_show_all(true);
    open.hide();
    controls.pack_start(&open, false, false, 0);

    infos.pack_start(&controls, false, false, 10);
    true
}


#[repr(C)]
pub struct LtGuiListRowSpec {
    key: *const c_char,
    name: *const c_char,
    secondary: *const c_char,
    icon_path: *const c_char,
    icon_name: *const c_char,
    status_icon: *const c_char,
    action_tooltip: *const c_char,
    secondary_visible: u8,
    spinner: u8,
    launch: u8,
    destructive_action: u8,
    action_kind: u8,
    embedded: u8,
}

unsafe fn create_list_row_from_spec(spec: &LtGuiListRowSpec) -> gtk::Box {
    let key = cstr(spec.key);
    let name_text = cstr(spec.name);
    let secondary_text = cstr(spec.secondary);
    let icon_path = cstr(spec.icon_path);
    let icon_name = cstr(spec.icon_name);
    let status_icon = cstr(spec.status_icon);
    let action_tooltip = cstr(spec.action_tooltip);

    let outer = gtk::Box::new(gtk::Orientation::Horizontal, 12);
    outer.set_widget_name(&format!("linuxtoys-list-row-{key}"));
    outer.style_context().add_class("queue-item");
    outer.set_margin_top(2);
    outer.set_margin_bottom(2);

    let icon = image(&icon_path, &icon_name, 38);
    icon.set_widget_name("linuxtoys-list-row-icon");
    outer.pack_start(&icon, false, false, 12);

    let text = gtk::Box::new(gtk::Orientation::Vertical, 2);
    text.set_widget_name("linuxtoys-list-row-text");
    text.set_valign(gtk::Align::Center);

    let name = gtk::Label::new(None);
    name.set_widget_name("linuxtoys-list-row-name");
    name.set_markup(&format!("<b>{}</b>", glib::markup_escape_text(&name_text)));
    name.set_halign(gtk::Align::Start);
    name.set_valign(gtk::Align::Center);
    if spec.embedded != 0 {
        name.set_ellipsize(gtk::pango::EllipsizeMode::End);
        name.set_single_line_mode(true);
        name.set_hexpand(true);
        name.set_halign(gtk::Align::Fill);
        name.set_xalign(0.0);
        text.set_hexpand(true);
    }
    text.pack_start(&name, false, false, 0);

    let secondary = gtk::Label::new(Some(&secondary_text));
    secondary.set_widget_name("linuxtoys-list-row-secondary");
    secondary.set_halign(gtk::Align::Start);
    if spec.embedded != 0 {
        secondary.set_ellipsize(gtk::pango::EllipsizeMode::End);
        secondary.set_single_line_mode(true);
        secondary.set_hexpand(true);
        secondary.set_halign(gtk::Align::Fill);
        secondary.set_xalign(0.0);
    }
    secondary.style_context().add_class("dim-label");
    if spec.secondary_visible == 0 {
        secondary.set_no_show_all(true);
        secondary.hide();
    }
    text.pack_start(&secondary, false, false, 0);
    outer.pack_start(&text, true, true, 0);

    if spec.spinner != 0 {
        let indicator = gtk::Spinner::new();
        indicator.set_widget_name("linuxtoys-list-row-status");
        indicator.set_size_request(16, 16);
        indicator.set_halign(gtk::Align::Center);
        indicator.set_valign(gtk::Align::Center);
        indicator.start();

        // Keep status indicators in the same button-sized slot used by the
        // ordinary action icons so running rows do not shift horizontally.
        let slot = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        slot.set_widget_name("linuxtoys-list-row-status-slot");
        slot.set_size_request(34, 34);
        slot.set_halign(gtk::Align::Center);
        slot.set_valign(gtk::Align::Center);
        slot.pack_start(&indicator, true, true, 0);
        outer.pack_start(&slot, false, false, 4);
    } else if !status_icon.is_empty() {
        let indicator = gtk::Image::from_icon_name(Some(&status_icon), gtk::IconSize::Button);
        indicator.set_widget_name("linuxtoys-list-row-status");
        indicator.set_halign(gtk::Align::Center);
        indicator.set_valign(gtk::Align::Center);

        let slot = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        slot.set_widget_name("linuxtoys-list-row-status-slot");
        slot.set_size_request(34, 34);
        slot.set_halign(gtk::Align::Center);
        slot.set_valign(gtk::Align::Center);
        slot.pack_start(&indicator, true, true, 0);
        outer.pack_start(&slot, false, false, 4);
    }

    if spec.launch != 0 {
        let launch = gtk::Button::from_icon_name(
            Some("media-playback-start-symbolic"),
            gtk::IconSize::Button,
        );
        launch.set_widget_name("linuxtoys-list-row-launch");
        launch.set_relief(gtk::ReliefStyle::None);
        outer.pack_start(&launch, false, false, 0);
    }

    if spec.action_kind != 0 {
        let icon_name = if spec.destructive_action != 0 {
            "edit-delete-symbolic"
        } else if spec.action_kind == 3 {
            "list-add-symbolic"
        } else {
            "process-stop-symbolic"
        };
        let action = gtk::Button::from_icon_name(Some(icon_name), gtk::IconSize::Button);
        action.set_widget_name("linuxtoys-list-row-action");
        action.set_relief(gtk::ReliefStyle::None);
        if !action_tooltip.is_empty() {
            action.set_tooltip_text(Some(&action_tooltip));
        }
        if spec.destructive_action != 0 {
            action.style_context().add_class("destructive-action");
            action.style_context().add_class("queue-remove");
        }
        outer.pack_start(&action, false, false, 4);
    }

    outer.show_all();
    outer
}


unsafe fn update_list_row_from_spec(row: &gtk::Box, spec: &LtGuiListRowSpec) -> bool {
    let root: gtk::Widget = row.clone().upcast();
    let name = match named_descendant(&root, "linuxtoys-list-row-name")
        .and_then(|w| w.downcast::<gtk::Label>().ok())
    {
        Some(value) => value,
        None => return false,
    };
    let secondary = match named_descendant(&root, "linuxtoys-list-row-secondary")
        .and_then(|w| w.downcast::<gtk::Label>().ok())
    {
        Some(value) => value,
        None => return false,
    };

    let name_text = cstr(spec.name);
    let secondary_text = cstr(spec.secondary);
    name.set_markup(&format!("<b>{}</b>", glib::markup_escape_text(&name_text)));
    secondary.set_text(&secondary_text);

    let embedded = spec.embedded != 0;
    name.set_ellipsize(if embedded {
        gtk::pango::EllipsizeMode::End
    } else {
        gtk::pango::EllipsizeMode::None
    });
    name.set_single_line_mode(embedded);
    name.set_hexpand(embedded);
    name.set_halign(if embedded { gtk::Align::Fill } else { gtk::Align::Start });
    name.set_xalign(0.0);
    secondary.set_ellipsize(if embedded {
        gtk::pango::EllipsizeMode::End
    } else {
        gtk::pango::EllipsizeMode::None
    });
    secondary.set_single_line_mode(embedded);
    secondary.set_hexpand(embedded);
    secondary.set_halign(if embedded { gtk::Align::Fill } else { gtk::Align::Start });
    secondary.set_xalign(0.0);
    if let Some(text) = named_descendant(&root, "linuxtoys-list-row-text")
        .and_then(|w| w.downcast::<gtk::Box>().ok())
    {
        text.set_hexpand(embedded);
    }

    if spec.secondary_visible != 0 {
        secondary.set_no_show_all(false);
        secondary.show();
    } else {
        secondary.set_no_show_all(true);
        secondary.hide();
    }

    // Status indicator changes between GtkSpinner and GtkImage. Replace its
    // complete fixed-size slot so both roles retain identical geometry.
    if let Some(old) = named_descendant(&root, "linuxtoys-list-row-status-slot") {
        row.remove(&old);
    } else if let Some(old) = named_descendant(&root, "linuxtoys-list-row-status") {
        // Compatibility with rows created by an older version of this code.
        row.remove(&old);
    }
    if spec.spinner != 0 {
        let indicator = gtk::Spinner::new();
        indicator.set_widget_name("linuxtoys-list-row-status");
        indicator.set_size_request(16, 16);
        indicator.set_halign(gtk::Align::Center);
        indicator.set_valign(gtk::Align::Center);
        indicator.start();

        let slot = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        slot.set_widget_name("linuxtoys-list-row-status-slot");
        slot.set_size_request(34, 34);
        slot.set_halign(gtk::Align::Center);
        slot.set_valign(gtk::Align::Center);
        slot.pack_start(&indicator, true, true, 0);
        row.pack_start(&slot, false, false, 4);
        row.reorder_child(&slot, 2);
        slot.show_all();
    } else {
        let status_icon = cstr(spec.status_icon);
        if !status_icon.is_empty() {
            let indicator = gtk::Image::from_icon_name(Some(&status_icon), gtk::IconSize::Button);
            indicator.set_widget_name("linuxtoys-list-row-status");
            indicator.set_halign(gtk::Align::Center);
            indicator.set_valign(gtk::Align::Center);

            let slot = gtk::Box::new(gtk::Orientation::Horizontal, 0);
            slot.set_widget_name("linuxtoys-list-row-status-slot");
            slot.set_size_request(34, 34);
            slot.set_halign(gtk::Align::Center);
            slot.set_valign(gtk::Align::Center);
            slot.pack_start(&indicator, true, true, 0);
            row.pack_start(&slot, false, false, 4);
            row.reorder_child(&slot, 2);
            slot.show_all();
        }
    }

    // Launch role can also change as installed-state metadata is refreshed.
    if let Some(old) = named_descendant(&root, "linuxtoys-list-row-launch") {
        row.remove(&old);
    }
    if spec.launch != 0 {
        let launch = gtk::Button::from_icon_name(
            Some("media-playback-start-symbolic"),
            gtk::IconSize::Button,
        );
        launch.set_widget_name("linuxtoys-list-row-launch");
        launch.set_relief(gtk::ReliefStyle::None);
        row.pack_end(&launch, false, false, 0);
        launch.show_all();
    }

    // Queue action role may appear/disappear or switch Cancel -> Remove.
    if let Some(old) = named_descendant(&root, "linuxtoys-list-row-action") {
        row.remove(&old);
    }
    if spec.action_kind != 0 {
        let action_icon = if spec.destructive_action != 0 {
            "edit-delete-symbolic"
        } else if spec.action_kind == 3 {
            "list-add-symbolic"
        } else {
            "process-stop-symbolic"
        };
        let action = gtk::Button::from_icon_name(Some(action_icon), gtk::IconSize::Button);
        action.set_widget_name("linuxtoys-list-row-action");
        action.set_relief(gtk::ReliefStyle::None);
        let tooltip = cstr(spec.action_tooltip);
        if !tooltip.is_empty() {
            action.set_tooltip_text(Some(&tooltip));
        }
        if spec.destructive_action != 0 {
            action.style_context().add_class("destructive-action");
            action.style_context().add_class("queue-remove");
        }
        row.pack_end(&action, false, false, 4);
        action.show_all();
    }

    true
}



fn clear_list_container(container: &gtk::Box) {
    for child in container.children() {
        container.remove(&child);
        // gtk3-rs marks WidgetExtManual::destroy() unsafe because callers must
        // ensure the widget is no longer used. It has just been detached from
        // this dedicated native list container and is not retained here.
        unsafe {
            child.destroy();
        }
    }
}

fn list_state_widget(container: &gtk::Box, state_kind: u8, empty_text: &str) {
    clear_list_container(container);
    match state_kind {
        1 => {
            let spinner = gtk::Spinner::new();
            spinner.set_widget_name("linuxtoys-list-state-loading");
            spinner.start();
            spinner.set_halign(gtk::Align::Center);
            spinner.set_margin_top(24);
            container.pack_start(&spinner, false, false, 0);
            spinner.show();
        }
        2 => {
            let label = gtk::Label::new(Some(empty_text));
            label.set_widget_name("linuxtoys-list-state-empty");
            label.style_context().add_class("dim-label");
            label.set_margin_top(24);
            container.pack_start(&label, false, false, 0);
            label.show();
        }
        _ => {}
    }
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_reconcile_list_rows(
    container: *mut gtk::ffi::GtkWidget,
    specs: *const LtGuiListRowSpec,
    count: usize,
    state_kind: u8,
    empty_text: *const c_char,
) -> usize {
    ensure_gtk_initialized();
    if container.is_null() {
        return 0;
    }

    let widget: gtk::Widget = from_glib_none(container);
    let container = match widget.downcast::<gtk::Box>() {
        Ok(value) => value,
        Err(_) => return 0,
    };

    if state_kind != 0 {
        list_state_widget(&container, state_kind, &cstr(empty_text));
        return 0;
    }

    // Content state owns the entire dedicated list box. Remove loading/empty
    // presentation and index retained native rows by their stable key.
    let mut existing: HashMap<String, gtk::Box> = HashMap::new();
    for child in container.children() {
        let name = child.widget_name().to_string();
        if let Some(key) = name.strip_prefix("linuxtoys-list-row-") {
            if let Ok(row) = child.clone().downcast::<gtk::Box>() {
                existing.insert(key.to_owned(), row);
                continue;
            }
        }
        container.remove(&child);
        child.destroy();
    }

    if count == 0 {
        for (_key, row) in existing {
            container.remove(&row);
            row.destroy();
        }
        return 0;
    }
    if specs.is_null() {
        return 0;
    }

    let specs = std::slice::from_raw_parts(specs, count);
    for (position, spec) in specs.iter().enumerate() {
        let key = cstr(spec.key);
        let row = if let Some(row) = existing.remove(&key) {
            if !update_list_row_from_spec(&row, spec) {
                container.remove(&row);
                row.destroy();
                let replacement = create_list_row_from_spec(spec);
                container.pack_start(&replacement, false, false, 0);
                replacement
            } else {
                row
            }
        } else {
            let row = create_list_row_from_spec(spec);
            container.pack_start(&row, false, false, 0);
            row
        };
        container.reorder_child(&row, position as i32);
        row.show_all();
    }

    for (_key, row) in existing {
        container.remove(&row);
        row.destroy();
    }

    count
}

fn text_tag(
    buffer: &gtk::TextBuffer,
    name: &str,
    props: &[(&str, &dyn glib::ToValue)],
) -> gtk::TextTag {
    let tag = gtk::TextTag::new(Some(name));

    for (property, value) in props {
        tag.set_property_from_value(property, &value.to_value());
    }

    if let Some(table) = buffer.tag_table() {
        table.add(&tag);
    }

    tag
}

fn insert_tagged(
    buffer: &gtk::TextBuffer,
    text: &str,
    tags: &[&gtk::TextTag],
) {
    if text.is_empty() {
        return;
    }

    let mut start = buffer.end_iter();
    let start_offset = start.offset();

    buffer.insert(&mut start, text);

    if tags.is_empty() {
        return;
    }

    let range_start = buffer.iter_at_offset(start_offset);
    let range_end = buffer.end_iter();

    for &tag in tags {
        buffer.apply_tag(tag, &range_start, &range_end);
    }
}

fn hex_bytes(value: &str) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(value.len() * 2);
    for byte in value.as_bytes() {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

struct MdTags {
    bold: gtk::TextTag,
    italic: gtk::TextTag,
    code: gtk::TextTag,
    code_block: gtk::TextTag,
    table_header: gtk::TextTag,
    table: gtk::TextTag,
    strike: gtk::TextTag,
    heading: gtk::TextTag,
    base: gtk::TextTag,
    lead: gtk::TextTag,
    quote: gtk::TextTag,
    list: gtk::TextTag,
    rule: gtk::TextTag,
}

fn markdown_tags(buffer: &gtk::TextBuffer) -> MdTags {
    use gtk::pango::Style;
    MdTags {
        bold: text_tag(buffer, "md-bold", &[("weight", &700i32)]),
        italic: text_tag(buffer, "md-italic", &[("style", &Style::Italic)]),
        code: text_tag(buffer, "md-code", &[("family", &"monospace")]),
        code_block: text_tag(buffer, "md-code-block", &[
            ("family", &"monospace"), ("left-margin", &14i32), ("right-margin", &14i32),
            ("pixels-above-lines", &3i32), ("pixels-below-lines", &3i32),
        ]),
        table_header: text_tag(buffer, "md-table-header", &[("family", &"monospace"), ("weight", &700i32)]),
        table: text_tag(buffer, "md-table", &[("family", &"monospace")]),
        strike: text_tag(buffer, "md-strike", &[("strikethrough", &true)]),
        heading: text_tag(buffer, "md-heading", &[("weight", &700i32), ("scale", &1.08f64)]),
        base: text_tag(buffer, "md-base", &[("scale", &1.10f64)]),
        lead: text_tag(buffer, "md-lead", &[("scale", &1.20f64)]),
        quote: text_tag(buffer, "md-quote", &[("style", &Style::Italic), ("left-margin", &18i32), ("right-margin", &8i32)]),
        list: text_tag(buffer, "md-list", &[("left-margin", &18i32), ("indent", &-12i32), ("scale", &1.10f64)]),
        rule: text_tag(buffer, "md-rule", &[]),
    }
}

fn find_inline_token(value: &str) -> Option<(usize, usize, &'static str, String, Option<String>)> {
    // Earliest token wins; equal starts preserve the Python regex's precedence.
    let mut best: Option<(usize, usize, usize, &'static str, String, Option<String>)> = None;
    let mut consider = |start: usize, end: usize, pri: usize, kind: &'static str, body: String, extra: Option<String>| {
        if best.as_ref().map_or(true, |b| (start, pri) < (b.0, b.2)) {
            best = Some((start, end, pri, kind, body, extra));
        }
    };
    if let Some(s) = value.find('`') { if let Some(e) = value[s+1..].find('`') { consider(s, s+1+e+1, 0, "code", value[s+1..s+1+e].to_string(), None); } }
    if let Some(s) = value.find('[') { if let Some(mid) = value[s+1..].find("](") { let m=s+1+mid; if let Some(e)=value[m+2..].find(')') { let inside=&value[m+2..m+2+e]; let url=inside.split_whitespace().next().unwrap_or(""); if !url.is_empty() { consider(s,m+2+e+1,1,"link",value[s+1..m].to_string(),Some(url.to_string())); } } } }
    for (pat, pri, kind) in [("**",2,"bold"),("__",3,"bold"),("~~",4,"strike")] { if let Some(s)=value.find(pat) { if let Some(e)=value[s+2..].find(pat) { consider(s,s+2+e+2,pri,kind,value[s+2..s+2+e].to_string(),None); } } }
    if let Some(s)=value.find('*') { if let Some(e)=value[s+1..].find('*') { consider(s,s+1+e+1,5,"italic",value[s+1..s+1+e].to_string(),None); } }
    // Underscore emphasis is deliberately conservative like Python's (?<!\\w)...(?!\\w).
    for (s, _) in value.match_indices('_') { if s>0 && value[..s].chars().next_back().map_or(false, |c| c.is_alphanumeric() || c=='_') { continue; } if let Some(rel)=value[s+1..].find('_') { let e=s+1+rel; if value[e+1..].chars().next().map_or(false, |c| c.is_alphanumeric() || c=='_') { continue; } consider(s,e+1,6,"italic",value[s+1..e].to_string(),None); break; } }
    best.map(|(a,b,_,k,v,e)|(a,b,k,v,e))
}

fn insert_inline(buffer: &gtk::TextBuffer, value: &str, base: &[&gtk::TextTag], tags: &MdTags) {
    let Some((start,end,kind,body,extra)) = find_inline_token(value) else { insert_tagged(buffer,value,base); return; };
    insert_tagged(buffer,&value[..start],base);
    let mut nested: Vec<&gtk::TextTag> = base.to_vec();
    match kind {
        "code" => { nested.push(&tags.code); insert_tagged(buffer,&body,&nested); }
        "bold" => { nested.push(&tags.bold); insert_inline(buffer,&body,&nested,tags); }
        "strike" => { nested.push(&tags.strike); insert_inline(buffer,&body,&nested,tags); }
        "italic" => { nested.push(&tags.italic); insert_inline(buffer,&body,&nested,tags); }
        "link" => {
            use gtk::pango::Underline;
            let url=extra.unwrap_or_default();
            let link=text_tag(buffer,&format!("md-link-{}",hex_bytes(&url)),&[("underline",&Underline::Single)]);
            nested.push(&link); insert_inline(buffer,&body,&nested,tags);
        }
        _ => insert_tagged(buffer,&body,&nested),
    }
    insert_inline(buffer,&value[end..],base,tags);
}

fn split_table_row(mut value: &str) -> Vec<String> {
    value=value.trim();
    if value.starts_with('|') { value=&value[1..]; }
    if value.ends_with('|') && !value.ends_with("\\|") { value=&value[..value.len()-1]; }
    let mut cells=Vec::new(); let mut current=String::new(); let mut escaped=false;
    for ch in value.chars() { if escaped { current.push(ch); escaped=false; } else if ch=='\\' { escaped=true; current.push(ch); } else if ch=='|' { cells.push(current.trim().to_string()); current.clear(); } else { current.push(ch); } }
    cells.push(current.trim().to_string()); cells
}

fn table_separator(value:&str)->Option<Vec<u8>> { let cells=split_table_row(value); if cells.is_empty(){return None;} let mut out=Vec::new(); for cell in cells { let c:String=cell.chars().filter(|x|!x.is_whitespace()).collect(); let core=c.trim_matches(':'); if core.len()<3 || !core.chars().all(|x|x=='-'){return None;} out.push(if c.starts_with(':')&&c.ends_with(':'){1}else if c.ends_with(':'){2}else{0}); } Some(out) }
fn plain_table_cell(s:&str)->String { s.chars().filter(|c| !matches!(c,'`'|'*'|'_'|'~')).collect() }

#[no_mangle]
pub unsafe extern "C" fn lt_gui_populate_markdown_buffer(buffer:*mut gtk::ffi::GtkTextBuffer, text:*const c_char)->bool {
    ensure_gtk_initialized(); if buffer.is_null(){return false;} let buffer:gtk::TextBuffer=from_glib_none(buffer); buffer.set_text(""); let source=cstr(text); let tags=markdown_tags(&buffer); let lines:Vec<&str>=source.lines().collect();
    let mut i=0usize; let mut in_fence=false; let mut fence_char='`'; let mut fence_len=0usize; let mut code_lines:Vec<String>=Vec::new(); let mut lead_started=false; let mut lead_finished=false;
    while i<lines.len(){ let raw=lines[i]; let line=raw.trim_end();
        let trimmed=line.trim_start(); let fence_run=trimmed.chars().take_while(|c|*c=='`'||*c=='~').collect::<String>();
        if in_fence { let closing=!fence_run.is_empty() && fence_run.chars().all(|c|c==fence_char) && fence_run.len()>=fence_len && trimmed[fence_run.len()..].trim().is_empty(); if closing { insert_tagged(&buffer,&code_lines.join("\n"),&[&tags.code_block]); code_lines.clear(); in_fence=false; if i+1<lines.len(){insert_tagged(&buffer,"\n",&[]);} } else {code_lines.push(raw.to_string());} i+=1; continue; }
        if fence_run.len()>=3 && fence_run.chars().all(|c|c==fence_run.chars().next().unwrap()) && line.len()-trimmed.len()<=3 { in_fence=true; fence_char=fence_run.chars().next().unwrap(); fence_len=fence_run.len(); i+=1; continue; }
        if line.contains('|') && i+1<lines.len(){ if let Some(aligns)=table_separator(lines[i+1]) { let mut rows=vec![split_table_row(line)]; i+=2; while i<lines.len() && lines[i].contains('|') && !lines[i].trim().is_empty(){rows.push(split_table_row(lines[i]));i+=1;} let cols=rows.iter().map(|r|r.len()).max().unwrap_or(0); for r in &mut rows {r.resize(cols,String::new());} let widths: Vec<usize> = (0..cols).map(|c|rows.iter().map(|r|plain_table_cell(&r[c]).chars().count()).max().unwrap_or(0).min(40)).collect(); for (ri,row) in rows.iter().enumerate(){ let mut pieces=Vec::new(); for c in 0..cols {let mut p=plain_table_cell(&row[c]); let w=widths[c]; if p.chars().count()>w {p=p.chars().take(w.saturating_sub(1).max(1)).collect::<String>()+"…";} let n=p.chars().count(); let pad=w.saturating_sub(n); p=match aligns.get(c).copied().unwrap_or(0){2=>format!("{}{}"," ".repeat(pad),p),1=>{let l=pad/2;format!("{}{}{}"," ".repeat(l),p," ".repeat(pad-l))},_=>format!("{}{}",p," ".repeat(pad))};pieces.push(p);} insert_tagged(&buffer,&pieces.join(" | "),&[if ri==0{&tags.table_header}else{&tags.table}]); if ri==0 {insert_tagged(&buffer,"\n",&[&tags.table]); let seps:Vec<String>=widths.iter().enumerate().map(|(c,w)|match aligns.get(c).copied().unwrap_or(0){1 if *w>=2=>format!(":{}:","-".repeat(w-2)),2 if *w>=1=>format!("{}:","-".repeat(w-1)),_=>"-".repeat(*w)}).collect();insert_tagged(&buffer,&seps.join("-+-"),&[&tags.table]);} if ri+1<rows.len(){insert_tagged(&buffer,"\n",&[]);} } if i<lines.len(){insert_tagged(&buffer,"\n",&[]);} continue; } }
        let t=line.trim_start(); let heading_hash=t.chars().take_while(|c|*c=='#').count(); let heading=heading_hash>=1&&heading_hash<=6&&t.chars().nth(heading_hash)==Some(' ');
        let quote=t.starts_with('>'); let unordered={let x=t.as_bytes();x.len()>2&&(x[0]==b'-'||x[0]==b'+'||x[0]==b'*')&&x[1]==b' '};
        let ordered_end=t.find(|c:char|c=='.'||c==')').filter(|&p|p>0&&t[..p].chars().all(|c|c.is_ascii_digit())&&t[p+1..].starts_with(' '));
        let compact:String=t.chars().filter(|c|!c.is_whitespace()).collect(); let rule=compact.len()>=3 && compact.chars().next().map_or(false,|c|matches!(c,'-'|'*'|'_')) && compact.chars().all(|c|c==compact.chars().next().unwrap());
        let is_block=heading||quote||unordered||ordered_end.is_some()||rule; if lead_started&&!lead_finished&&(t.is_empty()||is_block){lead_finished=true;}
        if rule {insert_tagged(&buffer,"────────────────────────",&[&tags.rule]);}
        else if heading {let body=t[heading_hash..].trim().trim_end_matches('#').trim_end();insert_inline(&buffer,body,&[&tags.heading],&tags);}
        else if unordered {let indent=line.len()-t.len();let depth=(indent/2).min(4);insert_tagged(&buffer,&format!("{}• ","    ".repeat(depth)),&[&tags.list]);insert_inline(&buffer,&t[2..],&[&tags.list],&tags);}
        else if let Some(p)=ordered_end {let indent=line.len()-t.len();let depth=(indent/2).min(4);insert_tagged(&buffer,&format!("{}{}. ","    ".repeat(depth),&t[..p]),&[&tags.list]);insert_inline(&buffer,t[p+2..].trim_start(),&[&tags.list],&tags);}
        else if quote {insert_inline(&buffer,t[1..].strip_prefix(' ').unwrap_or(&t[1..]),&[&tags.quote],&tags);}
        else if !t.is_empty(){if !lead_started{lead_started=true;} insert_inline(&buffer,line,&[if !lead_finished{&tags.lead}else{&tags.base}],&tags);}
        if i+1<lines.len(){insert_tagged(&buffer,"\n",&[]);} i+=1;
    }
    if in_fence {insert_tagged(&buffer,&code_lines.join("\n"),&[&tags.code_block]);} true
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_populate_appstream_buffer(buffer:*mut gtk::ffi::GtkTextBuffer, json:*const c_char)->bool {
    ensure_gtk_initialized(); if buffer.is_null(){return false;} let buffer:gtk::TextBuffer=from_glib_none(buffer); buffer.set_text(""); let value:serde_json::Value=match serde_json::from_str(&cstr(json)){Ok(v)=>v,Err(_)=>return false};
    use gtk::pango::Style;
    let base=text_tag(&buffer,"as-base",&[("scale",&1.10f64)]); let lead=text_tag(&buffer,"as-lead",&[("scale",&1.20f64)]); let list=text_tag(&buffer,"as-list",&[("left-margin",&18i32),("indent",&-12i32),("scale",&1.10f64)]); let bold=text_tag(&buffer,"as-bold",&[("weight",&700i32)]); let italic=text_tag(&buffer,"as-italic",&[("style",&Style::Italic)]); let code=text_tag(&buffer,"as-code",&[("family",&"monospace")]);
    let mut first=true; let mut rendered=0usize;
    let insert_spans=|buffer:&gtk::TextBuffer, spans:&serde_json::Value, base_tags:Vec<&gtk::TextTag>| { if let Some(items)=spans.as_array(){for span in items {let text=span.get("text").and_then(|v|v.as_str()).unwrap_or("");if text.is_empty(){continue;}let mut ts=base_tags.clone();if let Some(styles)=span.get("styles").and_then(|v|v.as_array()){for st in styles.iter().filter_map(|v|v.as_str()){match st{"bold"=>ts.push(&bold),"italic"=>ts.push(&italic),"code"=>ts.push(&code),_=>{}}}}insert_tagged(buffer,text,&ts);}} };
    if let Some(blocks)=value.as_array(){for block in blocks {let ty=block.get("type").and_then(|v|v.as_str()).unwrap_or("");match ty {"paragraph"=>{if rendered>0{insert_tagged(&buffer,"\n\n",&[]);}insert_spans(&buffer,block.get("spans").unwrap_or(&serde_json::Value::Null),vec![if first{&lead}else{&base}]);first=false;rendered+=1;},"unordered_list"|"ordered_list"=>{if rendered>0{insert_tagged(&buffer,"\n\n",&[]);}if let Some(items)=block.get("items").and_then(|v|v.as_array()){for (idx,item) in items.iter().enumerate(){if idx>0{insert_tagged(&buffer,"\n",&[]);}let prefix=if ty=="ordered_list"{format!("{}. ",idx+1)}else{"• ".to_string()};insert_tagged(&buffer,&prefix,&[&list]);insert_spans(&buffer,item,vec![&list]);}}rendered+=1;},_=>{}}}}
    true
}

#[repr(C)]
pub struct LtGuiDeveloperLineSpec {
    developer: *const c_char,
    badge_path: *const c_char,
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_add_app_page_developer_line(
    infos_box: *mut gtk::ffi::GtkWidget,
    spec: *const LtGuiDeveloperLineSpec,
) -> bool {
    ensure_gtk_initialized();
    if infos_box.is_null() || spec.is_null() { return false; }
    let widget: gtk::Widget = from_glib_none(infos_box);
    let infos = match widget.downcast::<gtk::Box>() { Ok(v) => v, Err(_) => return false };
    let spec = &*spec;
    let developer = cstr(spec.developer);
    if developer.is_empty() { return true; }

    let row = gtk::Box::new(gtk::Orientation::Horizontal, 6);
    row.set_widget_name("linuxtoys-app-developer-row");
    row.set_halign(gtk::Align::Start);
    row.set_margin_bottom(5);
    let label = gtk::Label::new(None);
    label.set_widget_name("linuxtoys-app-developer-label");
    label.set_markup(&format!("<span size=\"small\" weight=\"bold\">{}</span>", glib::markup_escape_text(&developer)));
    label.set_halign(gtk::Align::Start);
    label.set_selectable(false);
    label.set_can_focus(false);
    row.pack_start(&label, false, false, 0);

    let badge_path = cstr(spec.badge_path);
    if !badge_path.is_empty() {
        if let Some(pixbuf) = load_scaled(&badge_path, 16, 16) {
            let badge = gtk::Image::from_pixbuf(Some(&pixbuf));
            badge.set_widget_name("linuxtoys-app-developer-badge");
            row.pack_start(&badge, false, false, 0);
        }
    }
    infos.pack_start(&row, false, false, 0);
    infos.reorder_child(&row, 1);
    row.show_all();
    true
}

#[repr(C)]
pub struct LtGuiActionButtonSpec {
    label: *const c_char,
    icon_name: *const c_char,
    dropdown: u8,
    suggested: u8,
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_add_app_page_action_button(
    controls: *mut gtk::ffi::GtkWidget,
    spec: *const LtGuiActionButtonSpec,
) -> bool {
    ensure_gtk_initialized();
    if controls.is_null() || spec.is_null() { return false; }
    let widget: gtk::Widget = from_glib_none(controls);
    let controls = match widget.downcast::<gtk::Box>() { Ok(v) => v, Err(_) => return false };
    let spec = &*spec;
    let button: gtk::Widget = if spec.dropdown != 0 {
        gtk::MenuButton::new().upcast()
    } else {
        gtk::Button::new().upcast()
    };
    button.set_widget_name("linuxtoys-app-extra-action");
    if spec.suggested != 0 { button.style_context().add_class("suggested-action"); }
    let content = gtk::Box::new(gtk::Orientation::Horizontal, 6);
    content.set_margin_start(8);
    content.set_margin_end(8);
    let icon = gtk::Image::from_icon_name(Some(&cstr(spec.icon_name)), gtk::IconSize::Button);
    content.pack_start(&icon, false, false, 0);
    let label = gtk::Label::new(Some(cstr(spec.label).trim()));
    content.pack_start(&label, false, false, 0);
    if spec.dropdown != 0 {
        let arrow = gtk::Image::from_icon_name(Some("pan-down-symbolic"), gtk::IconSize::Button);
        content.pack_start(&arrow, false, false, 0);
    }
    if let Ok(container) = button.clone().downcast::<gtk::Container>() { container.add(&content); }
    controls.pack_start(&button, false, false, 0);
    button.show_all();
    true
}

#[repr(C)]
pub struct LtGuiScreenshotChromeSpec {
    previous_tooltip: *const c_char,
    next_tooltip: *const c_char,
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_populate_screenshot_chrome(
    outer: *mut gtk::ffi::GtkWidget,
    stack: *mut gtk::ffi::GtkWidget,
    spec: *const LtGuiScreenshotChromeSpec,
) -> bool {
    ensure_gtk_initialized();
    if outer.is_null() || stack.is_null() || spec.is_null() { return false; }
    let outer_w: gtk::Widget = from_glib_none(outer);
    let outer = match outer_w.downcast::<gtk::Box>() { Ok(v) => v, Err(_) => return false };
    let stack_w: gtk::Widget = from_glib_none(stack);
    let spec = &*spec;
    let row = gtk::Box::new(gtk::Orientation::Horizontal, 10);
    row.set_widget_name("linuxtoys-screenshot-row");
    let prev = gtk::Button::from_icon_name(Some("go-previous-symbolic"), gtk::IconSize::Button);
    prev.set_widget_name("linuxtoys-screenshot-previous");
    prev.set_tooltip_text(Some(&cstr(spec.previous_tooltip)));
    let next = gtk::Button::from_icon_name(Some("go-next-symbolic"), gtk::IconSize::Button);
    next.set_widget_name("linuxtoys-screenshot-next");
    next.set_tooltip_text(Some(&cstr(spec.next_tooltip)));
    row.pack_start(&prev, false, false, 0);
    row.pack_start(&stack_w, true, true, 0);
    row.pack_start(&next, false, false, 0);
    outer.pack_start(&row, false, false, 0);
    let counter = gtk::Label::new(None);
    counter.set_widget_name("linuxtoys-screenshot-counter");
    counter.set_halign(gtk::Align::Center);
    outer.pack_start(&counter, false, false, 0);
    true
}
