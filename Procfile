# Updated for Heroku deployment with Playwright support
# Attempting to force Heroku to pick up the latest Procfile changes
web: pip install playwright && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 python setup_playwright.py && gunicorn app:app
