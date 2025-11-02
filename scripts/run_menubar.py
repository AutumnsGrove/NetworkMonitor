#!/usr/bin/env python3
"""Script to run the Network Monitor menubar app."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.menubar import run_menubar

if __name__ == "__main__":
    run_menubar()
