# Updated for heroku-22 stack compatibility with Playwright buildpack
release: python -m playwright install chromium --with-deps
web: python setup_playwright.py && gunicorn app:app
