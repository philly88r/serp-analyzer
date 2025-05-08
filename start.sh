#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status.

# Set environment variables for Playwright on Render
export PLAYWRIGHT_BROWSERS_PATH="/opt/render/.playwright"
export PLAYWRIGHT_CHROMIUM_ARGS="--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage"

# Create browser cache directory
mkdir -p .browser_cache
chmod 777 .browser_cache

# Install Playwright and Chromium
echo "--- Installing Playwright and Chromium ---"
/usr/local/bin/python -m playwright install chromium

echo "--- Running setup_playwright.py ---"
/usr/local/bin/python setup_playwright.py

echo "--- Starting Gunicorn ---"
/usr/local/bin/gunicorn --bind 0.0.0.0:$PORT --timeout 300 app:app
