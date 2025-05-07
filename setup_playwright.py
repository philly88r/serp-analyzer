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
    
    try:
        # Check if playwright is installed
        try:
            import playwright
            logger.info(f"Playwright version: {playwright.__version__}")
        except ImportError:
            logger.error("Playwright not installed. Please install it with: pip install playwright")
            return False
        
        # Get the expected browser path
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            executable_path = p.chromium._engine.executable_path
            logger.info(f"Expected Chromium executable path: {executable_path}")
            
            # Check if the browser executable exists
            if os.path.exists(executable_path):
                logger.info("Chromium executable already exists")
            else:
                logger.info("Chromium executable does not exist, installing...")
                
                # Try different installation methods
                methods = [
                    ["playwright", "install", "chromium"],
                    ["playwright", "install", "chromium", "--with-deps"],
                    ["python", "-m", "playwright", "install", "chromium"],
                    ["python", "-m", "playwright", "install", "chromium", "--with-deps"]
                ]
                
                success = False
                for method in methods:
                    try:
                        logger.info(f"Trying installation method: {' '.join(method)}")
                        result = subprocess.run(
                            method,
                            capture_output=True,
                            text=True
                        )
                        logger.info(f"Return code: {result.returncode}")
                        logger.info(f"Output: {result.stdout}")
                        if result.returncode == 0:
                            success = True
                            break
                    except Exception as e:
                        logger.error(f"Error with method {' '.join(method)}: {e}")
                
                if not success:
                    logger.error("All installation methods failed")
                    return False
        
        # Verify installation by actually launching a browser
        logger.info("Verifying Chromium installation...")
        with sync_playwright() as p:
            try:
                # Use specific launch options for Heroku
                browser_args = {}
                if is_heroku:
                    browser_args = {
                        "chromium_sandbox": False,
                        "args": [
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-dev-shm-usage"
                        ]
                    }
                
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
                return False
    except Exception as e:
        logger.error(f"Error setting up Playwright: {e}")
        return False

if __name__ == "__main__":
    success = setup_playwright()
    if not success:
        logger.error("Failed to set up Playwright properly")
        sys.exit(1)
    logger.info("Playwright setup completed successfully")
