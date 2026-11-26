{
  pkgs ? import <nixpkgs> { },
}:

let
  inherit (pkgs) lib;

  pythonEnv = pkgs.python312.withPackages (
    ps: with ps; [
      # Application runtime
      pygobject3
      requests
      urllib3
      certifi
      # TUI stack (same pins as p3/requirements.txt, normally pip-vendored)
      textual
      pyte
      # build-rust.sh develop runs dev/build/vendor_deps.sh, which needs pip
      pip
    ]
  );

  # GTK/WebKit-adjacent runtime libraries used by the Python GUI and the
  # gui-rs cdylib.
  guiLibs = with pkgs; [
    gtk3
    gdk-pixbuf
    pango
    vte
    glib
    librsvg
    gobject-introspection
    harfbuzz
    at-spi2-core
    appstream
    flatpak
  ];

  # `makeSearchPath` on `pango`/`glib` would select their `bin` output; the
  # typelibs live in the library output.
  typelibPackages = map lib.getLib guiLibs;

  # Typelib and icon/database packages the app looks up at runtime.
  dataPackages = with pkgs; [
    adwaita-icon-theme
    hicolor-icon-theme
    xapp-symbolic-icons
    webp-pixbuf-loader
    shared-mime-info
  ];

  # Tools the Rust build needs (maturin, cargo, pkg-config) plus the commands
  # the application and its Bash libraries call at runtime.
  devTools = with pkgs; [
    rustc
    cargo
    maturin
    pkg-config
    patchelf
    git
    curl
    wget
    jq
    zenity
    xdg-utils
    procps
    util-linux
    bash
    coreutils
    findutils
    gnugrep
    gnused
    gawk
  ];
in
pkgs.mkShell {
  name = "linuxtoys-dev";

  buildInputs = [ pythonEnv ] ++ guiLibs ++ dataPackages;
  packages = devTools;

  shellHook = ''
    export GI_TYPELIB_PATH="${lib.makeSearchPath "lib/girepository-1.0" typelibPackages}''${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"
    export LD_LIBRARY_PATH="${lib.makeLibraryPath guiLibs}''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    export XDG_DATA_DIRS="${lib.makeSearchPath "share" dataPackages}''${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}"

    # The package wraps executables through wrapGAppsHook3, which builds a
    # combined gdk-pixbuf loader cache. In a plain shell there is no wrapper,
    # so build one from the same loader directories (GdkPixbuf needs it for
    # the WebP screenshots and SVG icons the app uses).
    if command -v gdk-pixbuf-query-loaders >/dev/null 2>&1; then
      _lt_pixbuf_dir="$(mktemp -d "''${TMPDIR:-/tmp}/linuxtoys-pixbuf.XXXXXX")"
      find "${pkgs.gdk-pixbuf}/lib/gdk-pixbuf-2.0" \
           "${pkgs.librsvg}/lib/gdk-pixbuf-2.0" \
           "${pkgs.webp-pixbuf-loader}/lib/gdk-pixbuf-2.0" \
           -name '*.so' -print0 2>/dev/null \
        | xargs -0 -r gdk-pixbuf-query-loaders > "$_lt_pixbuf_dir/loaders.cache" 2>/dev/null || true
      if [ -s "$_lt_pixbuf_dir/loaders.cache" ]; then
        export GDK_PIXBUF_MODULE_FILE="$_lt_pixbuf_dir/loaders.cache"
      fi
    fi

    echo "✓ LinuxToys development environment loaded"
    echo "  First run: ./build-rust.sh develop"
    echo "  Then:      python3 p3/linuxtoys.py"
  '';
}
