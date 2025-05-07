import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_playwright():
    """
    Ensure Playwright and Chromium are properly installed and configured.
    This script is meant to be run before starting the web server on Heroku.
    """
    logger.info("Setting up Playwright and Chromium...")
    
    try:
        # Install Playwright browsers
        logger.info("Installing Chromium browser...")
        result = subprocess.run(
            ["playwright", "install", "chromium", "--with-deps"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Playwright installation output: {result.stdout}")
        
        # Verify installation
        logger.info("Verifying Chromium installation...")
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto("https://example.com")
                title = page.title()
                logger.info(f"Successfully loaded page with title: {title}")
                browser.close()
                logger.info("Chromium is working correctly!")
            except Exception as e:
                logger.error(f"Error testing Chromium: {e}")
                raise
        
        return True
    except Exception as e:
        logger.error(f"Error setting up Playwright: {e}")
        return False

if __name__ == "__main__":
    success = setup_playwright()
    if not success:
        logger.error("Failed to set up Playwright properly")
        sys.exit(1)
    logger.info("Playwright setup completed successfully")
