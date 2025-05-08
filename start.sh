#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status.

echo "--- Running setup_playwright.py ---"
python setup_playwright.py

echo "--- Starting Gunicorn ---"
gunicorn --bind 0.0.0.0:$PORT --timeout 300 app:app
