import os
import json
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class ProxyManager:
    """Manages proxy endpoints with rotation and fallback strategies."""
    
    def __init__(self, config_path=None):
        """Initialize the proxy manager."""
        # Main proxy endpoint
        self.rotating_proxy_endpoint = None
        
        # Track proxy performance and rotation
        self.last_rotation_time = datetime.now()
        self.rotation_interval = 120  # Default: rotate every 2 minutes
        self.failed_attempts = 0
        self.max_failed_attempts = 3  # Rotate after 3 failures
        
        # Preferred proxy types in order (SOCKS5h is preferred for better anonymity)
        self.proxy_types = ['socks5h', 'socks5', 'http']
        
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
            
            # Check for proxy type preference in environment variables
            proxy_type = os.environ.get('PROXY_TYPE', '').lower()
            logger.info(f"Setting proxy configuration for Render environment. Preferred type: {proxy_type if proxy_type else 'not specified'}")
            
            # Try to load proxy from environment variables
            render_proxy = os.environ.get('ROTATING_PROXY_ENDPOINT')
            if render_proxy:
                # Keep the proxy URL as is, don't modify the protocol
                self.rotating_proxy_endpoint = render_proxy
                logger.info("Using proxy from ROTATING_PROXY_ENDPOINT environment variable on Render")
            else:
                # Determine best proxy protocol based on PROXY_TYPE env var
                if proxy_type == 'residential' or proxy_type == 'datacenter':
                    # For residential or datacenter proxies, prefer SOCKS5h for better anonymity
                    # The credentials are the same, just the protocol and port differ
                    self.rotating_proxy_endpoint = "socks5h://customer-pematthews41_5eo28-cc-us:Yitbos88++88@pr.oxylabs.io:9050"
                    logger.info("Using SOCKS5h proxy for residential/datacenter proxy on Render")
                else:
                    # Fallback to HTTP proxy if environment variable not set or type unknown
                    self.rotating_proxy_endpoint = "http://customer-pematthews41_5eo28-cc-us:Yitbos88++88@pr.oxylabs.io:7777"
                    logger.info("Using fallback hardcoded HTTP proxy configuration on Render")
            return
        
        # For non-Render environments, try multiple environment variable names for the proxy
        proxy_env_vars = ['ROTATING_PROXY_ENDPOINT', 'PROXY_URL', 'HTTP_PROXY', 'HTTPS_PROXY', 'SOCKS_PROXY']
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
                        
                        # Try to load proxy endpoints for different protocols
                        for proxy_type in self.proxy_types:
                            proxy_key = f"{proxy_type}_proxy_endpoint"
                            if proxy_key in config:
                                self.rotating_proxy_endpoint = config[proxy_key]
                                logger.info(f"Using {proxy_type.upper()} proxy from config file")
                                break
                        
                        # Fallback to generic rotating_proxy_endpoint if no specific protocol found
                        if not self.rotating_proxy_endpoint and 'rotating_proxy_endpoint' in config:
                            self.rotating_proxy_endpoint = config['rotating_proxy_endpoint']
                            logger.info(f"Using generic proxy endpoint from config file")
                        
                        # Load rotation settings if available
                        if 'rotation_interval' in config:
                            self.rotation_interval = config['rotation_interval']
                            logger.info(f"Set proxy rotation interval to {self.rotation_interval} seconds")
                        
                        if not self.rotating_proxy_endpoint:
                            logger.warning(f"No proxy endpoint found in {self.config_path}. Proxy functionality will be disabled.")
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
            # Mask sensitive parts of the proxy URL for logging
            masked_proxy = self._mask_proxy_url(self.rotating_proxy_endpoint)
            logger.info(f"ProxyManager: rotating_proxy_endpoint IS configured: {masked_proxy}")

    def _mask_proxy_url(self, proxy_url):
        """Mask sensitive parts of the proxy URL for logging."""
        if not proxy_url:
            return "None"
            
        try:
            if '://' in proxy_url and '@' in proxy_url:
                # Format: protocol://username:password@host:port
                protocol = proxy_url.split('://')[0]
                rest = proxy_url.split('://')[1]
                if '@' in rest:
                    credentials, host_part = rest.split('@', 1)
                    return f"{protocol}://*****@{host_part}"
            # If no credentials or unexpected format, just return the protocol and a placeholder
            if '://' in proxy_url:
                protocol = proxy_url.split('://')[0]
                return f"{protocol}://[masked]"
            return "[masked_proxy]"
        except Exception:
            return "[error_masking_proxy]"
    
    def _should_rotate_proxy(self):
        """Determine if the proxy should be rotated based on time or failures."""
        time_since_rotation = (datetime.now() - self.last_rotation_time).total_seconds()
        
        # Rotate if too much time has passed
        if time_since_rotation > self.rotation_interval:
            logger.info(f"Rotating proxy due to time interval ({time_since_rotation:.1f}s > {self.rotation_interval}s)")
            return True
            
        # Rotate if too many failures
        if self.failed_attempts >= self.max_failed_attempts:
            logger.info(f"Rotating proxy due to failures ({self.failed_attempts} >= {self.max_failed_attempts})")
            return True
            
        return False
    
    def get_proxy(self):
        """Get the configured rotating proxy endpoint with appropriate protocol prefix.
        Will automatically rotate the proxy if needed based on time interval or failures.
        """
        # Check if we're on Render for logging purposes
        is_render = 'RENDER' in os.environ
        
        # Check if we should rotate the proxy
        if self._should_rotate_proxy():
            self.load_config()
            self.last_rotation_time = datetime.now()
            self.failed_attempts = 0
            logger.info("Proxy rotated successfully")
        
        if not self.rotating_proxy_endpoint:
            logger.warning("get_proxy called but no rotating_proxy_endpoint is configured.")
            return None
            
        # Ensure the proxy URL has the appropriate protocol prefix
        proxy_url = self.rotating_proxy_endpoint
        if not any(proxy_url.startswith(protocol) for protocol in ['http://', 'https://', 'socks5://', 'socks5h://']):
            # Default to SOCKS5h if no protocol specified (best for anonymity)
            proxy_url = f'socks5h://{proxy_url}'
            logger.debug(f"Added socks5h:// prefix to proxy URL")
        
        # Log the protocol being used
        protocol = proxy_url.split('://')[0] if '://' in proxy_url else 'unknown'
        logger.info(f"Using proxy with protocol: {protocol}")
        
        # Log proxy usage on Render for debugging
        if is_render:
            # Mask sensitive parts but show the protocol and domain
            masked_proxy = self._mask_proxy_url(proxy_url)
            logger.info(f"Using proxy on Render: {masked_proxy}")
            
            # Add extra logging for SOCKS5 proxies
            if protocol in ['socks5', 'socks5h']:
                logger.info(f"SOCKS5 proxy detected. Using {protocol} protocol for better anonymity and CAPTCHA avoidance.")
                if protocol == 'socks5h':
                    logger.info("Using socks5h which resolves hostnames through the proxy for enhanced privacy.")
            elif protocol == 'http':
                logger.warning("Using HTTP proxy. Consider switching to SOCKS5h for better CAPTCHA avoidance.")
            
        return proxy_url
    
    def report_success(self, proxy_url, response_time_ms=None):
        """Report a successful request with the proxy."""
        # Reset failure counter on success
        self.failed_attempts = 0
        
        # Log success with response time if available
        if response_time_ms:
            logger.debug(f"Request succeeded with proxy. Response time: {response_time_ms}ms")
        else:
            logger.debug("Request succeeded with proxy.")
    
    def report_failure(self, proxy_url, is_block=False, error_details=None):
        """Report a failed request with the proxy."""
        # Increment failure counter
        self.failed_attempts += 1
        
        # Log the failure
        log_message = f"Request failed with proxy. Blocked: {is_block}. Failures: {self.failed_attempts}/{self.max_failed_attempts}."
        if error_details:
            log_message += f" Details: {error_details}"
        logger.warning(log_message)
        
        # If this is a CAPTCHA or block, we should rotate immediately
        if is_block:
            logger.warning("Block detected. Forcing proxy rotation.")
            # Reduce rotation interval temporarily to avoid further blocks
            self.rotation_interval = max(60, self.rotation_interval * 0.8)  # Reduce by 20% but not below 60 seconds
            self.load_config()
            self.last_rotation_time = datetime.now()
            self.failed_attempts = 0
            return True
        
        # If we've hit the failure threshold, trigger rotation
        if self.failed_attempts >= self.max_failed_attempts:
            logger.warning(f"Failure threshold reached ({self.failed_attempts}/{self.max_failed_attempts}). Rotating proxy.")
            self.load_config()
            self.last_rotation_time = datetime.now()
            self.failed_attempts = 0
            return True
            
        return False

# Create a global instance
proxy_manager = ProxyManager()
logger.info("Global proxy_manager instance created and configured.")
