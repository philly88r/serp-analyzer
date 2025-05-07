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
    logger.info(f"Setting up Playwright and Chromium on {platform.system()}...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    
    # Check if we're running on Heroku
    is_heroku = 'DYNO' in os.environ
    logger.info(f"Running on Heroku: {is_heroku}")
    
    # Check if browser download is skipped
    skip_browser_download = os.environ.get('PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD', '') == '1'
    logger.info(f"Skip browser download: {skip_browser_download}")
    
    # Set environment variables for Playwright on Heroku
    if is_heroku:
        # Set the path where Playwright browsers will be installed
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/app/.playwright'
        logger.info(f"Set PLAYWRIGHT_BROWSERS_PATH to {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")
        
        # Disable sandbox for Chromium on Heroku
        os.environ['PLAYWRIGHT_CHROMIUM_ARGS'] = '--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage'
        logger.info(f"Set PLAYWRIGHT_CHROMIUM_ARGS to {os.environ.get('PLAYWRIGHT_CHROMIUM_ARGS')}")
        
        # If we're skipping browser download, set this flag to avoid errors
        if skip_browser_download:
            os.environ['PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '1'
            logger.info("Browser download is skipped. The app will run in limited functionality mode.")
    
    # Check for PLAYWRIGHT_BUILDPACK_BROWSERS environment variable
    playwright_browsers = os.environ.get('PLAYWRIGHT_BUILDPACK_BROWSERS', '')
    logger.info(f"PLAYWRIGHT_BUILDPACK_BROWSERS: {playwright_browsers}")
    
    try:
        # Check if playwright is installed
        try:
            import playwright
            from playwright.__version__ import __version__ as playwright_version
            logger.info(f"Playwright is installed (version: {playwright_version})")
        except ImportError:
            logger.warning("Playwright not installed. Attempting to install it now...")
            try:
                # Try to install playwright
                logger.info("Installing playwright via pip...")
                subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
                
                # Try importing again
                import playwright
                from playwright.__version__ import __version__ as playwright_version
                logger.info(f"Successfully installed Playwright (version: {playwright_version})")
            except Exception as e:
                logger.error(f"Failed to install Playwright: {e}")
                # Continue anyway to allow the app to start with limited functionality
                if is_heroku:
                    logger.warning("Continuing despite Playwright installation failure on Heroku")
                    return True
                return False
        
        # Create a directory for browser cache if it doesn't exist
        browser_cache_dir = os.path.join(os.getcwd(), '.browser_cache')
        os.makedirs(browser_cache_dir, exist_ok=True)
        logger.info(f"Browser cache directory: {browser_cache_dir}")
        
        # Get the expected browser path
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                executable_path = p.chromium._engine.executable_path
                logger.info(f"Expected Chromium executable path: {executable_path}")
                
                # Check if the browser executable exists
                if os.path.exists(executable_path):
                    logger.info("Chromium executable already exists")
                else:
                    logger.info("Chromium executable does not exist, installing...")
                    
                    # Check for Heroku-specific paths
                    if is_heroku:
                        # Check if browser is installed by the buildpack
                        buildpack_browser_path = "/app/.playwright/chromium-"
                        potential_paths = list(Path("/app/.playwright").glob("chromium-*"))
                        if potential_paths:
                            logger.info(f"Found potential browser paths from buildpack: {potential_paths}")
                    
                    # Try different installation methods
                    methods = [
                        [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
                        [sys.executable, "-m", "playwright", "install", "chromium"],
                        ["playwright", "install", "chromium", "--with-deps"],
                        ["playwright", "install", "chromium"]
                    ]
                    
                    success = False
                    for method in methods:
                        try:
                            logger.info(f"Trying installation method: {' '.join(method)}")
                            result = subprocess.run(
                                method,
                                capture_output=True,
                                text=True,
                                env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=browser_cache_dir)
                            )
                            logger.info(f"Return code: {result.returncode}")
                            logger.info(f"Output: {result.stdout}")
                            logger.info(f"Error: {result.stderr}")
                            if result.returncode == 0:
                                success = True
                                break
                        except Exception as e:
                            logger.error(f"Error with method {' '.join(method)}: {e}")
                    
                    if not success:
                        logger.error("All installation methods failed")
                        
                        # Check if we're on Heroku and try to use the buildpack browser
                        if is_heroku and 'chromium' in playwright_browsers.lower():
                            logger.info("Attempting to use browser installed by buildpack...")
                            # The browser might still be available through the buildpack
                            success = True
                        else:
                            return False
            except Exception as e:
                logger.error(f"Error determining browser path: {e}")
                # Continue anyway, as the browser might be available through other means
        
        # If we're skipping browser download, skip verification
        if skip_browser_download:
            logger.info("Skipping browser verification since PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD is set")
            logger.info("The app will run in limited functionality mode without browser automation")
            return True
            
        # Verify installation by actually launching a browser
        logger.info("Verifying Chromium installation...")
        try:
            with sync_playwright() as p:
                try:
                    # Use specific launch options for Heroku
                    browser_args = {}
                    if is_heroku:
                        browser_args = {
                            "chromium_sandbox": False,
                            "executable_path": None,  # Let Playwright find the executable
                            "args": [
                                "--no-sandbox",
                                "--disable-setuid-sandbox",
                                "--disable-dev-shm-usage",
                                "--disable-gpu",
                                "--single-process",
                                f"--user-data-dir={browser_cache_dir}"
                            ],
                            "ignore_default_args": ["--disable-extensions"],
                            "timeout": 30000  # Increase timeout to 30 seconds
                        }
                        
                        # Log all environment variables for debugging
                        logger.info("Environment variables:")
                        for key, value in os.environ.items():
                            if "PLAYWRIGHT" in key or "CHROME" in key or "BROWSER" in key:
                                logger.info(f"  {key}: {value}")
                    
                    # Try to launch the browser
                    logger.info(f"Launching browser with args: {browser_args}")
                    browser = p.chromium.launch(**browser_args)
                    page = browser.new_page()
                    page.goto("https://example.com")
                    title = page.title()
                    logger.info(f"Successfully loaded page with title: {title}")
                    browser.close()
                    logger.info("Chromium is working correctly!")
                    return True
                except Exception as e:
                    logger.error(f"Error testing Chromium: {e}")
                    raise e
        except Exception as e:
            logger.error(f"Failed to verify browser installation: {e}")
            
            if is_heroku:
                logger.warning("Browser verification failed on Heroku, but continuing anyway")
                logger.warning("The app will run with limited functionality")
                return True
            return False
    except Exception as e:
        logger.error(f"Error testing Chromium: {e}")
        
        # If we're on Heroku, we'll log more details but still return True
        # as the app might still work with other features
        if is_heroku:
            logger.warning("Browser test failed on Heroku, but continuing anyway")
            logger.warning("The app will run with limited functionality")
            
            # List all directories in the Playwright browsers path
            try:
                playwright_path = Path("/app/.playwright")
                if playwright_path.exists():
                    logger.info(f"Contents of {playwright_path}:")
                    for item in playwright_path.iterdir():
                        logger.info(f"  {item}")
                        if item.is_dir() and item.name.startswith("chromium-"):
                            logger.info(f"  Contents of {item}:")
                            for subitem in item.iterdir():
                                logger.info(f"    {subitem}")
            except Exception as dir_error:
                logger.error(f"Error listing Playwright directories: {dir_error}")
            
            # Return True anyway to allow the app to start
            return True
        return False
    except Exception as e:
        logger.error(f"Error setting up Playwright: {e}")
        
        # If we're on Heroku, we'll log the error but still return True
        # to allow the app to start with limited functionality
        if is_heroku:
            logger.warning("Setup failed on Heroku, but continuing anyway")
            logger.warning("The app will run with limited functionality")
            return True
        return False

if __name__ == "__main__":
    success = setup_playwright()
    if not success:
        logger.error("Failed to set up Playwright properly")
        sys.exit(1)
    logger.info("Playwright setup completed successfully")
