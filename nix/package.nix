{
  lib,
  stdenv,
  rustPlatform,
  python312,
  pkg-config,
  patchelf,
  autoPatchelfHook,
  wrapGAppsHook3,
  makeWrapper,
  shared-mime-info,
  gtk3,
  gdk-pixbuf,
  pango,
  vte,
  glib,
  librsvg,
  gobject-introspection,
  harfbuzz,
  at-spi2-core,
  appstream,
  flatpak,
  adwaita-icon-theme,
  hicolor-icon-theme,
  xapp-symbolic-icons,
  webp-pixbuf-loader,
  zenity,
  jq,
  git,
  curl,
  wget,
  bash,
  coreutils,
  findutils,
  gnugrep,
  gnused,
  gawk,
  procps,
  util-linux,
  xdg-utils,
}:

let
  version = lib.removeSuffix "\n" (builtins.readFile ../src/ver);

  # The TUI stack is vendored by the distro packagers, but a Nix build cannot
  # run the pip-based vendor_deps.sh in its sandbox. Nixpkgs carries the same
  # exact pins (textual 8.2.8 / pyte 0.8.2), so put them on the interpreter's
  # path instead; linuxtoys.py only prefers p3/vendor when that directory
  # exists.
  pythonEnv = python312.withPackages (
    ps: with ps; [
      pygobject3
      requests
      urllib3
      certifi
      textual
      pyte
    ]
  );

  runtimeDeps = [
    bash
    coreutils
    findutils
    gnugrep
    gnused
    gawk
    procps
    util-linux
    git
    curl
    wget
    jq
    zenity
    appstream
    xdg-utils
  ];

  typelibPackages = map lib.getLib [
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

  dataPackages = [
    gtk3
    adwaita-icon-theme
    hicolor-icon-theme
    xapp-symbolic-icons
    webp-pixbuf-loader
    shared-mime-info
  ];

  # Keep the build source to what the application and both Rust crates need.
  # p3/vendor is the local, gitignored pip vendoring directory and must never
  # shadow the interpreter's packages in a Nix build.
  src = lib.fileset.toSource {
    root = ../.;
    fileset = lib.fileset.unions [
      ../Cargo.toml
      ../Cargo.lock
      (lib.fileset.difference ../p3 (
        lib.fileset.unions [
          (lib.fileset.maybeMissing ../p3/vendor)
          (lib.fileset.maybeMissing ../p3/app/_catalog_rs.abi3.so)
          (lib.fileset.maybeMissing ../p3/app/liblinuxtoys_gui.so)
        ]
      ))
      (lib.fileset.difference ../src (lib.fileset.maybeMissing ../src/__pycache__))
    ];
  };
in
rustPlatform.buildRustPackage {
  pname = "linuxtoys";
  inherit version src;

  cargoLock.lockFile = ../Cargo.lock;

  nativeBuildInputs = [
    pkg-config
    patchelf
    autoPatchelfHook
    wrapGAppsHook3
    makeWrapper
    shared-mime-info
    python312
  ];

  buildInputs = [
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
    pythonEnv
  ];

  env.PYO3_PYTHON = "${python312.interpreter}";

  doCheck = false;

  installPhase = ''
    runHook preInstall

    mkdir -p "$out/share/linuxtoys" "$out/bin"
    cp -a p3/. "$out/share/linuxtoys/"
    rm -rf "$out/share/linuxtoys/vendor"
    find "$out/share/linuxtoys" -type d -name __pycache__ -prune -exec rm -rf {} +
    find "$out/share/linuxtoys" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

    catalog_extension="$(find target -type f -name 'lib_catalog_rs.so' -print -quit)"
    gui_library="$(find target -type f -name 'liblinuxtoys_gui.so' -print -quit)"
    [ -n "$catalog_extension" ] || {
      echo "catalog extension not found under target/" >&2
      exit 1
    }
    [ -n "$gui_library" ] || {
      echo "GUI library not found under target/" >&2
      exit 1
    }

    install -Dm755 "$catalog_extension" \
      "$out/share/linuxtoys/app/_catalog_rs.abi3.so"
    install -Dm755 "$gui_library" \
      "$out/share/linuxtoys/app/liblinuxtoys_gui.so"

    chmod +x "$out/share/linuxtoys/linuxtoys.py"
    find "$out/share/linuxtoys/scripts" -type f -name '*.sh' -exec chmod +x {} +

    install -Dm644 src/linuxtoys.svg \
      "$out/share/icons/hicolor/scalable/apps/linuxtoys.svg"
    install -Dm644 src/linuxtoys-mimetypes.xml \
      "$out/share/mime/packages/linuxtoys-mimetypes.xml"
    install -Dm644 src/toys.linux.LinuxToys.metainfo.xml \
      "$out/share/metainfo/toys.linux.LinuxToys.metainfo.xml"
    install -Dm644 src/toys.linux.LinuxToys.desktop \
      "$out/share/applications/toys.linux.LinuxToys.desktop"
    substituteInPlace "$out/share/applications/toys.linux.LinuxToys.desktop" \
      --replace-fail "Exec=/usr/bin/linuxtoys" "Exec=linuxtoys"

    # wrapGAppsHook3 only carries the last GDK loader cache it saw (librsvg's).
    # Build one combined cache so the app's WebP screenshots and SVG icons
    # load alongside the built-in formats.
    mkdir -p "$out/lib/gdk-pixbuf-2.0/2.10.0"
    ${lib.getDev gdk-pixbuf}/bin/gdk-pixbuf-query-loaders \
      ${gdk-pixbuf}/lib/gdk-pixbuf-2.0/2.10.0/loaders/*.so \
      ${librsvg}/lib/gdk-pixbuf-2.0/2.10.0/loaders/*.so \
      ${webp-pixbuf-loader}/lib/gdk-pixbuf-2.0/2.10.0/loaders/*.so \
      > "$out/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache"

    cat > "$out/bin/linuxtoys" <<EOF
    #!${stdenv.shell}
    set -e
    export LINUXTOYS_PROCESS_NAME="linuxtoys"
    export LINUXTOYS_LAUNCHER="''${LINUXTOYS_LAUNCHER:-\$0}"
    export PYTHONDONTWRITEBYTECODE=1
    export PATH="${lib.makeBinPath (runtimeDeps ++ [ pythonEnv ])}:\$PATH"
    export XDG_DATA_DIRS="${lib.makeSearchPath "share" dataPackages}''${XDG_DATA_DIRS:+:\$XDG_DATA_DIRS}"
    export GI_TYPELIB_PATH="${lib.makeSearchPath "lib/girepository-1.0" typelibPackages}''${GI_TYPELIB_PATH:+:\$GI_TYPELIB_PATH}"
    export LD_LIBRARY_PATH="${lib.makeLibraryPath typelibPackages}''${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
    export GDK_PIXBUF_MODULE_FILE="${placeholder "out"}/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache"
    if [ "\$#" -gt 0 ]; then
        case "\$1" in
            --gui|-g|--tui|-t|linuxtoys://*) ;;
            *) export EASY_CLI=1 ;;
        esac
    fi
    cd "${placeholder "out"}/share/linuxtoys"
    exec "${pythonEnv}/bin/python3" "${placeholder "out"}/share/linuxtoys/linuxtoys.py" "\$@"
    EOF
    chmod +x "$out/bin/linuxtoys"

    runHook postInstall
  '';

  postFixup = ''
    patchShebangs "$out/bin"
  '';

  meta = {
    description = "For everything Linux - tools, tweaks and software manager";
    homepage = "https://linux.toys";
    license = lib.licenses.gpl3Only;
    mainProgram = "linuxtoys";
    platforms = lib.platforms.linux;
    sourceProvenance = [ lib.sourceTypes.fromSource ];
  };
}
