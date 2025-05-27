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
                proxy_username = os.environ.get('PROXY_USERNAME', 'customer-pematthews41_5eo28-cc-us')
                proxy_password = os.environ.get('PROXY_PASSWORD', 'Yitbos88++88')
                proxy_host = os.environ.get('PROXY_HOST', 'pr.oxylabs.io')
                
                # Mask credentials for logging
                masked_username = proxy_username[:5] + '...' if len(proxy_username) > 5 else proxy_username
                masked_password = '****'
                
                if proxy_type == 'socks5h' or proxy_type == 'residential' or proxy_type == 'datacenter':
                    # For residential or datacenter proxies, prefer SOCKS5h for better anonymity
                    proxy_port = os.environ.get('SOCKS5_PORT', '9050')
                    self.rotating_proxy_endpoint = f"socks5h://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
                    logger.info(f"Using SOCKS5h proxy for {proxy_type} proxy on Render with host: {proxy_host}:{proxy_port}")
                elif proxy_type == 'socks5':
                    # Standard SOCKS5 (without hostname resolution through the proxy)
                    proxy_port = os.environ.get('SOCKS5_PORT', '9050')
                    self.rotating_proxy_endpoint = f"socks5://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
                    logger.info(f"Using SOCKS5 proxy on Render with host: {proxy_host}:{proxy_port}")
                elif proxy_type == 'https':
                    # HTTPS proxy
                    proxy_port = os.environ.get('HTTPS_PORT', '7778')
                    self.rotating_proxy_endpoint = f"https://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
                    logger.info(f"Using HTTPS proxy on Render with host: {proxy_host}:{proxy_port}")
                else:
                    # Fallback to HTTP proxy
                    proxy_port = os.environ.get('HTTP_PORT', '7777')
                    self.rotating_proxy_endpoint = f"http://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
                    logger.info(f"Using HTTP proxy on Render with host: {proxy_host}:{proxy_port}")
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
        """Determine if the proxy should be rotated based on time, failures, or other factors.
        
        Returns:
            bool: True if the proxy should be rotated, False otherwise
        """
        time_since_rotation = (datetime.now() - self.last_rotation_time).total_seconds()
        
        # Get environment variables for rotation strategy
        force_rotation = os.environ.get('FORCE_PROXY_ROTATION', 'false').lower() == 'true'
        captcha_detected = os.environ.get('CAPTCHA_DETECTED', 'false').lower() == 'true'
        aggressive_rotation = os.environ.get('AGGRESSIVE_PROXY_ROTATION', 'false').lower() == 'true'
        
        # Force immediate rotation if requested
        if force_rotation:
            logger.info("Forcing proxy rotation due to FORCE_PROXY_ROTATION environment variable")
            return True
        
        # Rotate if CAPTCHA was detected
        if captcha_detected:
            logger.info("Rotating proxy due to CAPTCHA detection")
            # Reset the environment variable
            os.environ['CAPTCHA_DETECTED'] = 'false'
            return True
        
        # Rotate if too much time has passed
        if time_since_rotation > self.rotation_interval:
            logger.info(f"Rotating proxy due to time interval ({time_since_rotation:.1f}s > {self.rotation_interval}s)")
            return True
            
        # Rotate if too many failures
        if self.failed_attempts >= self.max_failed_attempts:
            logger.info(f"Rotating proxy due to failures ({self.failed_attempts} >= {self.max_failed_attempts})")
            return True
        
        # Aggressive rotation strategy for high-risk scenarios
        if aggressive_rotation:
            # In aggressive mode, rotate more frequently
            reduced_interval = self.rotation_interval / 2
            if time_since_rotation > reduced_interval:
                logger.info(f"Rotating proxy due to aggressive rotation strategy ({time_since_rotation:.1f}s > {reduced_interval:.1f}s)")
                return True
            
            # Also rotate after fewer failures in aggressive mode
            reduced_failures = max(1, self.max_failed_attempts // 2)
            if self.failed_attempts >= reduced_failures:
                logger.info(f"Rotating proxy due to aggressive rotation strategy failures ({self.failed_attempts} >= {reduced_failures})")
                return True
        
        return False
    
    def _check_proxy_health(self, proxy_url):
        """Perform a basic health check on the proxy by making a test request.
        
        Args:
            proxy_url: The full proxy URL to check
            
        Returns:
            bool: True if the proxy is working, False otherwise
        """
        import aiohttp
        import asyncio
        from aiohttp_socks import ProxyConnector
        import socket
        
        # Define a simple async function to test the proxy
        async def test_proxy():
            try:
                # Use a test URL that's likely to be accessible and lightweight
                test_url = "https://www.cloudflare.com/cdn-cgi/trace"
                timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
                
                # Handle different proxy types
                if proxy_url.startswith(('socks5://', 'socks5h://')):
                    try:
                        connector = ProxyConnector.from_url(proxy_url)
                        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                            async with session.get(test_url) as response:
                                return response.status == 200
                    except ImportError:
                        logger.error("aiohttp_socks package not installed. Cannot test SOCKS5 proxy health.")
                        return True  # Assume it's working if we can't test
                    except Exception as e:
                        logger.warning(f"SOCKS5 proxy health check failed: {str(e)}")
                        return False
                else:
                    # For HTTP/HTTPS proxies
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(test_url, proxy=proxy_url) as response:
                            return response.status == 200
            except (aiohttp.ClientError, socket.gaierror, asyncio.TimeoutError, OSError) as e:
                logger.warning(f"Proxy health check failed: {str(e)}")
                return False
            except Exception as e:
                logger.error(f"Unexpected error in proxy health check: {str(e)}")
                return False
        
        # Run the async test function
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an existing event loop, create a new one
                    loop = asyncio.new_event_loop()
                    result = loop.run_until_complete(test_proxy())
                    loop.close()
                else:
                    result = loop.run_until_complete(test_proxy())
            except RuntimeError:
                # No event loop exists, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(test_proxy())
                loop.close()
                
            return result
        except Exception as e:
            logger.error(f"Failed to run proxy health check: {str(e)}")
            return True  # Assume it's working if we can't test
    
    def get_proxy(self):
        """Get the configured rotating proxy endpoint with appropriate protocol prefix.
        Will automatically rotate the proxy if needed based on time interval or failures.
        Includes health check and fallback mechanisms for more reliable proxy usage.
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
        
        # Get proxy type preference from environment (default to SOCKS5h)
        proxy_type_pref = os.environ.get('PROXY_TYPE', 'socks5h').lower()
        
        # Ensure the proxy URL has the appropriate protocol prefix
        proxy_url = self.rotating_proxy_endpoint
        
        # If no protocol specified, use the preferred type from environment
        if not any(proxy_url.startswith(protocol) for protocol in ['http://', 'https://', 'socks5://', 'socks5h://']):
            proxy_url = f'{proxy_type_pref}://{proxy_url}'
            logger.debug(f"Added {proxy_type_pref}:// prefix to proxy URL based on environment preference")
        
        # Log the protocol being used
        protocol = proxy_url.split('://')[0] if '://' in proxy_url else 'unknown'
        
        # Perform a basic health check on the proxy if enabled
        if os.environ.get('PROXY_HEALTH_CHECK', 'false').lower() == 'true':
            if not self._check_proxy_health(proxy_url):
                logger.warning(f"Proxy health check failed for {protocol} proxy. Incrementing failure count.")
                self.failed_attempts += 1
                
                # If we've hit the failure threshold, force an immediate rotation
                if self.failed_attempts >= self.max_failed_attempts:
                    logger.info("Forcing immediate proxy rotation due to health check failure")
                    self.load_config()
                    self.last_rotation_time = datetime.now()
                    self.failed_attempts = 0
                    
                    # Try again with the new proxy
                    return self.get_proxy()
        
        # Log proxy usage with appropriate masking
        masked_proxy = self._mask_proxy_url(proxy_url)
        logger.info(f"Using proxy with protocol: {protocol}")
        
        # Add extra logging for different proxy types
        if protocol in ['socks5', 'socks5h']:
            logger.info(f"SOCKS5 proxy detected. Using {protocol} protocol for better anonymity and CAPTCHA avoidance.")
            if protocol == 'socks5h':
                logger.info("Using socks5h which resolves hostnames through the proxy for enhanced privacy.")
        elif protocol == 'http':
            logger.warning("Using HTTP proxy. Consider switching to SOCKS5h for better CAPTCHA avoidance.")
        
        # Log additional details on Render for debugging
        if is_render:
            logger.info(f"Using proxy on Render: {masked_proxy}")
            
        return proxy_url
    
    def report_success(self, proxy_url, response_time_ms=None, country_code=None, region=None):
        """Report a successful request with the proxy and update performance metrics.
        
        Args:
            proxy_url: The proxy URL that succeeded
            response_time_ms: Optional response time in milliseconds
            country_code: Optional country code where the proxy appears to be located
            region: Optional region information
        """
        # Reset failure counter on success
        self.failed_attempts = 0
        
        # Disable aggressive rotation mode if it was enabled
        if os.environ.get('AGGRESSIVE_PROXY_ROTATION', 'false').lower() == 'true':
            logger.info("Disabling aggressive proxy rotation due to successful request")
            os.environ['AGGRESSIVE_PROXY_ROTATION'] = 'false'
        
        # Reset force rotation flag if it was set
        if os.environ.get('FORCE_PROXY_ROTATION', 'false').lower() == 'true':
            os.environ['FORCE_PROXY_ROTATION'] = 'false'
        
        # Create a masked version of the proxy URL for logging
        masked_proxy = self._mask_proxy_url(proxy_url)
        
        # Log success with response time if available
        if response_time_ms:
            logger.info(f"Request succeeded with proxy {masked_proxy}. Response time: {response_time_ms}ms")
        else:
            logger.info(f"Request succeeded with proxy {masked_proxy}.")
            
        # Update the database with success metrics if available
        try:
            from database import update_proxy_status
            update_proxy_status(proxy_url, success=True, response_time_ms=response_time_ms,
                              country_code=country_code, region=region)
        except ImportError:
            logger.debug("Could not update database with proxy success - database module not available")
        except Exception as e:
            logger.error(f"Error updating database with proxy success: {str(e)}")
            
        # If we've had several consecutive successes, we can gradually increase the rotation interval
        # to reduce unnecessary rotations
        if hasattr(self, 'consecutive_successes'):
            self.consecutive_successes += 1
        else:
            self.consecutive_successes = 1
            
        # After 5 consecutive successes, increase rotation interval slightly
        if self.consecutive_successes >= 5 and self.rotation_interval < 3600:  # Cap at 1 hour
            self.rotation_interval = min(3600, self.rotation_interval * 1.2)  # Increase by 20%
            logger.info(f"Increased rotation interval to {self.rotation_interval}s due to consecutive successes")
    
    def report_failure(self, proxy_url, is_block=False, error_details=None, captcha_detected=False):
        """Report a proxy failure to increment the failure counter and track failure types.
        
        Args:
            proxy_url: The proxy URL that failed
            is_block: Whether this failure was due to being blocked (403/429)
            error_details: Optional details about the error
            captcha_detected: Whether a CAPTCHA was detected during this request
        """
        self.failed_attempts += 1
        
        # Create a masked version of the proxy URL for logging
        masked_proxy = self._mask_proxy_url(proxy_url)
        
        # Log the failure with appropriate details
        logger.warning(f"Proxy failure reported for {masked_proxy}. Total failures: {self.failed_attempts}/{self.max_failed_attempts}")
        
        # Handle different failure types
        if captcha_detected:
            logger.warning("CAPTCHA detected during request. Setting CAPTCHA_DETECTED flag.")
            os.environ['CAPTCHA_DETECTED'] = 'true'
            # CAPTCHA detection is serious - force rotation soon
            self.failed_attempts = max(self.failed_attempts, self.max_failed_attempts - 1)
            
            # Track CAPTCHA occurrences in database if available
            try:
                from database import update_proxy_status
                update_proxy_status(proxy_url, success=False, response_time_ms=None, 
                                  error_type='captcha')
            except ImportError:
                logger.debug("Could not update database with CAPTCHA occurrence - database module not available")
            except Exception as e:
                logger.error(f"Error updating database with CAPTCHA occurrence: {str(e)}")
        
        elif is_block:
            logger.warning(f"Proxy {masked_proxy} appears to be blocked (403/429 status). Consider rotating.")
            # Force more aggressive rotation for blocks
            self.failed_attempts = max(self.failed_attempts, self.max_failed_attempts - 1)
            
            # Track block occurrences in database if available
            try:
                from database import update_proxy_status
                update_proxy_status(proxy_url, success=False, response_time_ms=None, 
                                  error_type='blocked')
            except ImportError:
                logger.debug("Could not update database with block occurrence - database module not available")
            except Exception as e:
                logger.error(f"Error updating database with block occurrence: {str(e)}")
        
        # Log error details if provided
        if error_details:
            logger.warning(f"Proxy error details: {error_details}")
        
        # Check if we should enable aggressive rotation mode
        if self.failed_attempts >= self.max_failed_attempts // 2:
            logger.info("Enabling aggressive proxy rotation due to multiple failures")
            os.environ['AGGRESSIVE_PROXY_ROTATION'] = 'true'
            
        # If we've hit the max failures, force an immediate rotation on next get_proxy call
        if self.failed_attempts >= self.max_failed_attempts:
            logger.warning(f"Failure threshold reached ({self.failed_attempts}/{self.max_failed_attempts}). Forcing rotation on next request.")
            os.environ['FORCE_PROXY_ROTATION'] = 'true'
            return True
            
        return False

# Create a global instance
proxy_manager = ProxyManager()
logger.info("Global proxy_manager instance created and configured.")
