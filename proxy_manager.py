import os
import json
import random
import time
import logging
import requests
from datetime import datetime, timedelta
from database import get_best_performing_proxies, update_proxy_status

# Set up logging
logger = logging.getLogger(__name__)

class ProxyManager:
    """Enhanced proxy management system with health monitoring and geographic distribution."""
    
    def __init__(self, config_path=None):
        """Initialize the proxy manager."""
        self.proxies = []
        self.current_proxy = None
        self.last_rotation_time = datetime.now()
        self.rotation_frequency = 60  # Default rotation frequency in seconds (1 minute)
        self.min_rotation_frequency = 60  # Minimum rotation frequency (1 minute)
        self.max_rotation_frequency = 300  # Maximum rotation frequency (5 minutes)
        self.block_count = 0
        self.max_block_count = 5  # After this many blocks, force proxy refresh
        self.config_path = config_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'proxy_config.json')
        self.load_proxies()
    
    def load_proxies(self):
        """Load proxies from configuration file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.proxies = config.get('proxies', [])
                    self.rotation_frequency = config.get('rotation_frequency', 60)
                    self.min_rotation_frequency = config.get('min_rotation_frequency', 60)
                    self.max_rotation_frequency = config.get('max_rotation_frequency', 300)
                    logger.info(f"Loaded {len(self.proxies)} proxies from configuration")
            else:
                logger.warning(f"Proxy configuration file not found: {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading proxy configuration: {str(e)}")
    
    def save_proxies(self):
        """Save proxies to configuration file."""
        try:
            config = {
                'proxies': self.proxies,
                'rotation_frequency': self.rotation_frequency,
                'min_rotation_frequency': self.min_rotation_frequency,
                'max_rotation_frequency': self.max_rotation_frequency
            }
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Saved {len(self.proxies)} proxies to configuration")
        except Exception as e:
            logger.error(f"Error saving proxy configuration: {str(e)}")
    
    def add_proxy(self, proxy_url, country_code=None, region=None):
        """Add a proxy to the list."""
        if proxy_url not in [p['url'] for p in self.proxies]:
            self.proxies.append({
                'url': proxy_url,
                'country_code': country_code,
                'region': region,
                'last_used': None,
                'success_count': 0,
                'failure_count': 0
            })
            self.save_proxies()
            logger.info(f"Added proxy: {proxy_url}")
    
    def remove_proxy(self, proxy_url):
        """Remove a proxy from the list."""
        self.proxies = [p for p in self.proxies if p['url'] != proxy_url]
        self.save_proxies()
        logger.info(f"Removed proxy: {proxy_url}")
    
    def get_proxy(self, country_code=None, region=None):
        """Get a proxy from the list, optionally filtered by country or region."""
        # Check if it's time to rotate
        now = datetime.now()
        time_since_last_rotation = (now - self.last_rotation_time).total_seconds()
        
        # Force rotation if enough time has passed or if we've detected blocks
        if (time_since_last_rotation >= self.rotation_frequency or 
            self.block_count >= self.max_block_count or 
            self.current_proxy is None):
            
            # Try to get the best performing proxies from the database
            best_proxies = get_best_performing_proxies(limit=5)
            
            if best_proxies and random.random() < 0.7:  # 70% chance to use a best-performing proxy
                # Choose one of the best proxies
                best_proxy = random.choice(best_proxies)
                proxy_url = best_proxy['proxy_url']
                
                # Find this proxy in our list or add it
                proxy = next((p for p in self.proxies if p['url'] == proxy_url), None)
                if not proxy:
                    self.add_proxy(
                        proxy_url, 
                        country_code=best_proxy.get('country_code'),
                        region=best_proxy.get('region')
                    )
                    proxy = next((p for p in self.proxies if p['url'] == proxy_url), None)
                
                self.current_proxy = proxy
            else:
                # Filter proxies by country or region if specified
                filtered_proxies = self.proxies
                if country_code:
                    filtered_proxies = [p for p in filtered_proxies if p.get('country_code') == country_code]
                if region and not filtered_proxies:  # If no country match, try region
                    filtered_proxies = [p for p in self.proxies if p.get('region') == region]
                
                # If no matching proxies, use all proxies
                if not filtered_proxies:
                    filtered_proxies = self.proxies
                
                # If we have proxies, choose one randomly
                if filtered_proxies:
                    # Weighted random selection based on success rate
                    weights = []
                    for proxy in filtered_proxies:
                        total = proxy.get('success_count', 0) + proxy.get('failure_count', 0)
                        if total == 0:
                            weights.append(1.0)  # New proxy gets a fair chance
                        else:
                            success_rate = proxy.get('success_count', 0) / total
                            weights.append(max(0.1, success_rate))  # Minimum weight of 0.1
                    
                    # Choose a proxy based on weights
                    self.current_proxy = random.choices(filtered_proxies, weights=weights, k=1)[0]
                else:
                    logger.warning("No proxies available")
                    self.current_proxy = None
            
            # Reset block count and update rotation time
            self.block_count = 0
            self.last_rotation_time = now
            
            if self.current_proxy:
                self.current_proxy['last_used'] = now.isoformat()
                logger.info(f"Rotated to proxy: {self.current_proxy['url']}")
        
        return self.current_proxy
    
    def report_success(self, proxy_url, response_time_ms=None):
        """Report a successful request with a proxy."""
        for proxy in self.proxies:
            if proxy['url'] == proxy_url:
                proxy['success_count'] = proxy.get('success_count', 0) + 1
                self.save_proxies()
                
                # Update database
                update_proxy_status(
                    proxy_url=proxy_url,
                    success=True,
                    response_time_ms=response_time_ms,
                    country_code=proxy.get('country_code'),
                    region=proxy.get('region')
                )
                
                break
    
    def report_failure(self, proxy_url, is_block=False):
        """Report a failed request with a proxy."""
        for proxy in self.proxies:
            if proxy['url'] == proxy_url:
                proxy['failure_count'] = proxy.get('failure_count', 0) + 1
                self.save_proxies()
                
                # Update database
                update_proxy_status(
                    proxy_url=proxy_url,
                    success=False,
                    country_code=proxy.get('country_code'),
                    region=proxy.get('region')
                )
                
                break
        
        if is_block:
            self.block_count += 1
            
            # Adjust rotation frequency based on blocks
            if self.block_count > 2:
                # Decrease rotation frequency (rotate more often)
                self.rotation_frequency = max(
                    self.min_rotation_frequency,
                    self.rotation_frequency * 0.8  # 20% decrease
                )
                logger.info(f"Decreased rotation frequency to {self.rotation_frequency:.1f}s due to blocks")
            
            # Force immediate rotation if too many blocks
            if self.block_count >= self.max_block_count:
                logger.warning(f"Forcing proxy rotation after {self.block_count} blocks")
                self.get_proxy()  # This will force a rotation
    
    def check_proxy_health(self, proxy_url):
        """Check if a proxy is healthy by making a test request."""
        try:
            test_url = "https://www.google.com/robots.txt"
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
            
            start_time = time.time()
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=10
            )
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                self.report_success(proxy_url, response_time_ms)
                return True, response_time_ms
            else:
                self.report_failure(proxy_url)
                return False, response_time_ms
        except Exception as e:
            logger.error(f"Error checking proxy health for {proxy_url}: {str(e)}")
            self.report_failure(proxy_url)
            return False, None
    
    def check_all_proxies(self):
        """Check the health of all proxies."""
        results = []
        for proxy in self.proxies:
            healthy, response_time_ms = self.check_proxy_health(proxy['url'])
            results.append({
                'url': proxy['url'],
                'healthy': healthy,
                'response_time_ms': response_time_ms,
                'country_code': proxy.get('country_code'),
                'region': proxy.get('region')
            })
        return results
    
    def get_proxy_stats(self):
        """Get statistics about proxy usage."""
        total_success = sum(p.get('success_count', 0) for p in self.proxies)
        total_failure = sum(p.get('failure_count', 0) for p in self.proxies)
        total_requests = total_success + total_failure
        success_rate = total_success / total_requests if total_requests > 0 else 0
        
        return {
            'total_proxies': len(self.proxies),
            'total_requests': total_requests,
            'success_rate': success_rate,
            'current_rotation_frequency': self.rotation_frequency,
            'block_count': self.block_count
        }

# Create a global instance
proxy_manager = ProxyManager()
