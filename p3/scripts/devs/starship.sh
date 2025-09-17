#!/bin/bash
# name: Starship
# version: 1.0
# description: The minimal, blazing-fast, and infinitely customizable prompt for any shell!
# icon: starship.png

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/helpers.lib"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"

sudo_rq
curl -fsSL https://starship.rs/install.sh | sudo sh -s -- -f -y && {
	grep -q "starship init" ~/.bashrc || {
		echo -e "\neval \"\$(starship init bash)\"" >> ~/.bashrc;
	}
	
	grep -q "starship init" ~/.zshrc || {
		echo -e "\neval \"\$(starship init zsh)\"" >> ~/.zshrc;
	}

	grep -q "starship init" ~/.config/fish/config.fish || {
		echo -e "\nstarship init fish | source" >> ~/.config/fish/config.fish;
	}
}