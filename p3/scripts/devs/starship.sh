#!/bin/bash
# name: Starship
# version: 1.0
# description: starship_desc
# icon: starship.png
# repo: https://starship.rs

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

sudo_rq
sudo mkdir -p /usr/local/bin # ensure the directory exists before attempting to install starship
if [[ ":$PATH:" != *":/usr/local/bin"* ]]; then
	export PATH="/usr/local/bin:$PATH"
	[[ -f ~/.bashrc ]] && grep -q "/usr/local/bin" ~/.bashrc || echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
	[[ -f ~/.zshrc ]] && grep -q "/usr/local/bin" ~/.zshrc || echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
	[[ -f ~/.config/fish/config.fish ]] && grep -q "/usr/local/bin" ~/.config/fish/config.fish || echo 'set -gx PATH /usr/local/bin $PATH' >> ~/.config/fish/config.fish
fi

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

	zenwrn "$msg291"
}