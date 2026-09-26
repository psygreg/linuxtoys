use gdk::prelude::*;
use gdk_pixbuf::Pixbuf;
use glib::translate::from_glib_none;
use gtk::prelude::*;
use std::cell::RefCell;
use std::collections::HashMap;
use std::ffi::{c_char, CStr};
use std::fs;
use std::path::Path;

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

fn image(icon_path: &str, icon_name: &str, size: i32) -> gtk::Image {
    if !icon_path.is_empty() && Path::new(icon_path).exists() {
        if let Some(pixbuf) = load_scaled(icon_path, size, size) {
            return gtk::Image::from_pixbuf(Some(&pixbuf));
        }
    }
    let name = if icon_name.is_empty() { "application-x-executable" } else { icon_name };
    let img = gtk::Image::from_icon_name(Some(name), gtk::IconSize::Dialog);
    img.set_pixel_size(size);
    img
}

fn ensure_gtk_initialized() {
    if !gtk::is_initialized() {
        unsafe {
            gtk::set_initialized();
        }
    }
}

#[no_mangle]
pub extern "C" fn lt_gui_abi_version() -> u32 { 7 }

#[no_mangle]
pub extern "C" fn lt_gui_clear_pixbuf_cache() {
    PIXBUF_CACHE.with(|cache| cache.borrow_mut().clear());
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

    let row = gtk::Box::new(gtk::Orientation::Horizontal, 12);
    row.set_size_request(128, 52);
    row.set_hexpand(false);
    row.set_halign(gtk::Align::Fill);

    if removable {
        row.style_context().add_class("installed-card");
        let button = gtk::Button::from_icon_name(Some("edit-delete-symbolic"), gtk::IconSize::Menu);
        button.style_context().add_class("installed-card-remove-left");
        button.style_context().add_class("destructive-action");
        button.set_size_request(24, 24);
        button.set_relief(gtk::ReliefStyle::None);
        button.set_can_focus(true);
        button.set_widget_name("linuxtoys-native-remove");
        row.pack_start(&button, false, false, 0);
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
    if !removable && !checklist { label.set_margin_start(22); }
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
    row.pack_start(&label, true, true, 0);

    let icon = image(&icon_path, &icon_name, 38);
    icon.set_widget_name("linuxtoys-native-icon");
    icon.set_halign(gtk::Align::End);
    icon.set_valign(gtk::Align::Center);
    row.pack_start(&icon, false, false, 20);

    let surface = gtk::Box::new(gtk::Orientation::Horizontal, 0);
    surface.pack_start(&row, true, true, 0);
    surface.set_widget_name("linuxtoys-native-surface");
    surface.style_context().add_class("script-item");
    if is_new { surface.style_context().add_class("script-item-new"); }
    surface.set_margin_top(4);
    surface.set_margin_start(4);
    surface.set_margin_end(4);

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

    if !icon_path.is_empty() && Path::new(&icon_path).exists() {
        if let Some(pixbuf) = load_scaled(&icon_path, 38, 38) {
            icon.set_from_pixbuf(Some(&pixbuf));
        } else {
            let fallback = if icon_name.is_empty() {
                "application-x-executable"
            } else {
                icon_name.as_str()
            };
            icon.set_from_icon_name(Some(fallback), gtk::IconSize::Dialog);
            icon.set_pixel_size(38);
        }
    } else {
        let themed = if icon_name.is_empty() {
            "application-x-executable"
        } else {
            icon_name.as_str()
        };
        icon.set_from_icon_name(Some(themed), gtk::IconSize::Dialog);
        icon.set_pixel_size(38);
    }

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
    text.pack_start(&name, false, false, 0);

    let secondary = gtk::Label::new(Some(&secondary_text));
    secondary.set_widget_name("linuxtoys-list-row-secondary");
    secondary.set_halign(gtk::Align::Start);
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
        indicator.start();
        outer.pack_start(&indicator, false, false, 4);
    } else if !status_icon.is_empty() {
        let indicator = gtk::Image::from_icon_name(Some(&status_icon), gtk::IconSize::Button);
        indicator.set_widget_name("linuxtoys-list-row-status");
        outer.pack_start(&indicator, false, false, 4);
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

    if spec.secondary_visible != 0 {
        secondary.set_no_show_all(false);
        secondary.show();
    } else {
        secondary.set_no_show_all(true);
        secondary.hide();
    }

    // Status indicator changes between GtkSpinner and GtkImage, so replace only
    // that small child when its role changes rather than rebuilding the row.
    if let Some(old) = named_descendant(&root, "linuxtoys-list-row-status") {
        row.remove(&old);
    }
    if spec.spinner != 0 {
        let indicator = gtk::Spinner::new();
        indicator.set_widget_name("linuxtoys-list-row-status");
        indicator.start();
        row.pack_start(&indicator, false, false, 4);
        row.reorder_child(&indicator, 2);
        indicator.show();
    } else {
        let status_icon = cstr(spec.status_icon);
        if !status_icon.is_empty() {
            let indicator = gtk::Image::from_icon_name(Some(&status_icon), gtk::IconSize::Button);
            indicator.set_widget_name("linuxtoys-list-row-status");
            row.pack_start(&indicator, false, false, 4);
            row.reorder_child(&indicator, 2);
            indicator.show();
        }
    }

    // Queue action role may appear/disappear or switch Cancel -> Remove.
    if let Some(old) = named_descendant(&root, "linuxtoys-list-row-action") {
        row.remove(&old);
    }
    if spec.action_kind != 0 {
        let action_icon = if spec.destructive_action != 0 {
            "edit-delete-symbolic"
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

#[no_mangle]
pub unsafe extern "C" fn lt_gui_reconcile_list_row(
    row: *mut gtk::ffi::GtkWidget,
    spec: *const LtGuiListRowSpec,
) -> bool {
    ensure_gtk_initialized();
    if row.is_null() || spec.is_null() {
        return false;
    }
    let widget: gtk::Widget = from_glib_none(row);
    let row = match widget.downcast::<gtk::Box>() {
        Ok(value) => value,
        Err(_) => return false,
    };
    update_list_row_from_spec(&row, &*spec)
}

#[no_mangle]
pub unsafe extern "C" fn lt_gui_box_add_list_rows(
    container: *mut gtk::ffi::GtkWidget,
    specs: *const LtGuiListRowSpec,
    count: usize,
) -> usize {
    ensure_gtk_initialized();
    if container.is_null() || specs.is_null() {
        return 0;
    }
    let widget: gtk::Widget = from_glib_none(container);
    let container = match widget.downcast::<gtk::Box>() {
        Ok(value) => value,
        Err(_) => return 0,
    };
    let specs = std::slice::from_raw_parts(specs, count);

    let mut rows = Vec::with_capacity(count);
    for spec in specs {
        rows.push(create_list_row_from_spec(spec));
    }
    for row in rows {
        container.pack_start(&row, false, false, 0);
    }
    count
}
