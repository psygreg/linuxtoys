#!/bin/bash
# name: QPWGraph
# version: 1.0
# description: qpw_desc
# icon: qpwgraph.svg
# repo: https://github.com/rncbc/qpwgraph

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    org.rncbc.qpwgraph
)
_flatpak_