## THESE ARE THE INSTRUCTIONS TO ADD NON-STEAM GAMES TO STEAM FLATPAK.
This is required to use them in console mode.

### Limitations
- Games from Heroic Games Launcher cannot be launched unless HGL is open in the background. You will have to tick "Close to taskbar", "Start minimized" and "Minimize Heroic when launching a game" in HGL settings.
- Lutris games should work without issue, although you still need mouse and keyboard to operate other game stores' launchers, so it is recommended you add only direct shortcuts to games to Steam.
- You should enable autologin since having to type your user password defeats the purpose of this trick. For Plasma, go to System Settings > Color and Theme > Authentication (SDDM) > Behaviour > tick the first box and select the proper session.

## How-To

### Lutris

1. On Lutris, open the settings for any game you wish to add to Big Picture.
2. Look for the Identifier, more specifically, it's internal ID number.
3. Create a desktop shortcut for the game. This is important.
4. On Steam, add a non-Steam game and point it to the desktop shortcut. It may not appear at first, you will need to change the pop-up window to look for any filetypes.
5. You will find a new 'env' entry. Right-click it and go to Properties, and replace each line as follows, replacing 'YOUR-USERNAME' with your Linux username, and '6' with the internal ID number you got earlier:
- Name: Game's name, so it doesn't appear as 'env' in the menu.
- Target: `flatpak-spawn --host`
- Launch from: `"/home/YOUR-USERNAME"`
- Launch options: `env LUTRIS_SKIP_INIT=1 flatpak run net.lutris.Lutris lutris:rungameid/6`

### Heroic

1. Go to Heroic's Settings
2. Change Steam path to `/home/YOUR-USERNAME/.var/app/com.valvesoftware.Steam/.steam/steam`
3. Follow the steps mentioned in **Limitations** to ensure Heroic starts with your OS.
4. You may now either set Heroic to add Steam shortcuts automatically, or add the shortcuts manually for each game by selecting them, going to "..." and "Add to Steam"

You may use [SteamGridDB](https://www.steamgriddb.com/) to download cover arts and whatnot to give these shortcuts a good look in Big Picture.