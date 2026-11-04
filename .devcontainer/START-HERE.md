# This is the code editor. The app runs in its own browser tab.

The app takes about 1 minute to start on later starts, and 15 to 20 minutes the first time (it builds the app and restores the data).

**To open it:** click **Terminal** at the bottom and Ctrl+click the address after "Open it". Every new terminal prints it. When the app comes up, a notice at the bottom right also has an **Open in Browser** button. Don't use the editor's built-in browser: it can't sign in to the codespace and shows a blank page.

**Bookmark that address** (it looks like `https://<name>-3000.app.github.dev`). It stays the same for this codespace. It only works while the codespace is running: if it says the codespace is stopped, open https://github.com/codespaces, click the codespace to start it, and use the bookmark once the terminal says the app is up.

If nothing showed up: click **Ports** at the bottom of this window, then the globe icon next to **25x125** (port 3000). If there's no port 3000, type `python scripts/codespace.py status` in the terminal to see what happened.

The app starts on the Search screen: pick an area, filter with the chips, click a parcel in the list or on the map, then run feasibility.

The codespace stops after 30 minutes with the editor closed or idle.
