#!/bin/bash

# Advanced LinuxToys AppImage builder using linuxdeploy + Python plugin
# This version handles Python dependencies automatically

# Source utils library
source "$(dirname "$0")/../../libs/utils.lib"

LT_VERSION="$1"
OUTPUT_DIR="$2"

if [ -z "$LT_VERSION" ] || [ -z "$OUTPUT_DIR" ]; then
    _msg "error" "Usage: $0 <version> <output_dir>"
    exit 1
fi

# Ensure correct working directory
cd "$(dirname "$(realpath "$0")")"

# Set up paths relative to the new location
PROJECT_ROOT="$(cd ../../../../ && pwd)"
_msg "info" "Project root: $PROJECT_ROOT"

_msg "info" "Building LinuxToys-${LT_VERSION}-x86_64.AppImage..."

# Configuration
APPDIR="LinuxToys.AppDir"
BUILD_DIR="$OUTPUT_DIR/build_temp"
LINUXDEPLOY_URL="https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
PYTHON_PLUGIN_URL="https://github.com/niess/linuxdeploy-plugin-python/releases/download/continuous/linuxdeploy-plugin-python-x86_64.AppImage"
LINUXDEPLOY_BIN="linuxdeploy-x86_64.AppImage"
PYTHON_PLUGIN_BIN="linuxdeploy-plugin-python-x86_64.AppImage"

# Clean up previous build
_msg "info" "Cleaning up previous build..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Enable AppImage extraction if FUSE is not available
export APPIMAGE_EXTRACT_AND_RUN=1

# Download tools if not present
if [ ! -f "$LINUXDEPLOY_BIN" ]; then
    _msg "info" "Downloading linuxdeploy..."
    wget "$LINUXDEPLOY_URL" -O "$LINUXDEPLOY_BIN"
    chmod +x "$LINUXDEPLOY_BIN"
fi

if [ ! -f "$PYTHON_PLUGIN_BIN" ]; then
    _msg "info" "Downloading linuxdeploy Python plugin..."
    wget "$PYTHON_PLUGIN_URL" -O "$PYTHON_PLUGIN_BIN"
    chmod +x "$PYTHON_PLUGIN_BIN"
fi

# Create basic AppDir structure
_msg "info" "Creating AppDir structure..."
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$APPDIR/usr/share"

# Copy main application files
_msg "info" "Copying application files..."
cp -ru "$PROJECT_ROOT/p3" "$APPDIR/usr/share/linuxtoys"

# Copy system binaries that the app depends on
_msg "info" "Copying system dependencies..."
for binary in bash git curl wget zenity jq; do
    if command -v "$binary" >/dev/null 2>&1; then
        cp "$(which "$binary")" "$APPDIR/usr/bin/" || _msg "warning" "Failed to copy $binary"
    else
        _msg "warning" "Binary $binary not found on system"
    fi
done

