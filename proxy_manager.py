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
        # Use absolute path to ensure we can find the config file
        if config_path is None:
            self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'proxy_config.json')
        else:
            self.config_path = config_path
        logger.info(f"Using proxy config path: {self.config_path}")
        self.load_config()
    
    def load_config(self):
        """Load rotating proxy endpoint from environment variable or configuration file."""
        # Try to load from environment variable first (for Heroku/production)
        env_proxy_endpoint = os.environ.get('ROTATING_PROXY_ENDPOINT')
        if env_proxy_endpoint:
            self.rotating_proxy_endpoint = env_proxy_endpoint
            logger.info(f"Loaded rotating proxy endpoint from environment variable.")
            return

        # Fallback to config file (for local development)
        try:
            logger.info(f"Attempting to load proxy config from: {self.config_path}")
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.rotating_proxy_endpoint = config.get('rotating_proxy_endpoint')
                    if self.rotating_proxy_endpoint:
                        logger.info(f"Loaded rotating proxy endpoint from {self.config_path}")
                    else:
                        logger.warning(f"'rotating_proxy_endpoint' not found in {self.config_path}. Proxy functionality will be disabled.")
            else:
                logger.warning(f"Proxy configuration file not found: {self.config_path}. Attempts to use a proxy will fail if ROTATING_PROXY_ENDPOINT env var is not set.")
        except FileNotFoundError:
            logger.warning(f"{self.config_path} not found. Attempts to use a proxy will fail if ROTATING_PROXY_ENDPOINT env var is not set.")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.config_path}. Proxy functionality might be affected.")
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading proxy config: {e}")

        if not self.rotating_proxy_endpoint:
            logger.warning("Rotating proxy endpoint is not configured. Attempts to use a proxy will fail.")

    def get_proxy(self):
        """Get the configured rotating proxy endpoint."""
        if not self.rotating_proxy_endpoint:
            logger.debug("get_proxy called but no rotating_proxy_endpoint is configured.")
            return None
        return self.rotating_proxy_endpoint
    
    def report_success(self, proxy_url, response_time_ms=None):
        """Report a successful request with the proxy."""
        logger.debug(f"Request succeeded with rotating proxy. Response time: {response_time_ms}ms")
    
    def report_failure(self, proxy_url, is_block=False, error_details=None):
        """Report a failed request with the proxy."""
        log_message = f"Request failed with rotating proxy. Blocked: {is_block}."
        if error_details:
            log_message += f" Details: {error_details}"
        logger.warning(log_message)

# Create a global instance
proxy_manager = ProxyManager()
