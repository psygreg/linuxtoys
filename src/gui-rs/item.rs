use gtk::prelude::*;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::path::Path;

fn widget_ptr<W: IsA<gtk::Widget>>(widget: &W) -> usize {
    widget.as_ref().as_ptr() as usize
}

fn load_image(value: &str, size: i32) -> gtk::Image {
    if (value.ends_with(".png") || value.ends_with(".svg")) && Path::new(value).is_file() {
        if let Ok(pixbuf) = gdk_pixbuf::Pixbuf::from_file_at_scale(value, size, size, true) {
            return gtk::Image::from_pixbuf(Some(&pixbuf));
        }
    }
    let image = gtk::Image::from_icon_name(Some(value), gtk::IconSize::Dialog);
    image.set_pixel_size(size);
    image
}

#[pyfunction]
#[pyo3(signature = (name, icon, badge=None, bold=false, checklist=false, removable=false, is_new=false))]
fn create_item_widget(
    py: Python<'_>,
    name: &str,
    icon: &str,
    badge: Option<&str>,
    bold: bool,
    checklist: bool,
    removable: bool,
    is_new: bool,
) -> PyResult<PyObject> {
    // GTK is initialized by the Python application before cards are requested.
    let row = gtk::Box::new(gtk::Orientation::Horizontal, 12);
    row.set_size_request(128, 52);
    row.set_hexpand(false);
    row.set_halign(gtk::Align::Fill);

    let remove_button = if removable {
        row.style_context().add_class("installed-card");
        let button = gtk::Button::from_icon_name(Some("edit-delete-symbolic"), gtk::IconSize::Menu);
        button.style_context().add_class("installed-card-remove-left");
        button.style_context().add_class("destructive-action");
        button.set_size_request(24, 24);
        button.set_relief(gtk::ReliefStyle::None);
        button.set_can_focus(true);
        row.pack_start(&button, false, false, 0);
        Some(button)
    } else { None };

    let check = if checklist {
        let button = gtk::CheckButton::new();
        button.set_can_focus(false);
        if !removable { button.set_margin_start(22); }
        row.pack_start(&button, false, false, 0);
        Some(button)
    } else { None };

    let label = gtk::Label::new(Some(name));
    if !removable && !checklist { label.set_margin_start(22); }
    label.set_line_wrap(true);
    label.set_justify(gtk::Justification::Center);
    label.set_halign(gtk::Align::Center);
    label.set_valign(gtk::Align::Center);
    label.set_max_width_chars(28);
    label.set_width_chars(4);
    label.set_hexpand(false);
    if bold {
        let escaped = glib::markup_escape_text(name);
        label.set_markup(&format!("<b>{}</b>", escaped));
    }
    row.pack_start(&label, true, true, 0);

    let image = load_image(icon, 38);
    image.set_halign(gtk::Align::End);
    image.set_valign(gtk::Align::Center);
    row.pack_start(&image, false, false, 20);

    let surface = gtk::Box::new(gtk::Orientation::Horizontal, 0);
    surface.pack_start(&row, true, true, 0);
    surface.style_context().add_class("script-item");
    if is_new { surface.style_context().add_class("script-item-new"); }
    surface.set_margin_top(4);
    surface.set_margin_start(4);
    surface.set_margin_end(4);

    let overlay = gtk::Overlay::new();
    overlay.add(&surface);

    let badge_image = badge.filter(|p| !p.is_empty()).map(|path| {
        let image = load_image(path, 20);
        image.set_halign(gtk::Align::End);
        image.set_valign(gtk::Align::Start);
        overlay.add_overlay(&image);
        image
    });

    let event_box = gtk::EventBox::new();
    event_box.add(&overlay);
    event_box.set_events(
        gdk::EventMask::ENTER_NOTIFY_MASK
            | gdk::EventMask::LEAVE_NOTIFY_MASK
            | gdk::EventMask::BUTTON_PRESS_MASK
            | gdk::EventMask::BUTTON_RELEASE_MASK,
    );

    // Keep the hierarchy alive after returning raw pointers. The Python bridge
    // immediately creates PyGObject wrappers, which then own normal GObject refs.
    event_box.show_all();

    let out = PyDict::new(py);
    out.set_item("event_box", widget_ptr(&event_box))?;
    out.set_item("surface", widget_ptr(&surface))?;
    out.set_item("overlay", widget_ptr(&overlay))?;
    out.set_item("label", widget_ptr(&label))?;
    out.set_item("image", widget_ptr(&image))?;
    out.set_item("badge", badge_image.as_ref().map(widget_ptr).unwrap_or(0))?;
    out.set_item("check", check.as_ref().map(widget_ptr).unwrap_or(0))?;
    out.set_item("remove", remove_button.as_ref().map(widget_ptr).unwrap_or(0))?;

    // Transfer one reference on the root to the Python side. Child widgets are
    // retained by GTK ownership and wrapped while the root is alive.
    unsafe { glib::gobject_ffi::g_object_ref(event_box.as_ptr() as *mut _) };
    Ok(out.into())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(create_item_widget, module)?)?;
    Ok(())
}
