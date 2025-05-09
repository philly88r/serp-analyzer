import os
import json
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class ProxyManager:
    """Manages a single rotating proxy endpoint."""
    
    def __init__(self, config_path=None):
        """Initialize the proxy manager."""
        self.rotating_proxy_endpoint = None
        self.config_path = config_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'proxy_config.json')
        self.load_config()
    
    def load_config(self):
        """Load rotating proxy endpoint from configuration file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.rotating_proxy_endpoint = config.get('rotating_proxy_endpoint')
                    if self.rotating_proxy_endpoint:
                        logger.info(f"Loaded rotating proxy endpoint: {self.rotating_proxy_endpoint}")
                    else:
                        logger.warning(f"'rotating_proxy_endpoint' not found in {self.config_path}")
            else:
                logger.warning(f"Proxy configuration file not found: {self.config_path}. Please create it with your rotating_proxy_endpoint.")
        except Exception as e:
            logger.error(f"Error loading proxy configuration: {str(e)}")
            self.rotating_proxy_endpoint = None # Ensure it's None if loading fails

    def get_proxy(self):
        """Get the configured rotating proxy endpoint."""
        if not self.rotating_proxy_endpoint:
            logger.warning("Rotating proxy endpoint is not configured. Attempts to use a proxy will fail.")
            # Optionally, re-attempt loading config if it was initially missing
            # self.load_config()
            # if not self.rotating_proxy_endpoint:
            #     return None
        return self.rotating_proxy_endpoint
    
    def report_success(self, proxy_url, response_time_ms=None):
        """Report a successful request with the proxy."""
        # For a single rotating endpoint, we might just log success.
        # Complex tracking is handled by the proxy service itself.
        logger.debug(f"Request successful using proxy: {proxy_url}")
    
    def report_failure(self, proxy_url, is_block=False):
        """Report a failed request with the proxy."""
        # For a single rotating endpoint, we might just log failure.
        # The external service handles its own rotation and health checks.
        log_message = f"Request failed using proxy: {proxy_url}"
        if is_block:
            log_message += " (Detected as block)"
        logger.warning(log_message)

# Create a global instance
proxy_manager = ProxyManager()
