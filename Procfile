# Updated for Heroku deployment with Playwright support
web: PYTHONPATH=$PYTHONPATH:$PWD python setup_playwright.py && PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright gunicorn app:app
