#!/bin/bash
# name: Distrobox Command Handler
# version: 1.0
# description: dch_desc
# icon: cnfh.svg
# nocontainer: invert
# compat: !steamos

# --- End of script code ---
sudo_ ln -s /usr/bin/distrobox-host-exec /usr/local/bin/xdg-open
info "$finishmsg"
