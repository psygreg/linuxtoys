{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "linuxtoys-dev";
  
  buildInputs = with pkgs; [
    # Python and runtime
    python3
    python311Packages.pip
    python311Packages.venv
    
    # Core dependencies (from requirements.txt)
    python311Packages.pygobject3
    python311Packages.requests
    python311Packages.urllib3
    python311Packages.certifi
    
    # GTK and GUI libraries
    gtk3
    libhandy
    gnome.adwaita-icon-theme
    
    # VTE (Virtual Terminal Emulator) - needed for terminal features
    vte
    
    # Development utilities
    git
    curl
    wget
    zenity
    
    # Additional system libraries
    glib
    librsvg
    libxml2
  ];

  # Set environment variables for proper GTK/GObject introspection
  shellHook = ''
    # Create a virtual environment for Python packages
    if [ ! -d ".venv" ]; then
      ${pkgs.python3}/bin/python3 -m venv .venv
    fi
    
    source .venv/bin/activate
    
    # Install Python dependencies from requirements.txt
    if [ -f "p3/requirements.txt" ]; then
      pip install -q -r p3/requirements.txt 2>/dev/null || true
    fi
    
    # Set up proper library paths for GObject introspection
    export GI_TYPELIB_PATH="${pkgs.gtk3}/lib/girepository-1.0:${pkgs.libhandy}/lib/girepository-1.0:${pkgs.vte}/lib/girepository-1.0:$GI_TYPELIB_PATH"
    export LD_LIBRARY_PATH="${pkgs.gtk3}/lib:${pkgs.libhandy}/lib:${pkgs.vte}/lib:$LD_LIBRARY_PATH"
    export PKG_CONFIG_PATH="${pkgs.gtk3}/lib/pkgconfig:${pkgs.glib}/lib/pkgconfig:$PKG_CONFIG_PATH"
    
    echo "✓ LinuxToys development environment loaded"
    echo "  Run 'python3 p3/run.py' to start the application"
  '';
}
