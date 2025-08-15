#!/usr/bin/env python3
"""
Test script to verify the CLI ostree deployment check functionality.
This simulates being on an ostree system with pending deployments.
"""

import sys
import os

# Add the current directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.cli_helper import check_ostree_deployment_cli

def main():
    print("Testing CLI ostree deployment check...")
    print("This test simulates a system with pending deployments.")
    print("Note: This will show the actual CLI prompts that users would see.")
    print()
    
    # Mock the check_ostree_pending_deployments to return True
    import app.cli_helper
    original_check = app.cli_helper.check_ostree_pending_deployments
    
    def mock_check():
        return True
    
    app.cli_helper.check_ostree_pending_deployments = mock_check
    
    try:
        result = check_ostree_deployment_cli()
        print(f"\nTest result: {result}")
        if result:
            print("User chose to continue despite pending deployments.")
        else:
            print("User chose to exit or reboot.")
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        # Restore original function
        app.cli_helper.check_ostree_pending_deployments = original_check

if __name__ == "__main__":
    main()
