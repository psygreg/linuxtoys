#!/usr/bin/env python3

import sys
import os # Import the 'os' module
from app import main

if __name__ == "__main__":
    # --- UPDATE CHECK ---
    # Before launching the GUI, run the updater script.
    # The updater will handle all logic, including restarting if necessary.
    # If there are no updates, it will exit and the code below will run.
    os.system('./helpers/update_self.sh')

    # --- LAUNCH GUI ---
    # This part only runs if the updater script exits normally.
    sys.exit(main.run())
