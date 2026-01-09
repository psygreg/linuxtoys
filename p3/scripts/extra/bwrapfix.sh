#!/bin/bash
# name: Bubblewrap Fix
# description: bwrapfix_desc
# icon: system-run
# compat: ubuntu
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
sudo sh -c 'cat > /etc/apparmor.d/bwrap <<EOF
# Este perfil permite tudo e só existe para dar ao
# aplicativo um nome em vez de ter o rótulo "unconfined"

abi <abi/4.0>,
include <tunables/global>

profile bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,

  # Adições e substituições específicas do site. Veja local/README para detalhes.
  include if exists <local/bwrap>
}
EOF'
sudo systemctl restart apparmor.service