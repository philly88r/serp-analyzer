import os
import sys
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def print_message(message):
    logger.info(message)

def print_error(message):
    logger.error(message)

def setup_playwright():
    print_message("Starting Playwright setup...")
    is_heroku = 'DYNO' in os.environ
    # Default to '0' if the env var is not set, so skip_browser_download becomes False
    skip_browser_download = os.environ.get('PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD', '0') == '1'

    if is_heroku:
        print_message("Running on Heroku.")
        browsers_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH')
        if browsers_path:
            print_message(f"PLAYWRIGHT_BROWSERS_PATH is set to: {browsers_path}")
        else:
            # Default path Playwright uses within the app slug if not overridden
            # Heroku buildpacks typically install browsers to /app/.playwright
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/app/.playwright'
            print_message(f"PLAYWRIGHT_BROWSERS_PATH defaulted to /app/.playwright for Heroku.")

    if skip_browser_download:
        print_message("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD is '1'. Skipping browser installation and verification.")
        print_message("Playwright setup complete (browsers skipped). Application might run in limited functionality mode.")
        return True
    else:
        print_message("Proceeding with browser verification (PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD is not '1').")
        print_message("Assuming Heroku buildpack (e.g., heroku/playwright) has installed browsers if PLAYWRIGHT_BUILDPACK_BROWSERS is set.")
        
        try:
            print_message("Attempting to verify Chromium installation (expected to be provided by Heroku buildpack)...")
            try:
                import playwright # Check if module itself is importable
                from playwright.sync_api import sync_playwright # Further check
                # Fix for AttributeError: module 'playwright' has no attribute '__version__'
                # Try different ways to get the version
                try:
                    from playwright.__version__ import __version__ as playwright_version
                    print_message(f"Playwright module version: {playwright_version} found.")
                except ImportError:
                    print_message(f"Playwright module found, but version information not available.")
            except ImportError:
                print_error("Playwright Python module not found. Cannot verify browser installation.")
                print_message("Application will likely run in limited functionality mode.")
                return True # Allow app to attempt to start, though Playwright calls will fail

            verify_chromium_installation() # This function itself will attempt to launch Playwright
            print_message("Chromium verification successful! Playwright should be ready for use.")
            
        except RuntimeError as e: # This can be raised by verify_chromium_installation
            print_error(f"Chromium verification failed: {e}")
            print_message("Browser could not be verified. Application will likely run in limited functionality mode.")
            return True 
        except Exception as e:
            print_error(f"An unexpected error occurred during browser verification: {type(e).__name__}: {e}")
            print_message("Unexpected issue during browser verification. Application will likely run in limited functionality mode.")
            return True

    print_message("Playwright setup process finished.")
    return True

def install_playwright_browsers(browser_name="chromium"):
    # This function will now only be called if we explicitly decide to manage installation,
    # which we are trying to avoid for Heroku when relying on buildpacks.
    # For safety, keeping it but it should not be hit in the new Heroku flow.
    print_message(f"INFO: 'install_playwright_browsers' called. Attempting to install {browser_name} using 'playwright install {browser_name}'...")
    try:
        # Using sys.executable to ensure we're using the python from the correct environment
        process_result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", browser_name], 
            check=False,  # Set to False to handle errors manually
            capture_output=True, 
            text=True
        )
        if process_result.returncode == 0:
            print_message(f"{browser_name} installation command completed successfully.")
            if process_result.stdout: print_message(f"Stdout: {process_result.stdout.strip()}")
            # Some tools output non-error info to stderr, or it might be empty.
            if process_result.stderr: print_message(f"Stderr: {process_result.stderr.strip()}") 
        else:
            print_error(f"Failed to install {browser_name}. Exit code: {process_result.returncode}")
            if process_result.stderr: print_error(f"Stderr: {process_result.stderr.strip()}")
            if process_result.stdout: print_error(f"Stdout: {process_result.stdout.strip()}") # Log stdout too on error
            raise RuntimeError(f"Playwright install {browser_name} failed with exit code {process_result.returncode}.")
    except Exception as e:
        print_error(f"An unexpected error occurred during 'playwright install {browser_name}': {type(e).__name__}: {e}")
        # Ensure it's a RuntimeError if not already
        if isinstance(e, RuntimeError):
            raise
        else:
            raise RuntimeError(f"Unexpected error during playwright install {browser_name}: {e}")

def verify_chromium_installation():
    print_message("Verifying Chromium installation...")
    try:
        with sync_playwright() as p:
            browser_args = {
                "executable_path": None, # Let Playwright find it
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                    f"--user-data-dir={os.getcwd()}/.browser_cache"
                ],
                "ignore_default_args": ["--disable-extensions"],
                "timeout": 60000  # Increased timeout
            }
            if platform.system() == "Linux" and os.environ.get("DISPLAY") is None:
                print_message("Linux environment with no DISPLAY detected, ensuring headless for verification.")
                # browser_args["headless"] = True # Playwright's chromium is headless by default

            print_message(f"Attempting to launch browser with args: {browser_args}")
            browser = p.chromium.launch(**browser_args)
            page = browser.new_page()
            page.goto("https://example.com")
            title = page.title()
            print_message(f"Successfully loaded page with title: {title}")
            browser.close()
            print_message("Chromium verification successful!")
    except Exception as e:
        print_error(f"Chromium verification failed: {e}")
        raise RuntimeError(f"Chromium verification failed: {e}")

if __name__ == "__main__":
    success = setup_playwright()
    if not success:
        print_error("Failed to set up Playwright properly")
        sys.exit(1)
    print_message("Playwright setup completed successfully from __main__")
