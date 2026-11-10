"""Explicit native application probes; run inside a disposable Linux user profile.

Usage: PYTHONPATH=p3:p3/vendor python3 dev/tests/native_application_smoke.py imports|widgets|gui|launcher|tui|mcp --profile NEW_DIRECTORY
Set GDK_BACKEND explicitly for display tests. No install/update action is invoked.
"""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import faulthandler
import gc
import importlib
import json
import os
import signal
import socket
import subprocess
import urllib.request
import urllib.error
from unittest.mock import patch
from pathlib import Path
import resource
import runpy
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "p3"), str(ROOT / "p3/vendor")]
os.environ.setdefault("SCRIPT_DIR", str(ROOT / "p3"))
os.environ.setdefault("CACHE_DIR", str(ROOT / "p3/scripts"))


def imports() -> None:
    import gi
    from app import _catalog_rs, architecture, gui_rs

    for name, version in (
        ("Gtk", "3.0"),
        ("Gdk", "3.0"),
        ("GLib", "2.0"),
        ("GObject", "2.0"),
        ("Gio", "2.0"),
        ("Pango", "1.0"),
        ("GdkPixbuf", "2.0"),
        ("Vte", "2.91"),
        ("AppStream", "1.0"),
    ):
        gi.require_version(name, version)
        importlib.import_module("gi.repository." + name)
    gi.require_foreign("cairo")
    import cairo

    assert ctypes.sizeof(ctypes.c_void_p) == 8
    lib = gui_rs._load()
    assert lib is not None and lib.lt_gui_abi_version() == 20
    for file in (Path(_catalog_rs.__file__), Path(lib._name)):
        from app.architecture_files import validate_file

        validate_file(file)
    print(
        json.dumps(
            {
                "probe": "imports",
                "host": architecture.host().value,
                "python": sys.version.split()[0],
                "catalog": _catalog_rs.__file__,
                "gui": lib._name,
                "pointer_bytes": ctypes.sizeof(ctypes.c_void_p),
                "cairo": cairo.cairo_version_string(),
                "abi": lib.lt_gui_abi_version(),
            }
        )
    )


def display():
    from app.gtk_common import Gtk, Gdk, GLib

    assert Gtk.init_check()[0], "Requested display backend is unavailable"
    actual = Gdk.Display.get_default().__class__.__name__
    expected = os.environ.get("GDK_BACKEND")
    assert expected in ("wayland", "x11"), "Set GDK_BACKEND explicitly"
    assert expected in actual.lower(), (expected, actual)
    return Gtk, GLib, actual