# Copy git helpers which are needed for git functionality
if [ -d "/usr/lib/git-core" ]; then
    mkdir -p "$APPDIR/usr/lib/git-core"
    cp /usr/lib/git-core/* "$APPDIR/usr/lib/git-core/" 2>/dev/null || _msg "warning" "Some git-core files could not be copied"
elif [ -d "/usr/libexec/git-core" ]; then
    mkdir -p "$APPDIR/usr/libexec/git-core"
    cp /usr/libexec/git-core/* "$APPDIR/usr/libexec/git-core/" 2>/dev/null || _msg "warning" "Some git-core files could not be copied"
fi

# Create requirements.txt for Python dependencies
if [ ! -f "$PROJECT_ROOT/p3/requirements.txt" ]; then
    _msg "info" "Creating requirements.txt..."
    cat > "$APPDIR/usr/share/linuxtoys/requirements.txt" << 'EOF'
# Python dependencies for LinuxToys
PyGObject>=3.36.0
requests>=2.25.0
urllib3>=1.26.0
certifi>=2021.5.25
EOF
else
    _msg "info" "Using existing requirements.txt"
    # Ensure PyGObject is included for GTK support
    if ! grep -q "PyGObject" "$PROJECT_ROOT/p3/requirements.txt"; then
        echo "PyGObject>=3.36.0" >> "$APPDIR/usr/share/linuxtoys/requirements.txt"
    fi
fi

# Create entry point script
cat > "$APPDIR/usr/bin/linuxtoys" << 'EOF'
#!/bin/bash

# Get the directory containing this script (usr/bin)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# AppDir root
APPDIR="$(dirname "$(dirname "$DIR")")"

# Set up environment
export LD_LIBRARY_PATH="$APPDIR/usr/lib:$APPDIR/usr/lib64:$APPDIR/usr/lib/x86_64-linux-gnu:$APPDIR/lib:$APPDIR/lib64:$APPDIR/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}"
export PATH="$APPDIR/usr/bin:$APPDIR/bin:${PATH}"

# Git paths
if [ -d "$APPDIR/usr/lib/git-core" ]; then
    export GIT_EXEC_PATH="$APPDIR/usr/lib/git-core"
elif [ -d "$APPDIR/usr/libexec/git-core" ]; then
    export GIT_EXEC_PATH="$APPDIR/usr/libexec/git-core"
fi

# SSL
if [ -f "$APPDIR/etc/ssl/certs/ca-certificates.crt" ]; then
    export SSL_CERT_FILE="$APPDIR/etc/ssl/certs/ca-certificates.crt"
    export SSL_CERT_DIR="$APPDIR/etc/ssl/certs"
    export CURL_CA_BUNDLE="$APPDIR/etc/ssl/certs/ca-certificates.crt"
    export REQUESTS_CA_BUNDLE="$APPDIR/etc/ssl/certs/ca-certificates.crt"
fi

# GI Typelib
GI_PATH=""
for path in "$APPDIR/usr/lib/girepository-1.0" "$APPDIR/usr/lib/x86_64-linux-gnu/girepository-1.0" "$APPDIR/usr/lib64/girepository-1.0"; do
    if [ -d "$path" ]; then
        if [ -z "$GI_PATH" ]; then
            GI_PATH="$path"
        else
            GI_PATH="$GI_PATH:$path"
        fi
    fi
done
if [ -n "$GI_PATH" ]; then
    export GI_TYPELIB_PATH="$GI_PATH:${GI_TYPELIB_PATH}"
fi

# Python Path
export PYTHONPATH="$APPDIR/usr/share/linuxtoys:$PYTHONPATH"
export PYTHONHOME="$APPDIR/usr"

# Change to app directory
cd "$APPDIR/usr/share/linuxtoys"

# Run app
exec python3 -c "import sys; from app import main; sys.exit(main.run())" "$@"
EOF

chmod +x "$APPDIR/usr/bin/linuxtoys"

# Copy desktop file and icon
_msg "info" "Setting up desktop integration..."
cp "$PROJECT_ROOT/src/LinuxToys.desktop" "$APPDIR/usr/share/applications/" 2>/dev/null || {
    _msg "warning" "Desktop file not found in src/, creating basic one..."
    cat > "$APPDIR/usr/share/applications/LinuxToys.desktop" << EOF
[Desktop Entry]
Name=LinuxToys
Type=Application
Exec=linuxtoys
Terminal=false
Icon=linuxtoys
Comment=A set of tools for Linux presented in a user-friendly way
Categories=Utility;System;
EOF
}

cp "$PROJECT_ROOT/src/linuxtoys.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/" 2>/dev/null || {
    _msg "warning" "Icon not found in src/, looking for alternatives..."
    # Try to find icon in other locations
    if [ -f "$PROJECT_ROOT/p3/app/icons/app-icon.png" ]; then
        cp "$PROJECT_ROOT/p3/app/icons/app-icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/linuxtoys.png"
    else
        _msg "warning" "No icon found, AppImage will use default icon"
    fi
}

# Copy icon to AppDir root
cp "$APPDIR/usr/share/icons/hicolor/256x256/apps/linuxtoys.png" "$APPDIR/" 2>/dev/null || {
    _msg "warning" "Could not copy icon to AppDir root"
}

# Create the main desktop file in AppDir root
cat > "$APPDIR/LinuxToys.desktop" << EOF
[Desktop Entry]
Name=LinuxToys
Type=Application
Exec=linuxtoys
Terminal=false
Icon=linuxtoys
Comment=A set of tools for Linux presented in a user-friendly way
Categories=Utility;System;
EOF

# Copy SSL certificates for Python requests
_msg "info" "Setting up SSL certificates..."
mkdir -p "$APPDIR/etc/ssl/certs"
if [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
    cp "/etc/ssl/certs/ca-certificates.crt" "$APPDIR/etc/ssl/certs/"
elif [ -f "/etc/pki/tls/certs/ca-bundle.crt" ]; then
    cp "/etc/pki/tls/certs/ca-bundle.crt" "$APPDIR/etc/ssl/certs/ca-certificates.crt"
elif [ -f "/etc/ssl/ca-bundle.pem" ]; then
    cp "/etc/ssl/ca-bundle.pem" "$APPDIR/etc/ssl/certs/ca-certificates.crt"
else
    _msg "warning" "No SSL certificates found in standard locations"
fi

# Copy GTK/GObject introspection files
_msg "info" "Setting up GTK and GObject introspection..."
mkdir -p "$APPDIR/usr/lib/girepository-1.0"
mkdir -p "$APPDIR/usr/share/glib-2.0/schemas"

# Copy GIR files for GTK3
for gir_file in Gtk-3.0.typelib GObject-2.0.typelib GLib-2.0.typelib Gio-2.0.typelib GdkPixbuf-2.0.typelib Gdk-3.0.typelib Pango-1.0.typelib PangoCairo-1.0.typelib cairo-1.0.typelib; do
    for gir_dir in /usr/lib/girepository-1.0 /usr/lib/x86_64-linux-gnu/girepository-1.0 /usr/lib64/girepository-1.0; do
        if [ -f "$gir_dir/$gir_file" ]; then
            cp "$gir_dir/$gir_file" "$APPDIR/usr/lib/girepository-1.0/" 2>/dev/null || true
            break
        fi
    done
done

# Copy GLib schemas
if [ -d "/usr/share/glib-2.0/schemas" ]; then
    cp -r /usr/share/glib-2.0/schemas/* "$APPDIR/usr/share/glib-2.0/schemas/" 2>/dev/null || _msg "warning" "Could not copy GLib schemas"
    # Compile schemas
    if command -v glib-compile-schemas >/dev/null 2>&1; then
        glib-compile-schemas "$APPDIR/usr/share/glib-2.0/schemas/" 2>/dev/null || _msg "warning" "Could not compile GLib schemas"
    fi
fi

# Set up environment for the Python plugin
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
export PYTHON_VERSION
export PYTHON_APPDIR="$PWD/$APPDIR"

_msg "info" "Using Python version: $PYTHON_VERSION"

# Use linuxdeploy with Python plugin
_msg "info" "Running linuxdeploy with Python plugin..."

# Set environment variables for the Python plugin
export DEPLOY_GTK_VERSION=3
export LINUXDEPLOY_PLUGIN_PYTHON_INSTALL_SYSTEM_PACKAGES=1
export LINUXDEPLOY_PLUGIN_PYTHON_SCAN_DIRS="$APPDIR/usr/share/linuxtoys"
# Create dummy Tcl/Tk directories to prevent plugin errors
sudo mkdir -p /usr/share/tcl8.6 /usr/share/tk8.6 2>/dev/null || true

./"$LINUXDEPLOY_BIN" \
    --appdir "$APPDIR" \
    --plugin python \
    --desktop-file "$APPDIR/LinuxToys.desktop" \
    --icon-file "$APPDIR/linuxtoys.png" \
    --library /lib64/libgtk-3.so.0 \
    --library /lib64/libgdk-3.so.0 \
    --library /lib64/libgio-2.0.so.0 \
    --library /lib64/libgobject-2.0.so.0 \
    --library /lib64/libglib-2.0.so.0 \
    --output appimage

# Move the resulting AppImage
_msg "info" "Moving AppImage to output dir..."
mv LinuxToys-*.AppImage "$OUTPUT_DIR/" 2>/dev/null || {
    _msg "warning" "Could not find generated AppImage with expected name pattern"
    # Look for any AppImage files
    for img in *.AppImage; do
        if [ -f "$img" ]; then
            mv "$img" "$OUTPUT_DIR/"
            break
        fi
    done
}

# Check if AppImage was created successfully
if [ -f "$OUTPUT_DIR/LinuxToys-${LT_VERSION}-x86_64.AppImage" ]; then
    _msg "info" "Build completed! AppImage created: LinuxToys-${LT_VERSION}-x86_64.AppImage"
    
    # Show file size
    FILESIZE=$(du -h "$OUTPUT_DIR/LinuxToys-${LT_VERSION}-x86_64.AppImage" | cut -f1)
    _msg "info" "AppImage size: $FILESIZE"
    _msg "info" "Location: $OUTPUT_DIR/LinuxToys-${LT_VERSION}-x86_64.AppImage"
else
    _msg "error" "Failed to create AppImage!"
    exit 1
fi
