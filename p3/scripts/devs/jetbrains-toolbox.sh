# name: JetBrains Toolbox
# version: 1.0
# description: Manage your IDEs the easy way
# icon: jetbrains-toolbox.svg

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq

PKG_NAM="jetbrains-toolbox"
PKG_VER="2.8.1.52155"
PKG_FLL="${PKG_NAM}-${PKG_VER}"
PKG_URL="https://download.jetbrains.com/toolbox/${PKG_FLL}.tar.gz"
PKG_TMP="/tmp/"

## Download
curl -fsSLo "${PKG_TMP}/${PKG_FLL}.tar.gz" "${PKG_URL}" && {
	## Install in /opt
	sudo tar -xvf "${PKG_TMP}/${PKG_FLL}.tar.gz" --strip-components=2 --one-top-level="/opt/${PKG_NAM}" && {
		(
			## Link in /usr
			sudo ln -v -s "/opt/${PKG_NAM}/${PKG_NAM}" /usr/bin/;
			sudo ln -v -s "/opt/${PKG_NAM}/${PKG_NAM}.desktop" /usr/share/applications/;
		) && {
			## Remove tarball from temporary directory 
			rm -vf "${PKG_TMP}/${PKG_FLL}.tar.gz"; 
		}
	};
} || { exit 1; }
