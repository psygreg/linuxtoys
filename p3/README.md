# Lintoy-PoC 🧸

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

> A simple and beautiful graphical launcher for your favorite automation scripts on Linux.

**Important Note:** This project is a proof-of-concept and a learning exercise, heavily inspired by the original [linuxtoys by psygreg](https://github.com/psygreg/linuxtoys). Its main purpose was to explore GUI development with Python and GTK3.

Lintoy-PoC provides a clean, user-friendly interface to organize and run shell scripts. Instead of hunting through folders or remembering command-line syntax, you can browse your scripts by category and run them with a single click, viewing the live output in an integrated console.

![Application Screenshot](httpsd://i.imgur.com/your-screenshot.png)
*(You should replace the link above with a real screenshot of your app!)*

---
## Why Python + GTK3?

The primary goal for this exercise was to create a graphical application with **minimal new dependencies** for the end-user.
* **Python** was chosen because it is pre-installed on virtually every modern Linux distribution.
* **GTK3** was chosen because its core libraries are often already on a user's system, regardless of their desktop environment. Popular applications like **Firefox, GIMP, and Inkscape** use GTK3, meaning that users on GNOME, KDE, or XFCE likely have the necessary libraries installed, making this app very lightweight to add.

---
## Features

* **Visual Grid Layout:** Displays your scripts as icons in a modern grid layout.
* **Automatic Categorization:** Creates categories based on the subfolders inside the `scripts/` directory.
* **Integrated Console:** Executes scripts in a background thread and displays their live output in a pop-up dialog—no external terminal needed.
* **Metadata Parsing:** Reads a simple header from each `.sh` file to get its name, description, and icon.
* **Tooltips:** Hover over any script to see its full description.
* **Easy to Extend:** Simply drop new `.sh` files into the category folders to add them to the launcher.

---
## Installation & Setup

**1. Install Dependencies**

First, ensure you have Python 3 and the GTK3 bindings installed. On a Debian/Ubuntu-based system, you can do this with:
```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-3.0
```

**2. Clone the Repository**

```bash
git clone [https://github.com/rediv/lintoy-poc.git](https://github.com/rediv/lintoy-poc.git)
cd lintoy-poc
```
---
## Usage

To run the application, simply execute the `run.py` script from the root of the project directory:

```bash
python3 run.py
```
---
## Adding Your Own Scripts

This is the best part! Adding new scripts is incredibly easy.

**1. Create a Category Folder**

If it doesn't already exist, create a folder for your script's category inside the `scripts/` directory. For example:
```bash
mkdir "scripts/Networking Tools"
```

**2. Create Your Script File**

Create a new file with the `.sh` extension inside your category folder. The application will find it automatically.

**3. Add the Required Header**

At the very top of your `.sh` file, add a commented header. The application uses this to display the script in the UI.

**Required Header Format:**
```bash
#!/bin/bash
# NAME: The display name of your script
# VERSION: The script's version (e.g., 1.0)
# DESCRIPTION: A sentence or two explaining what the script does. This appears on hover.
# ICON: A standard Freedesktop icon name (e.g., network-wired, accessories-calculator, etc.)

# --- Your script's code goes here ---
```
**Note:** The scripts included in this repository are **non-functional dummy examples** for demonstration purposes only. They `echo` text but do not perform any real system actions.

---
## Important Limitations

The current implementation displays the full output from scripts but **does not yet support providing input back to them**. This means that scripts requiring user interaction (like `sudo` password prompts or "y/n" confirmations) will appear to hang or will fail, as there is no way to send a response.

---
## License

This project is licensed under the **GNU General Public License v3.0**. See the `LICENSE` file for details or visit the [GNU website](https://www.gnu.org/licenses/gpl-3.0.html).
