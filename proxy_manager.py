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
        logger.info(f"ProxyManager initialized. Using proxy config path: {self.config_path}")
        self.load_config()
    
    def load_config(self):
        """Load rotating proxy endpoint from environment variable or configuration file."""
        # Check if we're running on Render
        is_render = 'RENDER' in os.environ
        if is_render:
            logger.info("Running on Render environment")
            # Log all environment variables on Render (excluding sensitive ones)
            logger.info("Environment variables on Render:")
            for key in sorted(os.environ.keys()):
                value = os.environ[key]
                if any(sensitive in key.lower() for sensitive in ['key', 'secret', 'password', 'token', 'proxy']):
                    # Show just the first few characters of sensitive values
                    if value and len(value) > 5:
                        value = value[:5] + '...' 
                    logger.info(f"Render env (sensitive): {key}={value}")
                else:
                    logger.info(f"Render env: {key}={value}")
            
            # On Render, always use our known working proxy configuration
            logger.info("Setting hardcoded proxy configuration for Render environment")
            self.rotating_proxy_endpoint = "http://customer-pematthews41_5eo28-cc-us:Yitbos88++88@pr.oxylabs.io:7777"
            logger.info("Successfully set hardcoded proxy configuration on Render")
            return
        
        # For non-Render environments, try multiple environment variable names for the proxy
        proxy_env_vars = ['ROTATING_PROXY_ENDPOINT', 'PROXY_URL', 'HTTP_PROXY', 'HTTPS_PROXY']
        for env_var in proxy_env_vars:
            env_proxy_endpoint = os.environ.get(env_var)
            if env_proxy_endpoint:
                self.rotating_proxy_endpoint = env_proxy_endpoint
                logger.info(f"Loaded rotating proxy endpoint from environment variable: {env_var}")
                break
        
        # If we found a proxy in env vars, we can return early
        if self.rotating_proxy_endpoint:
            return

        # Fallback to config file (for local development) if not loaded from env var
        if not self.rotating_proxy_endpoint:
            try:
                logger.info(f"Attempting to load proxy config from file: {self.config_path}")
                if os.path.exists(self.config_path):
                    logger.info(f"Config file {self.config_path} exists.")
                    with open(self.config_path, 'r') as f:
                        config = json.load(f)
                        logger.debug(f"Config file content: {config}")
                        self.rotating_proxy_endpoint = config.get('rotating_proxy_endpoint')
                        if self.rotating_proxy_endpoint:
                            logger.info(f"Successfully loaded rotating_proxy_endpoint from {self.config_path}")
                        else:
                            logger.warning(f"'rotating_proxy_endpoint' key not found in {self.config_path}. Proxy functionality will be disabled if not set by env var.")
                else:
                    logger.warning(f"Proxy configuration file NOT FOUND: {self.config_path}. Proxy will be disabled if ROTATING_PROXY_ENDPOINT env var is not set.")
            except FileNotFoundError: # Should be caught by os.path.exists, but good to have defense
                logger.warning(f"Proxy configuration file explicitly NOT FOUND (FileNotFoundError): {self.config_path}. Proxy will be disabled if ROTATING_PROXY_ENDPOINT env var is not set.")
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON from {self.config_path}. Proxy functionality might be affected.")
            except Exception as e:
                logger.error(f"An unexpected error occurred while loading proxy config from file: {e}")

        if not self.rotating_proxy_endpoint:
            logger.warning("ProxyManager: rotating_proxy_endpoint is NOT configured after load_config. Proxy will be unavailable.")
        else:
            logger.info(f"ProxyManager: rotating_proxy_endpoint IS configured: {self.rotating_proxy_endpoint[:30]}...") # Log a snippet

    def get_proxy(self):
        """Get the configured rotating proxy endpoint with http:// prefix if needed."""
        # Check if we're on Render for logging purposes
        is_render = 'RENDER' in os.environ
        
        if not self.rotating_proxy_endpoint:
            logger.warning("get_proxy called but no rotating_proxy_endpoint is configured.")
            return None
            
        # Ensure the proxy URL has the http:// prefix
        proxy_url = self.rotating_proxy_endpoint
        if not proxy_url.startswith('http://') and not proxy_url.startswith('https://') and not proxy_url.startswith('socks5://'):
            proxy_url = f'http://{proxy_url}'
            logger.debug(f"Added http:// prefix to proxy URL: {proxy_url}")
        
        # Log proxy usage on Render for debugging
        if is_render:
            logger.info(f"Using proxy on Render: {proxy_url[:10]}...")
            
        return proxy_url
    
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
logger.info("Global proxy_manager instance created and configured.")
