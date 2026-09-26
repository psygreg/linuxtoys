"""Thin ctypes bridge to the native GTK3 LinuxToys GUI library."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

_LIB = None


class _ItemCardSpec(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char_p),
        ("icon_path", ctypes.c_char_p),
        ("icon_name", ctypes.c_char_p),
        ("badge_path", ctypes.c_char_p),
        ("bold", ctypes.c_uint8),
        ("removable", ctypes.c_uint8),
        ("checklist", ctypes.c_uint8),
        ("is_new", ctypes.c_uint8),
    ]


class _GridPosition(ctypes.Structure):
    _fields_ = [
        ("column", ctypes.c_int32),
        ("row", ctypes.c_int32),
    ]


class _InfosHeadSpec(ctypes.Structure):
    _fields_ = [
        ("execute_label", ctypes.c_char_p),
        ("remove_label", ctypes.c_char_p),
        ("report_label", ctypes.c_char_p),
        ("show_terminal_controls", ctypes.c_uint8),
    ]


class _AppPageHeaderSpec(ctypes.Structure):
    _fields_ = [
        ("aggregate_markup", ctypes.c_char_p),
        ("install_label", ctypes.c_char_p),
        ("open_label", ctypes.c_char_p),
    ]


class _ListRowSpec(ctypes.Structure):
    _fields_ = [
        ("key", ctypes.c_char_p),
        ("name", ctypes.c_char_p),
        ("secondary", ctypes.c_char_p),
        ("icon_path", ctypes.c_char_p),
        ("icon_name", ctypes.c_char_p),
        ("status_icon", ctypes.c_char_p),
        ("action_tooltip", ctypes.c_char_p),
        ("secondary_visible", ctypes.c_uint8),
        ("spinner", ctypes.c_uint8),
        ("launch", ctypes.c_uint8),
        ("destructive_action", ctypes.c_uint8),
        ("action_kind", ctypes.c_uint8),
    ]


def _pointer(obj):
    if obj is None:
        return None
    capsule = obj.__gpointer__
    get_ptr = ctypes.pythonapi.PyCapsule_GetPointer
    get_ptr.argtypes = [ctypes.py_object, ctypes.c_char_p]
    get_ptr.restype = ctypes.c_void_p
    return get_ptr(capsule, None)


def _candidate_paths():
    here = Path(__file__).resolve().parent
    env = os.environ.get("LINUXTOYS_GUI_RS_LIB")
    if env:
        yield Path(env)
    yield here / "liblinuxtoys_gui.so"
    yield here.parent / "lib" / "liblinuxtoys_gui.so"


def _load():
    global _LIB
    if _LIB is not None:
        return _LIB
    for path in _candidate_paths():
        if path.is_file():
            lib = ctypes.CDLL(str(path))
            lib.lt_gui_abi_version.restype = ctypes.c_uint32
            if lib.lt_gui_abi_version() != 7:
                raise RuntimeError("Unsupported LinuxToys GUI Rust ABI (expected ABI 7)")
            lib.lt_gui_flowbox_add_item_cards.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(_ItemCardSpec), ctypes.c_size_t,
            ]
            lib.lt_gui_flowbox_add_item_cards.restype = ctypes.c_size_t
            lib.lt_gui_grid_attach_item_cards.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(_ItemCardSpec),
                ctypes.POINTER(_GridPosition),
                ctypes.c_size_t,
            ]
            lib.lt_gui_grid_attach_item_cards.restype = ctypes.c_size_t
            lib.lt_gui_update_item_card.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(_ItemCardSpec),
            ]
            lib.lt_gui_update_item_card.restype = ctypes.c_bool
            lib.lt_gui_populate_infos_head.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(_InfosHeadSpec),
            ]
            lib.lt_gui_populate_infos_head.restype = ctypes.c_bool
            lib.lt_gui_populate_app_page_header.argtypes = [
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.POINTER(_AppPageHeaderSpec),
                ctypes.c_uint8,
                ctypes.c_uint8,
            ]
            lib.lt_gui_populate_app_page_header.restype = ctypes.c_bool
            lib.lt_gui_box_add_list_rows.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(_ListRowSpec), ctypes.c_size_t,
            ]
            lib.lt_gui_box_add_list_rows.restype = ctypes.c_size_t
            lib.lt_gui_reconcile_list_row.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(_ListRowSpec),
            ]
            lib.lt_gui_reconcile_list_row.restype = ctypes.c_bool
            _LIB = lib
            return lib
    return None


def available():
    return _load() is not None


def _event_box_from_flowbox_child(child):
    """Return the native EventBox contained by a Gtk.FlowBoxChild."""
    if child is None:
        return None
    get_child = getattr(child, "get_child", None)
    return get_child() if get_child is not None else None


def card_child(card, name):
    """Find a named descendant using normal PyGObject APIs."""
    if card is None:
        return None
    if card.get_name() == name:
        return card
    get_children = getattr(card, "get_children", None)
    if get_children is None:
        return None
    for child in get_children():
        found = card_child(child, name)
        if found is not None:
            return found
    return None



def _native_spec(spec):
    """Marshal one Python card descriptor while keeping its strings alive."""
    values = [
        str(spec.get("name", "")).encode(),
        str(spec.get("icon_path", "") or "").encode(),
        str(spec.get("icon_name", "") or "").encode(),
        str(spec.get("badge_path", "") or "").encode(),
    ]
    native = _ItemCardSpec(
        values[0], values[1], values[2], values[3],
        int(bool(spec.get("bold", False))),
        int(bool(spec.get("removable", False))),
        int(bool(spec.get("checklist", False))),
        int(bool(spec.get("is_new", False))),
    )
    return native, values


def add_item_cards(flowbox, specs):
    """Create ordinary cards and insert them into ``flowbox`` in one native call."""
    lib = _load()
    specs = list(specs)
    if lib is None or flowbox is None or not specs:
        return []

    # Keep encoded strings alive until the native call returns. ctypes structures
    # only retain their pointers, not independent copies of the C strings.
    encoded = []
    native_specs = []
    for spec in specs:
        native, values = _native_spec(spec)
        encoded.append(values)
        native_specs.append(native)

    array_type = _ItemCardSpec * len(native_specs)
    native_array = array_type(*native_specs)
    before = set(flowbox.get_children())
    created = lib.lt_gui_flowbox_add_item_cards(
        _pointer(flowbox), native_array, len(native_specs)
    )
    if created != len(native_specs):
        raise RuntimeError(
            f"Native GTK batch created {created}/{len(native_specs)} cards"
        )

    # Rust inserts EventBoxes into the FlowBox. GTK wraps each one in a
    # Gtk.FlowBoxChild; obtain those wrappers through PyGObject's public API.
    new_children = [child for child in flowbox.get_children() if child not in before]
    if len(new_children) != created:
        raise RuntimeError(
            f"Native GTK batch inserted {created} cards but Python found "
            f"{len(new_children)} new FlowBox children"
        )

    widgets = [_event_box_from_flowbox_child(child) for child in new_children]
    if any(widget is None for widget in widgets):
        raise RuntimeError("Native GTK batch produced an empty FlowBox child")
    return widgets


def attach_item_cards_grid(grid, specs, positions):
    """Create ordinary cards and attach them to explicit Gtk.Grid cells."""
    lib = _load()
    specs = list(specs)
    positions = [(int(column), int(row)) for column, row in positions]
    if lib is None or grid is None or not specs:
        return []
    if len(specs) != len(positions):
        raise ValueError("Grid card specs and positions must have the same length")

    encoded = []
    native_specs = []
    for spec in specs:
        native, values = _native_spec(spec)
        encoded.append(values)
        native_specs.append(native)

    spec_array_type = _ItemCardSpec * len(native_specs)
    native_array = spec_array_type(*native_specs)
    pos_array_type = _GridPosition * len(positions)
    native_positions = pos_array_type(
        *(_GridPosition(column, row) for column, row in positions)
    )

    before = set(grid.get_children())
    created = lib.lt_gui_grid_attach_item_cards(
        _pointer(grid), native_array, native_positions, len(native_specs)
    )
    if created != len(native_specs):
        raise RuntimeError(
            f"Native GTK grid batch created {created}/{len(native_specs)} cards"
        )

    new_children = [child for child in grid.get_children() if child not in before]
    if len(new_children) != created:
        raise RuntimeError(
            f"Native GTK grid batch inserted {created} cards but Python found "
            f"{len(new_children)} new Grid children"
        )

    by_position = {}
    for child in new_children:
        column = int(grid.child_get_property(child, "left-attach"))
        row = int(grid.child_get_property(child, "top-attach"))
        by_position[(column, row)] = child

    try:
        return [by_position[position] for position in positions]
    except KeyError as error:
        raise RuntimeError(
            f"Native GTK grid batch could not recover card at {error.args[0]}"
        ) from error


def update_item_card(card, spec):
    """Rebind an existing native ordinary card without changing its hierarchy."""
    lib = _load()
    if lib is None or card is None:
        return False
    native, encoded = _native_spec(spec)
    return bool(lib.lt_gui_update_item_card(_pointer(card), ctypes.byref(native)))


def populate_infos_head(root, *, execute_label, remove_label, report_label,
                        show_terminal_controls=True):
    """Populate a Python-owned InfosHead root and recover its named children."""
    lib = _load()
    if lib is None or root is None:
        return None

    encoded = [
        str(execute_label).encode(),
        str(remove_label).encode(),
        str(report_label).encode(),
    ]
    spec = _InfosHeadSpec(
        encoded[0], encoded[1], encoded[2],
        int(bool(show_terminal_controls)),
    )
    if not lib.lt_gui_populate_infos_head(_pointer(root), ctypes.byref(spec)):
        return None

    names = {
        "vbox_infos": "linuxtoys-infos-vbox",
        "label_name": "linuxtoys-infos-name",
        "label_desc": "linuxtoys-infos-description",
        "label_repo": "linuxtoys-infos-repository",
        "hbox_header": "linuxtoys-infos-header",
        "icon_head": "linuxtoys-infos-icon",
        "hbox_controls": "linuxtoys-infos-controls",
        "button_run": "linuxtoys-infos-run",
        "button_remove": "linuxtoys-infos-remove",
        "button_copy": "linuxtoys-infos-report",
        "progress_bar": "linuxtoys-infos-progress",
    }
    widgets = {key: card_child(root, name) for key, name in names.items()}
    if any(widget is None for widget in widgets.values()):
        return None
    return widgets


def populate_app_page_header(overlay, infos_box, repo_label, *,
                             aggregate_markup="", install_label=" Install ",
                             open_label=" Open ", show_aggregate=False,
                             show_rating=False):
    """Build the structural app-page header additions in native GTK."""
    lib = _load()
    if lib is None or overlay is None or infos_box is None or repo_label is None:
        return None

    encoded = [
        str(aggregate_markup).encode(),
        str(install_label).encode(),
        str(open_label).encode(),
    ]
    spec = _AppPageHeaderSpec(*encoded)
    ok = lib.lt_gui_populate_app_page_header(
        _pointer(overlay),
        _pointer(infos_box),
        _pointer(repo_label),
        ctypes.byref(spec),
        int(bool(show_aggregate)),
        int(bool(show_rating)),
    )
    if not ok:
        return None

    names = {
        "aggregate": "linuxtoys-app-aggregate-rating",
        "repository_rating_row": "linuxtoys-app-repository-rating-row",
        "rating_box": "linuxtoys-app-rating-control",
        "controls": "linuxtoys-app-actions",
        "install_button": "linuxtoys-app-install",
        "open_button": "linuxtoys-app-open",
    }
    widgets = {key: card_child(overlay, name) for key, name in names.items()}
    if widgets["controls"] is None or widgets["install_button"] is None or widgets["open_button"] is None:
        return None
    if show_aggregate and widgets["aggregate"] is None:
        return None
    if show_rating:
        if widgets["repository_rating_row"] is None or widgets["rating_box"] is None:
            return None
        rating_buttons = [
            card_child(widgets["rating_box"], f"linuxtoys-app-rating-{stars}")
            for stars in range(1, 6)
        ]
        if any(button is None for button in rating_buttons):
            return None
    else:
        rating_buttons = []

    widgets["rating_buttons"] = rating_buttons
    return widgets


def _native_list_row_spec(spec):
    values = [
        str(spec.get("key", "")).encode(),
        str(spec.get("name", "")).encode(),
        str(spec.get("secondary", "") or "").encode(),
        str(spec.get("icon_path", "") or "").encode(),
        str(spec.get("icon_name", "") or "").encode(),
        str(spec.get("status_icon", "") or "").encode(),
        str(spec.get("action_tooltip", "") or "").encode(),
    ]
    native = _ListRowSpec(
        *values,
        int(bool(spec.get("secondary_visible", False))),
        int(bool(spec.get("spinner", False))),
        int(bool(spec.get("launch", False))),
        int(bool(spec.get("destructive_action", False))),
        int(spec.get("action_kind", 0)),
    )
    return native, values


def add_list_rows(container, specs):
    """Batch-create queue/library rows in a Python-owned Gtk.Box."""
    lib = _load()
    specs = list(specs)
    if lib is None or container is None or not specs:
        return []

    encoded = []
    native_specs = []
    for spec in specs:
        native, values = _native_list_row_spec(spec)
        encoded.append(values)
        native_specs.append(native)

    array_type = _ListRowSpec * len(native_specs)
    native_array = array_type(*native_specs)
    before = set(container.get_children())
    created = lib.lt_gui_box_add_list_rows(
        _pointer(container), native_array, len(native_specs)
    )
    if created != len(native_specs):
        raise RuntimeError(
            f"Native GTK list batch created {created}/{len(native_specs)} rows"
        )
    rows = [child for child in container.get_children() if child not in before]
    if len(rows) != created:
        raise RuntimeError(
            f"Native GTK list batch inserted {created} rows but Python found {len(rows)}"
        )
    return rows


def reconcile_list_row(row, spec):
    """Update the mutable parts of an existing native list row in place."""
    lib = _load()
    if lib is None or row is None:
        return False
    native, encoded = _native_list_row_spec(spec)
    return bool(lib.lt_gui_reconcile_list_row(_pointer(row), ctypes.byref(native)))