def widgets() -> None:
    from app import gui_rs
    from app.gtk_common import Vte

    Gtk, GLib, actual = display()
    window = Gtk.Window()
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    window.add(box)
    flow = Gtk.FlowBox()
    box.add(flow)
    sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.add(sidebar)
    resident = []
    for index in range(100):
        cards = gui_rs.add_item_cards(
            flow, [{"name": "ARM64 qualification", "icon_name": "folder", "bold": True}]
        )
        assert len(cards) == 1
        for card in list(flow.get_children()):
            card.destroy()
        rows = gui_rs.build_sidebar(
            sidebar,
            [{"key": "test", "label": "Test", "icon_name": "folder", "depth": 0}],
        )
        assert "test" in rows
        for row in list(sidebar.get_children()):
            row.destroy()
        if index in (9, 99):
            gc.collect()
            resident.append(
                int(Path("/proc/self/statm").read_text().split()[1])
                * os.sysconf("SC_PAGE_SIZE")
            )
    assert resident[1] - resident[0] < 16 * 1024**2, resident
    buffer = Gtk.TextBuffer()
    assert gui_rs.populate_markdown_buffer(
        buffer, "# Native qualification\nGTK / Rust / Python"
    )
    terminal = Vte.Terminal()
    box.add(terminal)
    window.show_all()
    loop = GLib.MainLoop()
    statuses = []

    def exited(_terminal, status):
        statuses.append(status)
        GLib.timeout_add(100, lambda: loop.quit() or False)

    terminal.connect("child-exited", exited)
    terminal.spawn_async(
        Vte.PtyFlags.DEFAULT,
        None,
        ["/bin/sh", "-c", "printf 'linuxtoys-native-terminal\\n'"],
        None,
        GLib.SpawnFlags.DEFAULT,
        None,
        None,
        -1,
        None,
        None,
    )
    deadline = GLib.timeout_add_seconds(8, lambda: loop.quit() or False)
    loop.run()
    GLib.source_remove(deadline)
    from app.term_reporting import BugReporting
    from types import SimpleNamespace

    text = BugReporting._get_vte_buffer_text(SimpleNamespace(terminal=terminal))
    assert statuses == [0] and "linuxtoys-native-terminal" in text, (statuses, text)

    while GLib.MainContext.default().iteration(False):
        pass
    window.destroy()
    while GLib.MainContext.default().iteration(False):
        pass
    gc.collect()
    print(
        json.dumps(
            {
                "probe": "widgets",
                "display": actual,
                "cycles": 100,
                "vte_shell_exit": statuses[0],
                "vte_output_verified": True,
                "resident_bytes_after_10_and_100": resident,
                "rss_max_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            }
        )
    )


def gui() -> None:
    Gtk, GLib, actual = display()
    from app.lang_utils import save_automatic_updates

    save_automatic_updates(False)
    faulthandler.dump_traceback_later(20, repeat=True)
    from app import main
    from gi.repository import Gio

    app = main.Application(main.translations, flags=Gio.ApplicationFlags.NON_UNIQUE)
    started = time.monotonic()
    seen = []

    def decline_setup():
        for window in Gtk.Window.list_toplevels():
            if isinstance(window, Gtk.Dialog) and window.get_visible():
                window.response(Gtk.ResponseType.CANCEL)
        return not seen

    GLib.timeout_add(500, decline_setup)

    def finish():
        if app.window is not None:
            seen.append(app.window.__class__.__name__)
        app.window.close()
        return False

    def search():
        if app.window is not None:
            app.window.search_entry.set_text("Atkinson")
        return False

    GLib.timeout_add_seconds(5, search)
    GLib.timeout_add_seconds(12, finish)
    result = app.run([])
    faulthandler.cancel_dump_traceback_later()
    assert result == 0 and seen, (result, seen)
    assert app.window.search_entry.get_text() == "Atkinson"
    print(
        json.dumps(
            {
                "probe": "gui",
                "display": actual,
                "window": seen[0],
                "search_groups": len(app.window.search_results),
                "elapsed_seconds": round(time.monotonic() - started, 2),
            }
        )
    )


def launcher() -> None:
    Gtk, GLib, actual = display()
    from gi.repository import Gio

    seen = []

    def decline_setup():
        for window in Gtk.Window.list_toplevels():
            if isinstance(window, Gtk.Dialog) and window.get_visible():
                window.response(Gtk.ResponseType.CANCEL)
        return not seen

    def finish():
        app = Gio.Application.get_default()
        assert app is not None and app.window is not None
        seen.append(app.window.__class__.__name__)
        app.window.close()
        return False

    GLib.timeout_add(500, decline_setup)
    GLib.timeout_add_seconds(12, finish)
    sys.argv = [str(ROOT / "p3/linuxtoys.py"), "--gui"]
    try:
        runpy.run_path(sys.argv[0], run_name="__main__")
    except SystemExit as result:
        assert result.code in (None, 0), result.code
    assert seen == ["AppWindow"], seen
    print(
        json.dumps(
            {"probe": "launcher", "display": actual, "window": seen[0], "exit": 0}
        )
    )


async def tui_probe() -> None:
    from app.tui.main import LinuxToys, HomeScreen
    from app.tui.runner_helper import ScriptRunnerMixin

    with patch(
        "app.tui.runner_helper.search_appimage_items",
        side_effect=OSError("optional backend unavailable"),
    ):
        with patch("app.tui.runner_helper.logger.exception") as logged:
            await ScriptRunnerMixin._appimage_search_async(object(), "probe")
            logged.assert_called_once()
    from textual.widgets import Input

    app = LinuxToys()
    async with app.run_test(size=(110, 35)) as pilot:
        for _ in range(60):
            if app.screen.__class__.__name__ == "StartupRecommendationsDialog":
                await pilot.press("escape")
            if isinstance(app.screen, HomeScreen):
                break
            await pilot.pause(0.1)
        assert isinstance(app.screen, HomeScreen), type(app.screen)
        search = app.screen.query_one("#search-input", Input)
        for widget in list(app.screen.query("Button")):
            if str(getattr(widget, "id", "")) == "skip":
                await pilot.click(widget)
        search.value = "Atkinson"
        await pilot.pause(1)
        app.exit()
    print(json.dumps({"probe": "tui", "screen": "HomeScreen", "search": "Atkinson"}))


def mcp() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    env = dict(os.environ, LINUXTOYS_MCP_PORT=str(port), PYTHONUNBUFFERED="1")
    server = subprocess.Popen(
        [sys.executable, str(ROOT / "p3/linuxtoys.py"), "--mcp"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    endpoint = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError("MCP startup failed")
            try:
                with urllib.request.urlopen(
                    endpoint + "/health", timeout=1
                ) as response:
                    assert json.load(response)["status"] == "ok"
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("MCP startup timeout")
        token = (Path.home() / ".config/linuxtoys/mcp-token").read_text().strip()

        def rpc(body, session="", authorized=True):
            headers = {"Content-Type": "application/json"}
            if authorized:
                headers["Authorization"] = "Bearer " + token
            if session:
                headers["Mcp-Session-Id"] = session
            request = urllib.request.Request(
                endpoint + "/mcp", data=json.dumps(body).encode(), headers=headers
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response), response.headers.get("Mcp-Session-Id")

        initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        try:
            rpc(initialize, authorized=False)
            raise AssertionError("MCP accepted an unauthenticated request")
        except urllib.error.HTTPError as error:
            assert error.code == 401
        result, session = rpc(initialize)
        assert session and result["result"]["serverInfo"]["name"]
        tools, _ = rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, session)
        assert tools["result"]["tools"]
        search, _ = rpc(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "search_apps", "arguments": {"query": "Atkinson"}},
            },
            session,
        )
        assert not search["result"].get("isError"), search
        assert "Atkinson" in json.dumps(search), search
        print(
            json.dumps(
                {
                    "probe": "mcp",
                    "authenticated": True,
                    "unauthenticated_refused": True,
                    "tool_count": len(tools["result"]["tools"]),
                    "search": "Atkinson",
                }
            )
        )
    finally:
        if server.poll() is None:
            server.send_signal(signal.SIGINT)
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
                raise
        assert server.returncode == 0, server.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=["imports", "widgets", "gui", "launcher", "tui", "mcp"]
    )
    parser.add_argument(
        "--profile",
        type=Path,
        required=True,
        help="New disposable user profile; must not exist",
    )
    args = parser.parse_args()
    profile = args.profile.resolve()
    profile.mkdir(parents=True, exist_ok=False)
    os.environ.update(
        HOME=str(profile),
        XDG_CONFIG_HOME=str(profile / ".config"),
        XDG_CACHE_HOME=str(profile / ".cache"),
        XDG_DATA_HOME=str(profile / ".local/share"),
    )
    from app.lang_utils import save_automatic_updates

    save_automatic_updates(False)
    mode = args.mode
    if mode == "imports":
        imports()
    elif mode == "widgets":
        widgets()
    elif mode == "gui":
        gui()
    elif mode == "launcher":
        launcher()
    elif mode == "tui":
        asyncio.run(tui_probe())
    elif mode == "mcp":
        mcp()
    else:
        raise SystemExit("Choose imports, widgets, gui, tui or mcp")
