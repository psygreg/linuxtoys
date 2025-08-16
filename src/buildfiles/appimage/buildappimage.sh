#!/bin/bash

# Advanced LinuxToys AppImage builder using linuxdeploy + Python plugin
# This version handles Python dependencies automatically

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Ensure correct working directory
cd "$(dirname "$(realpath "$0")")"

# Set up paths relative to the new location
PROJECT_ROOT="$(cd ../../../ && pwd)"
echo "Project root: $PROJECT_ROOT"

# Ask for version number
echo "LinuxToys AppImage Builder"
echo "=========================="
echo "This script will create a portable AppImage with all dependencies included."
echo ""
read -p "Enter version number (e.g., 5.0, 5.1, 6.0-beta): " VERSION

if [ -z "$VERSION" ]; then
    echo_error "Error: Version number is required!"
    echo "Example: 5.0"
    exit 1
fi

# Validate version format (basic check)
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+.*$ ]]; then
    echo_warn "Warning: Version format should be like '5.0' or '5.1-beta'"
    read -p "Continue anyway? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[yY]$ ]]; then
        echo "Build cancelled."
        exit 1
    fi
fi

echo "Building LinuxToys-${VERSION}-x86_64.AppImage..."
echo ""

# Remove existing AppImage if it exists in project root
if [ -f "$PROJECT_ROOT/LinuxToys-${VERSION}-x86_64.AppImage" ]; then
    echo_info "Removing existing LinuxToys-${VERSION}-x86_64.AppImage..."
    rm "$PROJECT_ROOT/LinuxToys-${VERSION}-x86_64.AppImage"
fi

# Configuration
APPDIR="LinuxToys.AppDir"
BUILD_DIR="build-linuxdeploy-python"
LINUXDEPLOY_URL="https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
PYTHON_PLUGIN_URL="https://github.com/niess/linuxdeploy-plugin-python/releases/download/continuous/linuxdeploy-plugin-python-x86_64.AppImage"
LINUXDEPLOY_BIN="linuxdeploy-x86_64.AppImage"
PYTHON_PLUGIN_BIN="linuxdeploy-plugin-python-x86_64.AppImage"

# Clean up previous build
echo_info "Cleaning up previous build..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Download tools if not present
if [ ! -f "$LINUXDEPLOY_BIN" ]; then
    echo_info "Downloading linuxdeploy..."
    wget "$LINUXDEPLOY_URL" -O "$LINUXDEPLOY_BIN"
    chmod +x "$LINUXDEPLOY_BIN"
fi

if [ ! -f "$PYTHON_PLUGIN_BIN" ]; then
    echo_info "Downloading linuxdeploy Python plugin..."
    wget "$PYTHON_PLUGIN_URL" -O "$PYTHON_PLUGIN_BIN"
    chmod +x "$PYTHON_PLUGIN_BIN"
fi

# Create basic AppDir structure
echo_info "Creating AppDir structure..."
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# Copy main application files
echo_info "Copying application files..."
cp -r "$PROJECT_ROOT/p3" "$APPDIR/usr/bin/"

# Copy system binaries that the app depends on
echo_info "Copying system dependencies..."
for binary in bash git curl wget zenity jq; do
    if command -v "$binary" >/dev/null 2>&1; then
        cp "$(which "$binary")" "$APPDIR/usr/bin/" || echo_warn "Failed to copy $binary"
    else
        echo_warn "Binary $binary not found on system"
    fi
done

