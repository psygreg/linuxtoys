{ pkgs ? import <nixpkgs> {} }:

let
  # Create a Python environment with all dependencies properly included
  pythonEnv = pkgs.python312.withPackages (ps: with ps; [
    # Core dependencies (from requirements.txt)
    pygobject3
    requests
    urllib3
    certifi
  ]);
in

pkgs.mkShell rec {
  name = "linuxtoys-dev";
  
  buildInputs = with pkgs; [
    # Python environment (pre-configured with packages)
    pythonEnv
    
    # GObject Introspection
    gobject-introspection
    
    # GTK and GUI libraries
    gtk3
    libhandy
    adwaita-icon-theme
    
    # VTE (Virtual Terminal Emulator) - needed for terminal features
    vte
    
    # Pango (must come before GTK dependencies)
    pango
    
    # Additional GObject Introspection typelibs
    gdk-pixbuf
    librsvg
    
    # Development utilities
    git
    curl
    wget
    zenity
    
    # Additional system libraries
    glib
    libxml2
  ];

  # Set environment variables for proper GTK/GObject introspection
  shellHook = ''
    export GI_TYPELIB_PATH="$GI_TYPELIB_PATH"
    export GI_TYPELIB_PATH="${pkgs.gtk3}/lib/girepository-1.0:$GI_TYPELIB_PATH"
    export GI_TYPELIB_PATH="${pkgs.vte}/lib/girepository-1.0:$GI_TYPELIB_PATH"
    export GI_TYPELIB_PATH="${pkgs.pango}/lib/girepository-1.0:$GI_TYPELIB_PATH"
    export GI_TYPELIB_PATH="${pkgs.gdk-pixbuf}/lib/girepository-1.0:$GI_TYPELIB_PATH"
    export GI_TYPELIB_PATH="${pkgs.libhandy}/lib/girepository-1.0:$GI_TYPELIB_PATH"
    export GI_TYPELIB_PATH="${pkgs.librsvg}/lib/girepository-1.0:$GI_TYPELIB_PATH"
    export GI_TYPELIB_PATH="${pkgs.glib}/lib/girepository-1.0:$GI_TYPELIB_PATH"
    
    export LD_LIBRARY_PATH="${pkgs.gtk3}/lib:${pkgs.pango}/lib:${pkgs.gdk-pixbuf}/lib:${pkgs.vte}/lib:${pkgs.glib}/lib:${pkgs.libhandy}/lib:${pkgs.librsvg}/lib:${pkgs.libxml2}/lib:$LD_LIBRARY_PATH"
    
    echo "✓ LinuxToys development environment loaded"
    echo "  Run 'python3 p3/run.py' to start the application"
  '';
}
