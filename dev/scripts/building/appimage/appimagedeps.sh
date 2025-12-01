#!/bin/bash

# Dependency checker for LinuxToys AppImage build
# Run this before building to ensure all dependencies are available

# Set up paths relative to the new location
echo "Checking Ubuntu dependencies for LinuxToys AppImage build..."
echo "Project root: $PROJECT_ROOT"
echo "========================================================="

# Required packages for Ubuntu
REQUIRED_PACKAGES=(
    "bash"
    "git" 
    "curl"
    "wget"
    "zenity"
    "python3"
    "python3-gi"
    "libgtk-3-0"
    "gir1.2-gtk-3.0"
    "jq"
)

# Required binaries
REQUIRED_BINARIES=(
    "bash"
    "git"
    "curl"
    "wget"
    "zenity"
    "python3"
    "jq"
)

# Required libraries
REQUIRED_LIBRARIES=(
    "/lib64/libgtk-3.so.0"
    "/usr/lib/x86_64-linux-gnu/libgdk-3.so.0"
    "/usr/lib/x86_64-linux-gnu/libgio-2.0.so.0"
    "/usr/lib/x86_64-linux-gnu/libgobject-2.0.so.0"
    "/usr/lib/x86_64-linux-gnu/libglib-2.0.so.0"
)

# Required GIR files
REQUIRED_GIR=(
    "Gtk-3.0.typelib"
    "GObject-2.0.typelib"
    "GLib-2.0.typelib"
    "Gio-2.0.typelib"
)

missing_packages=()
missing_binaries=()
missing_libraries=()
missing_gir=()

echo "Checking packages..."
for package in "${REQUIRED_PACKAGES[@]}"; do
    # Handle package name variations and architecture suffixes
    case "$package" in
        "libgtk-3-0")
            if dpkg -l | grep -E "^ii  (libgtk-3-0|libgtk-3-0t64)" | grep -q .; then
                echo "✅ Found package: $package"
            else
                missing_packages+=("$package")
                echo "❌ Missing package: $package"
            fi
            ;;
        *)
            if dpkg -l | grep -E "^ii  $package(:amd64|:i386)?" | grep -q .; then
                echo "✅ Found package: $package"
            else
                missing_packages+=("$package")
                echo "❌ Missing package: $package"
            fi
            ;;
    esac
done

echo ""
echo "Checking binaries..."
for binary in "${REQUIRED_BINARIES[@]}"; do
    if ! command -v "$binary" >/dev/null 2>&1; then
        missing_binaries+=("$binary")
        echo "❌ Missing binary: $binary"
    else
        echo "✅ Found binary: $binary at $(which "$binary")"
    fi
done

echo ""
echo "Checking libraries..."
for library in "${REQUIRED_LIBRARIES[@]}"; do
    if [ ! -f "$library" ]; then
        missing_libraries+=("$library")
        echo "❌ Missing library: $library"
    else
        echo "✅ Found library: $library"
    fi
done

echo ""
echo "Checking GIR typelib files..."
for gir in "${REQUIRED_GIR[@]}"; do
    found=false
    for gir_dir in /usr/lib/girepository-1.0 /usr/lib/x86_64-linux-gnu/girepository-1.0 /usr/lib64/girepository-1.0; do
        if [ -f "$gir_dir/$gir" ]; then
            echo "✅ Found GIR: $gir at $gir_dir"
            found=true
            break
        fi
    done
    if [ "$found" = false ]; then
        missing_gir+=("$gir")
        echo "❌ Missing GIR: $gir"
    fi
done

echo ""
echo "Checking Python modules..."
python3 -c "
import sys
modules = ['gi', 'gi.repository.Gtk', 'gi.repository.Gdk', 'json', 'os', 'pathlib']
missing = []
for module in modules:
    try:
        __import__(module)
        print(f'✅ Python module: {module}')
    except ImportError:
        missing.append(module)
        print(f'❌ Missing Python module: {module}')
        
if missing:
    sys.exit(1)
"

echo ""
echo "========================================================="

# Summary
if [ ${#missing_packages[@]} -eq 0 ] && [ ${#missing_binaries[@]} -eq 0 ] && [ ${#missing_libraries[@]} -eq 0 ] && [ ${#missing_gir[@]} -eq 0 ]; then
    echo "🎉 All dependencies are available! You can proceed with the AppImage build."
    echo ""
    echo "To install any missing packages, run:"
    echo "sudo apt update && sudo apt install bash git curl wget zenity python3 python3-gi python3-gi-cairo libgtk-3-0 gir1.2-gtk-3.0 jq"
    exit 0
else
    echo "❌ Some dependencies are missing!"
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        echo ""
        echo "Missing packages: ${missing_packages[*]}"
        echo "Install with: sudo apt install ${missing_packages[*]}"
    fi
    
    if [ ${#missing_binaries[@]} -gt 0 ]; then
        echo ""
        echo "Missing binaries: ${missing_binaries[*]}"
    fi
    
    if [ ${#missing_libraries[@]} -gt 0 ]; then
        echo ""
        echo "Missing libraries: ${missing_libraries[*]}"
    fi
    
    if [ ${#missing_gir[@]} -gt 0 ]; then
        echo ""
        echo "Missing GIR files: ${missing_gir[*]}"
    fi
    
    echo ""
    echo "Complete installation command:"
    echo "sudo apt update && sudo apt install bash git curl wget zenity python3 python3-gi python3-gi-cairo libgtk-3-0 gir1.2-gtk-3.0 jq"
    
    exit 1
fi
