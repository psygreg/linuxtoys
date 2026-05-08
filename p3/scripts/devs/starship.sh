#!/bin/bash
# name: Starship
# version: 1.0
# description: starship_desc
# icon: starship.png
# repo: https://starship.rs

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

sudo_rq
sudo mkdir -p /usr/local/bin # ensure the directory exists before attempting to install starship
if [[ ":$PATH:" != *":/usr/local/bin"* ]]; then
	export PATH="/usr/local/bin:$PATH"
	[[ -f ~/.bashrc ]] && grep -q "/usr/local/bin" ~/.bashrc || echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
	[[ -f ~/.zshrc ]] && grep -q "/usr/local/bin" ~/.zshrc || echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
	[[ -f ~/.config/fish/config.fish ]] && grep -q "/usr/local/bin" ~/.config/fish/config.fish || echo 'set -gx PATH /usr/local/bin $PATH' >> ~/.config/fish/config.fish
fi
prep_create /usr/local/bin/starship # track file for reversion
sudo rm /usr/local/bin/starship # remove created file to ensure correct procedure from starship script
curl -fsSL https://starship.rs/install.sh | sudo sh -s -- -f -y && {
	grep -q "starship init" ~/.bashrc || {
		prep_edit "$HOME/.bashrc"
		echo -e "\neval \"\$(starship init bash)\"" >> ~/.bashrc;
	}
	
	grep -q "starship init" ~/.zshrc || {
		prep_edit "$HOME/.zshrc"
		echo -e "\neval \"\$(starship init zsh)\"" >> ~/.zshrc;
	}

	grep -q "starship init" ~/.config/fish/config.fish || {
		prep_edit "$HOME/.config/fish/config.fish"
		echo -e "\nstarship init fish | source" >> ~/.config/fish/config.fish;
	}

	zenwrn "$msg291"
}