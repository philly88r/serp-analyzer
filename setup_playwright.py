import os
import sys
import subprocess
import logging
import platform
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_playwright():
    """
    Ensure Playwright and Chromium are properly installed and configured.
    This script is meant to be run before starting the web server on Heroku.
    """
    logger.info(f"Setting up Playwright on {platform.system()}...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    
    is_heroku = 'DYNO' in os.environ
    logger.info(f"Running on Heroku: {is_heroku}")
    
    skip_browser_download = os.environ.get('PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD', '') == '1'
    logger.info(f"PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD: {skip_browser_download}")
    
    if is_heroku:
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/app/.playwright'
        logger.info(f"Set PLAYWRIGHT_BROWSERS_PATH to {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")
        
        os.environ['PLAYWRIGHT_CHROMIUM_ARGS'] = '--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage'
        logger.info(f"Set PLAYWRIGHT_CHROMIUM_ARGS to {os.environ.get('PLAYWRIGHT_CHROMIUM_ARGS')}")

    if skip_browser_download:
        logger.info("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD is set. Skipping browser installation and verification.")
        logger.info("The app will attempt to run in limited functionality mode if browsers are not found by other means.")
        # Ensure playwright module itself is importable, as app.py might need it for types/exceptions
        try:
            import playwright
            from playwright.__version__ import __version__ as playwright_version
            logger.info(f"Playwright module is installed (version: {playwright_version})")
        except ImportError:
            logger.error("Playwright module not found even though installation was supposed to be handled by Procfile.")
            logger.error("This indicates a problem with the deployment setup.")
            # Even if playwright module itself is missing, allow Heroku to continue if it's a Heroku issue
            if is_heroku:
                logger.warning("Proceeding despite Playwright module import failure on Heroku.")
                return True 
            return False # Fail for local setups if module is not there
        return True # Successfully completed setup for skip_browser_download case
    
    # The following code will only execute if PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD is NOT '1'
    logger.info("Proceeding with browser checks and potential installation (PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD is not '1').")

    try:
        import playwright
        from playwright.__version__ import __version__ as playwright_version
        logger.info(f"Playwright is installed (version: {playwright_version})")
    except ImportError:
        logger.error("Playwright module not found. This should have been installed by the Procfile.")
        if is_heroku:
            logger.warning("Continuing despite Playwright module not found on Heroku, assuming limited functionality.")
            return True
        return False
        
    browser_cache_dir = os.path.join(os.getcwd(), '.browser_cache')
    os.makedirs(browser_cache_dir, exist_ok=True)
    logger.info(f"Browser cache directory: {browser_cache_dir}")
    
    from playwright.sync_api import sync_playwright
    
    installed_browsers = []
    try:
        # This command lists installed browsers without trying to install them
        result = subprocess.run([sys.executable, "-m", "playwright", "install", "--dry-run"], capture_output=True, text=True, check=False)
        logger.info(f"Playwright install --dry-run output:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Playwright install --dry-run stderr:\n{result.stderr}")

        # A more reliable way to check if chromium is installed, without triggering auto-install
        # by checking the directory Playwright would use.
        # This is a bit of a heuristic as Playwright's internal paths can change.
        # A better method would be if Playwright offered a direct query API for installed browsers.
        playwright_browsers_path = Path(os.environ.get('PLAYWRIGHT_BROWSERS_PATH', Path.home() / ".cache/ms-playwright"))
        # Example path: /app/.playwright/chromium-1091/chrome-linux/chrome
        # Look for a directory like 'chromium-<version>'
        chromium_installed = any(d.name.startswith("chromium-") and (d / "chrome-linux" / "chrome").exists() for d in playwright_browsers_path.iterdir() if d.is_dir())
        
        if chromium_installed:
            logger.info(f"Chromium appears to be installed in {playwright_browsers_path}.")
            installed_browsers.append("chromium")
        else:
            logger.info(f"Chromium does not appear to be installed in {playwright_browsers_path}.")

    except Exception as e:
        logger.error(f"Error checking installed browsers with 'playwright install --dry-run': {e}")
        # Continue, as this check is informative.

    if "chromium" not in installed_browsers:
        logger.info("Chromium is not installed. Attempting to install Chromium...")
        try:
            install_command = [sys.executable, "-m", "playwright", "install", "chromium"]
            if is_heroku:
                # On Heroku, the buildpack might handle dependencies, but '--with-deps' can be problematic.
                # Given we are NOT skipping download here, an explicit install is intended.
                # However, avoid --with-deps if it causes root issues not solvable by PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
                pass # Consider if --with-deps is ever safe or needed when PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
            
            logger.info(f"Running command: {' '.join(install_command)}")
            process = subprocess.Popen(install_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            logger.info(f"Playwright install chromium stdout:\n{stdout.decode()}")
            if stderr:
                logger.error(f"Playwright install chromium stderr:\n{stderr.decode()}")
            
            if process.returncode != 0:
                raise Exception(f"'playwright install chromium' failed with return code {process.returncode}")
            logger.info("Successfully installed Chromium.")
            installed_browsers.append("chromium")
        except Exception as e:
            logger.error(f"Failed to install Chromium: {e}")
            if is_heroku:
                logger.warning("Chromium installation failed on Heroku. The app might run with limited functionality.")
                return True # Allow app to start with limited functionality
            return False # Fail for local non-Heroku setups
    else:
        logger.info("Chromium is already installed.")

    # Verify Chromium installation
    if "chromium" in installed_browsers:
        logger.info("Verifying Chromium installation...")
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
                        f"--user-data-dir={browser_cache_dir}"
                    ],
                    "ignore_default_args": ["--disable-extensions"],
                    "timeout": 60000  # Increased timeout
                }
                if platform.system() == "Linux" and os.environ.get("DISPLAY") is None:
                    logger.info("Linux environment with no DISPLAY detected, ensuring headless for verification.")
                    # browser_args["headless"] = True # Playwright's chromium is headless by default

                logger.info(f"Attempting to launch browser with args: {browser_args}")
                browser = p.chromium.launch(**browser_args)
                page = browser.new_page()
                page.goto("https://example.com")
                title = page.title()
                logger.info(f"Successfully loaded page with title: {title}")
                browser.close()
                logger.info("Chromium verification successful!")
        except Exception as e:
            logger.error(f"Chromium verification failed: {e}")
            # Log detailed environment for debugging
            logger.info("Environment variables during verification failure:")
            for key, value in os.environ.items():
                if "PLAYWRIGHT" in key or "CHROME" in key or "BROWSER" in key or "DISPLAY" in key:
                    logger.info(f"  {key}: {value}")
            # List contents of playwright browsers path
            try:
                pw_path = Path(os.environ.get('PLAYWRIGHT_BROWSERS_PATH', Path.home() / ".cache/ms-playwright"))
                if pw_path.exists():
                    logger.info(f"Contents of {pw_path} ({pw_path.resolve()}):")
                    for item in sorted(list(pw_path.rglob('*'))): # Recursive list for more detail
                        logger.info(f"  {item.relative_to(pw_path)} {'[DIR]' if item.is_dir() else ''}")
            except Exception as dir_error:
                logger.error(f"Error listing Playwright browser directory contents: {dir_error}")

            if is_heroku:
                logger.warning("Chromium verification failed on Heroku. The app will run with limited functionality.")
                return True # Allow app to start with limited functionality
            return False # Fail for local non-Heroku setups
    else:
        logger.warning("Chromium not in installed browsers list after attempting installation. Cannot verify.")
        if is_heroku:
            return True # Allow app to start with limited functionality
        return False

    logger.info("Playwright setup and browser verification completed.")
    return True

if __name__ == "__main__":
    success = setup_playwright()
    if not success:
        logger.error("Failed to set up Playwright properly")
        sys.exit(1)
    logger.info("Playwright setup completed successfully from __main__")
