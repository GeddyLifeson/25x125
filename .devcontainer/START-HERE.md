# This is the code editor. The app opens next to it.

When the app is ready it shows up inside this window, in a tab named after its address. That takes about 1 minute on later starts, and 15 to 20 minutes the first time (it builds the app and restores the data). The terminal at the bottom shows each step.

**For the app in its own browser tab:** when the terminal says "Open 25x125", a box asks to open the address. Click **Open**. Or Ctrl+click the address in the terminal.

**Bookmark that address** (it looks like `https://<name>-3000.app.github.dev`). It stays the same for this codespace. It only works while the codespace is running: if it says the codespace is stopped, open https://github.com/codespaces, click the codespace to start it, and use the bookmark once the terminal says the app is up.

If nothing showed up: click **Ports** at the bottom of this window, then the globe icon next to **25x125** (port 3000). If there's no port 3000, type `python scripts/codespace.py status` in the terminal to see what happened.

The app starts on the Search screen: pick an area, filter with the chips, click a parcel in the list or on the map, then run feasibility.

The codespace stops after 30 minutes with the editor closed or idle.
