"""
QuantDinger Local Trade Client - GUI Application

Main entry point for the graphical user interface.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.gui.app import QuantDingerApp


def main():
    """Main entry point."""
    app = QuantDingerApp()
    app.run()


if __name__ == "__main__":
    main()