# Copy git helpers which are needed for git functionality
if [ -d "/usr/lib/git-core" ]; then
    mkdir -p "$APPDIR/usr/lib/git-core"
    cp /usr/lib/git-core/* "$APPDIR/usr/lib/git-core/" 2>/dev/null || echo_warn "Some git-core files could not be copied"
elif [ -d "/usr/libexec/git-core" ]; then
    mkdir -p "$APPDIR/usr/libexec/git-core"
    cp /usr/libexec/git-core/* "$APPDIR/usr/libexec/git-core/" 2>/dev/null || echo_warn "Some git-core files could not be copied"
fi

# Create requirements.txt for Python dependencies
if [ ! -f "$PROJECT_ROOT/p3/requirements.txt" ]; then
    echo_info "Creating requirements.txt..."
    cat > "$APPDIR/usr/bin/p3/requirements.txt" << 'EOF'
# Python dependencies for LinuxToys
PyGObject>=3.36.0
requests>=2.25.0
urllib3>=1.26.0
certifi>=2021.5.25
EOF
else
    echo_info "Using existing requirements.txt"
    # Ensure PyGObject is included for GTK support
    if ! grep -q "PyGObject" "$PROJECT_ROOT/p3/requirements.txt"; then
        echo "PyGObject>=3.36.0" >> "$APPDIR/usr/bin/p3/requirements.txt"
    fi
fi

# Create entry point script
cat > "$APPDIR/usr/bin/linuxtoys" << 'EOF'
#!/usr/bin/env python3

import sys
import os
from pathlib import Path

# Get the directory containing this script
script_dir = Path(__file__).parent.absolute()
app_dir = script_dir / "p3"
appdir = script_dir.parent.parent

# Set up environment for GTK and system tools
os.environ['LD_LIBRARY_PATH'] = f"{appdir}/usr/lib:{appdir}/usr/lib64:{appdir}/usr/lib/x86_64-linux-gnu:{appdir}/lib:{appdir}/lib64:{appdir}/lib/x86_64-linux-gnu:{os.environ.get('LD_LIBRARY_PATH', '')}"
os.environ['PATH'] = f"{appdir}/usr/bin:{appdir}/bin:{os.environ.get('PATH', '')}"

# Set up Git paths
git_core_paths = [
    f"{appdir}/usr/lib/git-core",
    f"{appdir}/usr/libexec/git-core"
]
for git_path in git_core_paths:
    if Path(git_path).exists():
        os.environ['GIT_EXEC_PATH'] = git_path
        break

# Set up SSL certificates
ssl_cert_file = f"{appdir}/etc/ssl/certs/ca-certificates.crt"
if Path(ssl_cert_file).exists():
    os.environ['SSL_CERT_FILE'] = ssl_cert_file
    os.environ['SSL_CERT_DIR'] = f"{appdir}/etc/ssl/certs"
    os.environ['CURL_CA_BUNDLE'] = ssl_cert_file
    os.environ['REQUESTS_CA_BUNDLE'] = ssl_cert_file

# Set up GI typelib path for GTK
gi_typelib_paths = [
    f"{appdir}/usr/lib/girepository-1.0",
    f"{appdir}/usr/lib/x86_64-linux-gnu/girepository-1.0",
    f"{appdir}/usr/lib64/girepository-1.0"
]
existing_paths = [path for path in gi_typelib_paths if Path(path).exists()]
if existing_paths:
    os.environ['GI_TYPELIB_PATH'] = ':'.join(existing_paths)

# Add the app directory to Python path
sys.path.insert(0, str(app_dir))

# Change to app directory
os.chdir(app_dir)

# Import and run the main application
try:
    from app import main
    sys.exit(main.run())
except ImportError as e:
    print(f"Error importing main application: {e}", file=sys.stderr)
    sys.exit(1)
EOF

chmod +x "$APPDIR/usr/bin/linuxtoys"

# Copy desktop file and icon
echo_info "Setting up desktop integration..."
cp "$PROJECT_ROOT/src/LinuxToys.desktop" "$APPDIR/usr/share/applications/" 2>/dev/null || {
    echo_warn "Desktop file not found in src/, creating basic one..."
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
    echo_warn "Icon not found in src/, looking for alternatives..."
    # Try to find icon in other locations
    if [ -f "$PROJECT_ROOT/p3/app/icons/app-icon.png" ]; then
        cp "$PROJECT_ROOT/p3/app/icons/app-icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/linuxtoys.png"
    else
        echo_warn "No icon found, AppImage will use default icon"
    fi
}

# Copy icon to AppDir root
cp "$APPDIR/usr/share/icons/hicolor/256x256/apps/linuxtoys.png" "$APPDIR/" 2>/dev/null || {
    echo_warn "Could not copy icon to AppDir root"
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
echo_info "Setting up SSL certificates..."
mkdir -p "$APPDIR/etc/ssl/certs"
if [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
    cp "/etc/ssl/certs/ca-certificates.crt" "$APPDIR/etc/ssl/certs/"
elif [ -f "/etc/pki/tls/certs/ca-bundle.crt" ]; then
    cp "/etc/pki/tls/certs/ca-bundle.crt" "$APPDIR/etc/ssl/certs/ca-certificates.crt"
elif [ -f "/etc/ssl/ca-bundle.pem" ]; then
    cp "/etc/ssl/ca-bundle.pem" "$APPDIR/etc/ssl/certs/ca-certificates.crt"
else
    echo_warn "No SSL certificates found in standard locations"
fi

# Copy GTK/GObject introspection files
echo_info "Setting up GTK and GObject introspection..."
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
    cp -r /usr/share/glib-2.0/schemas/* "$APPDIR/usr/share/glib-2.0/schemas/" 2>/dev/null || echo_warn "Could not copy GLib schemas"
    # Compile schemas
    if command -v glib-compile-schemas >/dev/null 2>&1; then
        glib-compile-schemas "$APPDIR/usr/share/glib-2.0/schemas/" 2>/dev/null || echo_warn "Could not compile GLib schemas"
    fi
fi

# Set up environment for the Python plugin
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
export PYTHON_VERSION
export PYTHON_APPDIR="$PWD/$APPDIR"

echo_info "Using Python version: $PYTHON_VERSION"

# Use linuxdeploy with Python plugin
echo_info "Running linuxdeploy with Python plugin..."

# Set environment variables for the Python plugin
export DEPLOY_GTK_VERSION=3
export LINUXDEPLOY_PLUGIN_PYTHON_INSTALL_SYSTEM_PACKAGES=1

./"$LINUXDEPLOY_BIN" \
    --appdir "$APPDIR" \
    --plugin python \
    --executable "$APPDIR/usr/bin/linuxtoys" \
    --desktop-file "$APPDIR/LinuxToys.desktop" \
    --icon-file "$APPDIR/linuxtoys.png" \
    --library /usr/lib/x86_64-linux-gnu/libgtk-3.so.0 \
    --library /usr/lib/x86_64-linux-gnu/libgdk-3.so.0 \
    --library /usr/lib/x86_64-linux-gnu/libgio-2.0.so.0 \
    --library /usr/lib/x86_64-linux-gnu/libgobject-2.0.so.0 \
    --library /usr/lib/x86_64-linux-gnu/libglib-2.0.so.0 \
    --output appimage

# Move the resulting AppImage
echo_info "Moving AppImage to project root..."
mv LinuxToys-*.AppImage "$PROJECT_ROOT/LinuxToys-${VERSION}-x86_64.AppImage" 2>/dev/null || {
    echo_warn "Could not find generated AppImage with expected name pattern"
    # Look for any AppImage files
    for img in *.AppImage; do
        if [ -f "$img" ]; then
            mv "$img" "$PROJECT_ROOT/LinuxToys-${VERSION}-x86_64.AppImage"
            break
        fi
    done
}

# Check if AppImage was created successfully
if [ -f "$PROJECT_ROOT/LinuxToys-${VERSION}-x86_64.AppImage" ]; then
    echo_info "Build completed! AppImage created: LinuxToys-${VERSION}-x86_64.AppImage"
    echo_info "You can now run: ./LinuxToys-${VERSION}-x86_64.AppImage"
    
    # Show file size
    FILESIZE=$(du -h "$PROJECT_ROOT/LinuxToys-${VERSION}-x86_64.AppImage" | cut -f1)
    echo_info "AppImage size: $FILESIZE"
    echo_info "Location: $PROJECT_ROOT/LinuxToys-${VERSION}-x86_64.AppImage"
else
    echo_error "Failed to create AppImage!"
    exit 1
fi
