#!/bin/bash
# Nuitka build script for LinuxToys
# Usage: build.sh <version> <output_path>
# Example: build.sh 1.1 /tmp/builds

# Source utils.lib
SCRIPT_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
source "$SCRIPT_DIR/../../libs/utils.lib"

# Detect project root automatically
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

# Check CLI arguments
if [ $# -ne 2 ]; then
    _msg error "Usage: $0 <version> <output_path>"
    _msg info "Example: $0 1.1 /tmp/builds"
    exit 1
fi

LT_VERSION="$1"
OUTPUT_PATH="$2"

# Validate project structure
if [ ! -d "$PROJECT_ROOT/p3" ]; then
    _msg error "Invalid project structure: $PROJECT_ROOT/p3 not found"
    exit 1
fi

# Nuitka binary path
Nuitka="$HOME/.local/bin/nuitka"

if [ ! -f "$Nuitka" ]; then
    _msg error "Nuitka not found at $Nuitka"
    exit 1
fi

ENTRY_POINT="$PROJECT_ROOT/p3/run.py"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_PATH"

_msg info "Starting Nuitka build for version $LT_VERSION..."
_msg info "Project Root: $PROJECT_ROOT"
_msg info "Entry Point: $ENTRY_POINT"
_msg info "Output Path: $OUTPUT_PATH"

"$Nuitka" --onefile --follow-imports --output-dir="$OUTPUT_PATH" \
    --include-data-dir="$PROJECT_ROOT/p3/app/icons=app/icons" \
    --include-data-dir="$PROJECT_ROOT/p3/helpers=helpers" \
    --include-data-dir="$PROJECT_ROOT/p3/libs=libs" \
    --include-data-dir="$PROJECT_ROOT/p3/scripts=scripts" \
    --include-data-file="$PROJECT_ROOT/p3/LICENSE=LICENSE" \
    --include-data-file="$PROJECT_ROOT/p3/style.css=style.css" \
    --include-data-file="$PROJECT_ROOT/p3/manifest.txt=manifest.txt" \
    --include-data-file="$PROJECT_ROOT/p3/update_version.py=update_version.py" \
    "$ENTRY_POINT"

if [ $? -eq 0 ]; then
    _msg info "Build successful! Artifacts are in $OUTPUT_PATH"
else
    _msg error "Build failed."
    exit 1
fi