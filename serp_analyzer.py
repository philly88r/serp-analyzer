# SERP Analyzer with enhanced Oxylabs integration for reliable Google search results
import os
import sys
import json
import csv
import time
import gc
import random
import asyncio
import logging
import requests
import pandas as pd
from urllib.parse import quote_plus, unquote
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

# Import Oxylabs configuration
try:
    from oxylabs_config import (
        OXYLABS_USERNAME, 
        OXYLABS_PASSWORD, 
        PROXY_URL, 
        SERP_API_URL,
        PROXY_TYPE,
        COUNTRY
    )
    OXYLABS_CONFIGURED = True
except (ImportError, AttributeError):
    # Try to get configuration from environment variables
    OXYLABS_USERNAME = os.environ.get('OXYLABS_USERNAME')
    OXYLABS_PASSWORD = os.environ.get('OXYLABS_PASSWORD')
    PROXY_URL = os.environ.get('PROXY_URL')
    SERP_API_URL = os.environ.get('SERP_API_URL')
    PROXY_TYPE = os.environ.get('PROXY_TYPE')
    COUNTRY = os.environ.get('COUNTRY')
    
    # Check if all required variables are set
    if all([OXYLABS_USERNAME, OXYLABS_PASSWORD, PROXY_URL, SERP_API_URL, PROXY_TYPE, COUNTRY]):
        print("Using Oxylabs configuration from environment variables.")
        OXYLABS_CONFIGURED = True
    else:
        print("Oxylabs configuration not found or incomplete. Will use direct requests.")
        OXYLABS_CONFIGURED = False

class SerpAnalyzer:
    def __init__(self, headless=False):
        """
        Initialize the SERP Analyzer with browser and crawler configurations.
        
        Args:
            headless (bool): Whether to run the browser in headless mode
        """
        self.headless = headless
        
        # Check if we're running on Heroku
        self.is_heroku = 'DYNO' in os.environ
        print(f"Running on Heroku: {self.is_heroku}")
        
        # Create a directory for browser cache if it doesn't exist
        self.browser_cache_dir = os.path.join(os.getcwd(), '.browser_cache')
        os.makedirs(self.browser_cache_dir, exist_ok=True)
        
        # Configure browser options based on environment
        self.browser_config = self._get_browser_config()
        
        # Create necessary directories
        os.makedirs("results", exist_ok=True)
        
        # Initialize proxy rotation variables
        self._last_state_index = 0
        
        # Initialize proxy state tracking
        us_states = [
            "us_florida", "us_california", "us_massachusetts", "us_north_carolina", 
            "us_south_carolina", "us_nevada", "us_new_york", "us_texas", 
            "us_washington", "us_illinois", "us_arizona", "us_colorado",
            "us_georgia", "us_michigan", "us_ohio", "us_pennsylvania"
        ]
        
        # Initialize proxy state tracking dictionary
        self._proxy_state = {
            'last_state': None,
            'used_states': set(),
            'state_blocks': {state: 0 for state in us_states},
            'state_delays': {state: 1 for state in us_states},  # Default 1 second delay
            'circuit_breaker': {state: {'is_open': False, 'reset_timeout': 300, 'last_attempt': time.time()} for state in us_states},
            'rotation_interval': 120,  # 2 minutes default
            'last_rotation_time': time.time(),
            'last_rotation': time.time(),  # For compatibility with existing code
            'consecutive_blocks': 0,
            'global_backoff': 1,  # Global backoff multiplier
            'block_count': 0,  # Count of recent blocks
            'last_block_time': time.time()  # Time of the last block
        }
    
    def _get_browser_config(self):
        """
        Get browser configuration based on the current environment.
        
        Returns:
            dict: Browser configuration options
        """
        # Base configuration that works for both local and Heroku environments
        config = {}
        
        # Add Heroku-specific configuration if needed
        if self.is_heroku:
            print("Configuring browser for Heroku environment")
            # Check for PLAYWRIGHT_BUILDPACK_BROWSERS environment variable
            playwright_browsers = os.environ.get('PLAYWRIGHT_BUILDPACK_BROWSERS', '')
            print(f"PLAYWRIGHT_BUILDPACK_BROWSERS: {playwright_browsers}")
            
            # Set environment variables for Playwright
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/app/.playwright'
        
        return config
        

    
    async def search_google(self, query, num_results=6):
        """
        Search Google for a query and extract the top results.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to extract
            
        Returns:
            list: List of dictionaries containing search results, or empty list if error
        """
        # Initialize an empty list to ensure we always return a list even on error
        search_results = []
        
        # Set the search region to the United States by adding gl=us and hl=en parameters
        # Add additional parameters to make the request look more natural
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&gl=us&hl=en&pws=0&safe=off&num={num_results}"
        print(f"Searching Google for: {query}")
        
        # Check if Oxylabs is configured
        if OXYLABS_CONFIGURED:
            # Try different methods in order of reliability
            # 1. First try direct HTTP request with Oxylabs proxy (often most reliable)
            print("Trying direct HTTP request with Oxylabs proxy")
            results = await self._search_with_oxylabs_direct_http(query, num_results)
            if results and len(results) > 0:
                return results
                
            # 2. If that fails, try Oxylabs SERP API if configured for that
            if PROXY_TYPE.lower() == "serp_api":
                print("Direct HTTP request failed, trying Oxylabs SERP API")
                results = await self._search_with_oxylabs_serp_api(query, num_results)
                if results and len(results) > 0:
                    return results
            
            # 3. Finally, try browser automation with Oxylabs proxy
            print(f"Trying browser automation with Oxylabs {PROXY_TYPE} proxies")
            return await self._search_with_oxylabs_proxy(query, search_url, num_results)
        
        # If Oxylabs is not configured, use the direct method with anti-bot measures
        print("Using direct search method with anti-bot measures")
        return await self._direct_search_google(query, search_url, num_results)
        
    async def _search_with_oxylabs_direct_http(self, query, num_results=6):
        """
        Search Google using direct HTTP requests with Oxylabs proxy
        This method often works better than browser automation for simple searches
        """
        search_results = []
        
        # Expanded list of US states to rotate through for better diversity
        us_states = [
            "us_florida", "us_california", "us_massachusetts", "us_north_carolina", 
            "us_south_carolina", "us_nevada", "us_new_york", "us_texas", 
            "us_illinois", "us_washington", "us_colorado", "us_arizona", 
            "us_oregon", "us_virginia", "us_georgia", "us_michigan", 
            "us_ohio", "us_pennsylvania", "us_new_jersey", "us_minnesota"
        ]
        
        # Track proxy state, block counts, and circuit breaker information
        if not hasattr(self, '_proxy_state'):
            self._proxy_state = {
                'last_rotation': 0,
                'last_state': None,
                'block_count': 0,
                'last_block_time': 0,
                'used_states': set(),
                'state_blocks': {},       # Track blocks per state
                'state_delays': {},       # Delay times for each state
                'circuit_breaker': {},    # Circuit breaker for each state
                'global_backoff': 1,      # Global backoff multiplier
                'last_success_time': 0    # Last successful request time
            }
            
        # Initialize tracking for each state if not already done
        for state in us_states:
            if state not in self._proxy_state['state_blocks']:
                self._proxy_state['state_blocks'][state] = 0
            if state not in self._proxy_state['state_delays']:
                self._proxy_state['state_delays'][state] = 1  # Base delay in seconds
            if state not in self._proxy_state['circuit_breaker']:
                self._proxy_state['circuit_breaker'][state] = {
                    'is_open': False,      # Is circuit open (state blocked)
                    'failure_count': 0,     # Consecutive failures
                    'last_attempt': 0,      # Last attempt time
                    'reset_timeout': 300    # Time to wait before trying again (5 minutes)
                }
        
        # Determine rotation interval based on block history
        current_time = time.time()
        
        # Base rotation interval is 1-2 minutes
        base_interval = random.randint(60, 120)
        
        # Apply global backoff if we've had many recent failures
        if self._proxy_state['global_backoff'] > 1:
            # Gradually reduce global backoff over time
            time_since_last_block = current_time - self._proxy_state['last_block_time']
            if time_since_last_block > 600:  # 10 minutes
                self._proxy_state['global_backoff'] = max(1, self._proxy_state['global_backoff'] * 0.8)
                print(f"Reducing global backoff to {self._proxy_state['global_backoff']:.2f}")
        
        # If we've seen blocks recently, adjust the interval
        if self._proxy_state['block_count'] > 0:
            # Reset block count after 30 minutes of no blocks
            if current_time - self._proxy_state['last_block_time'] > 1800:
                self._proxy_state['block_count'] = 0
                self._proxy_state['global_backoff'] = 1
                print("Reset block count and global backoff after 30 minutes of no blocks")
            else:
                # Exponentially decrease interval based on block count
                # More blocks = more frequent rotation
                reduction_factor = min(0.9, 0.2 * self._proxy_state['block_count'])
                base_interval = int(base_interval * (1 - reduction_factor))
                print(f"Block-adaptive rotation: Interval reduced to {base_interval}s due to {self._proxy_state['block_count']} recent blocks")
        
        # Check if we need to rotate proxies
        if current_time - self._proxy_state['last_rotation'] > base_interval:
            # Filter out states with open circuit breakers
            working_states = []
            for state in us_states:
                circuit = self._proxy_state['circuit_breaker'][state]
                
                # Check if circuit is open (state is blocked)
                if circuit['is_open']:
                    # Check if it's time to try the state again (circuit half-open)
                    if current_time - circuit['last_attempt'] > circuit['reset_timeout']:
                        print(f"Circuit breaker half-open for {state}, will try again")
                        circuit['is_open'] = False  # Reset to try again
                    else:
                        continue  # Skip this state, circuit still open
                
                # Add state to working states list
                working_states.append(state)
            
            # If no working states, reset all circuit breakers as a last resort
            if not working_states:
                print("WARNING: All states blocked, resetting all circuit breakers")
                for state in us_states:
                    self._proxy_state['circuit_breaker'][state]['is_open'] = False
                working_states = us_states
            
            # Choose a random state, but avoid recently used ones if possible
            available_states = [s for s in working_states if s not in self._proxy_state['used_states']]
            
            # If all states have been used, reset and use any working state
            if not available_states:
                self._proxy_state['used_states'] = set()
                available_states = working_states
            
            # Sort states by their block count and delay factor (prefer less blocked states)
            available_states.sort(key=lambda s: (self._proxy_state['state_blocks'][s], self._proxy_state['state_delays'][s]))
            
            # Select a state with preference for those with fewer blocks
            # Use the first 3 states with lowest block counts, or all if fewer than 3
            selection_pool = available_states[:min(3, len(available_states))]
            current_state = random.choice(selection_pool)
            
            # Update state tracking
            self._proxy_state['last_rotation'] = current_time
            self._proxy_state['last_state'] = current_state
            self._proxy_state['used_states'].add(current_state)
            
            # Keep track of the last 10 used states to avoid repetition
            if len(self._proxy_state['used_states']) > 10:
                self._proxy_state['used_states'].pop()
                
            print(f"Rotating proxy: Switching to US state {current_state} (blocks: {self._proxy_state['state_blocks'][current_state]}, delay: {self._proxy_state['state_delays'][current_state]}s)")
            
        try:
            # Prepare the search URL
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&gl=us&hl=en&pws=0&safe=off&num={num_results}"
            
            # Generate a unique session ID for each request
            import uuid
            session_id = str(uuid.uuid4())[:12]
            
            # Create username with US state and session parameters
            # Format: customer-USERNAME-st-STATE-sessid-SESSION_ID-sesstime-3
            # This targets specific US state proxies and maintains the same IP for 3 minutes
            enhanced_username = f"{OXYLABS_USERNAME}-st-{current_state}-sessid-{session_id}-sesstime-3"
            
            print(f"Using Oxylabs with enhanced parameters: US state={current_state}, session={session_id}")
            
            # Set up the proxy with enhanced authentication
            # Using the proxy port 7777 which is recommended for country-specific targeting
            proxy_url = "pr.oxylabs.io:7777"
            proxies = {
                "http": f"http://{enhanced_username}:{OXYLABS_PASSWORD}@{proxy_url}",
                "https": f"http://{enhanced_username}:{OXYLABS_PASSWORD}@{proxy_url}"
            }
                
            # Rotate user agents with more modern browser signatures
            user_agents = [
                # Chrome on Windows
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                # Chrome on macOS
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
                # Edge on Windows
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.58",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35",
                # Firefox on Windows
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
                # Firefox on macOS
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/112.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/113.0",
                # Safari on macOS
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"
            ]
            
            # Add request throttling to avoid triggering Google's rate limiting
            # Wait a small random time before making the request
            throttle_time = random.uniform(0.5, 2.0)
            await asyncio.sleep(throttle_time)
            print(f"Request throttling: Waited {throttle_time:.2f}s before making request")
            
            # Set up headers to look like a real browser with more human-like parameters
            selected_user_agent = random.choice(user_agents)
            
            # Create more realistic headers based on the selected user agent
            is_chrome = "Chrome" in selected_user_agent
            is_firefox = "Firefox" in selected_user_agent
            is_safari = "Safari" in selected_user_agent and "Chrome" not in selected_user_agent
            
            # Generate a realistic Accept header based on browser type
            if is_chrome or is_safari:
                accept_header = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            elif is_firefox:
                accept_header = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            else:
                accept_header = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            
            # Generate a realistic Accept-Language header with slight variations
            languages = ["en-US,en;q=0.9", "en-US,en;q=0.8", "en-GB,en;q=0.9,en-US;q=0.8", "en-CA,en;q=0.9,fr-CA;q=0.8"]
            
            # Add cookie consent parameters that regular browsers would have
            cookies = {}
            if random.random() > 0.5:  # Randomly include cookies
                cookies = {
                    "CONSENT": f"YES+cb.{int(time.time())}-04-p0.en+FX+{random.randint(100, 999)}",
                    "NID": ''.join(random.choices('0123456789abcdef', k=26)),
                    "1P_JAR": time.strftime("%Y-%m-%d"),
                }
            
            headers = {
                "User-Agent": selected_user_agent,
                "Accept": accept_header,
                "Accept-Language": random.choice(languages),
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.google.com/",
                "DNT": "1" if random.random() > 0.3 else "0",  # Most browsers have DNT enabled
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0"
            }
            
            print(f"Making direct HTTP request to {search_url} via Oxylabs country-specific proxy")
            
            # Create a session to maintain cookies and connection
            session = requests.Session()
            
            # Add cookies if we have them
            if 'cookies' in locals() and cookies:
                for name, value in cookies.items():
                    session.cookies.set(name, value, domain=".google.com")
            
            # Add random query parameters to make the request look more natural
            url_params = {
                "q": query,
                "gl": "us",
                "hl": "en",
                "pws": "0",
                "safe": "off",
                "num": str(num_results)
            }
            
            # Add random parameters that real browsers might include
            if random.random() > 0.5:
                url_params["source"] = "hp"
            if random.random() > 0.7:
                url_params["ei"] = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEF0123456789_-', k=22))
            if random.random() > 0.6:
                url_params["ved"] = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', k=random.randint(40, 60)))
            
            # Make the request with the session
            response = session.get(
                "https://www.google.com/search",
                params=url_params,
                proxies=proxies,
                headers=headers,
                timeout=30,
                allow_redirects=True  # Follow redirects
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                # Save the HTML for debugging
                html_content = response.text
                print(f"HTML preview: {html_content[:500]}...")
                
                # Check if we got a CAPTCHA page or any other block indicator
                # More comprehensive detection of Google blocks
                block_indicators = [
                    "captcha", 
                    "unusual traffic", 
                    "sorry...",
                    "automated queries",
                    "javascript to continue",
                    "please click here if you are not redirected",
                    "our systems have detected",
                    "enable javascript",
                    "httpservice/retry",
                    "detected unusual activity",
                    "confirm you're not a robot",
                    "security check",
                    "before we continue"
                ]
                
                is_blocked = any(indicator in html_content.lower() for indicator in block_indicators)
                if is_blocked:
                    print("DETECTED: Google CAPTCHA or block page in direct HTTP request")
                    
                    # Track the block for adaptive rotation
                    self._proxy_state['block_count'] += 1
                    self._proxy_state['last_block_time'] = time.time()
                    current_state = self._proxy_state['last_state']
                    
                    # Update circuit breaker for the current state
                    circuit = self._proxy_state['circuit_breaker'][current_state]
                    circuit['failure_count'] += 1
                    circuit['last_attempt'] = time.time()
                    
                    # Increment block count for this specific state
                    self._proxy_state['state_blocks'][current_state] += 1
                    
                    # Increase delay factor for this state (exponential backoff)
                    self._proxy_state['state_delays'][current_state] = min(
                        120,  # Cap at 2 minutes
                        self._proxy_state['state_delays'][current_state] * 1.5
                    )
                    
                    # Open circuit breaker if too many consecutive failures
                    if circuit['failure_count'] >= 3:
                        circuit['is_open'] = True
                        circuit['reset_timeout'] = min(1800, 300 * (2 ** (circuit['failure_count'] - 3)))
                        print(f"Circuit breaker OPEN for {current_state} - too many blocks. Will try again in {circuit['reset_timeout']}s")
                    
                    # Increase global backoff factor
                    self._proxy_state['global_backoff'] = min(8, self._proxy_state['global_backoff'] * 1.5)
                    
                    # Find states with closed circuit breakers
                    available_states = []
                    for state in us_states:
                        if state != current_state and not self._proxy_state['circuit_breaker'][state]['is_open']:
                            available_states.append(state)
                    
                    # If no available states, reset circuit breakers as last resort
                    if not available_states:
                        print("WARNING: All states blocked, resetting least-recently blocked state")
                        # Find the state with the oldest last_attempt
                        oldest_state = min(us_states, key=lambda s: self._proxy_state['circuit_breaker'][s]['last_attempt'])
                        self._proxy_state['circuit_breaker'][oldest_state]['is_open'] = False
                        available_states = [oldest_state]
                    
                    # Sort by block count and delay (prefer states with fewer blocks)
                    available_states.sort(key=lambda s: (self._proxy_state['state_blocks'][s], self._proxy_state['state_delays'][s]))
                    
                    # Choose from the top 3 least-blocked states
                    selection_pool = available_states[:min(3, len(available_states))]
                    new_state = random.choice(selection_pool)
                    
                    self._proxy_state['last_state'] = new_state
                    self._proxy_state['used_states'].add(new_state)
                    self._proxy_state['last_rotation'] = time.time()
                    
                    print(f"Immediate proxy rotation due to block: Switching to US state {new_state} (blocks: {self._proxy_state['state_blocks'][new_state]}, delay: {self._proxy_state['state_delays'][new_state]}s)")
                    
                    # Calculate backoff time based on global backoff and state-specific delay
                    backoff_time = random.uniform(2.0, 5.0) * self._proxy_state['global_backoff'] * self._proxy_state['state_delays'][new_state]
                    backoff_time = min(60, backoff_time)  # Cap at 60 seconds
                    
                    await asyncio.sleep(backoff_time)
                    print(f"Backing off for {backoff_time:.2f}s before retry")
                    
                    return []
                    
                # Process the HTML response
                return await self._process_google_html(html_content, query, num_results)
            else:
                print(f"Error from Google: {response.status_code} - {response.reason}")
                    
                # Check for specific error codes
                is_rate_limited = response.status_code == 429
                is_blocked = response.status_code in [403, 429, 503]
                
                # Track the error as a potential block
                self._proxy_state['block_count'] += 1
                self._proxy_state['last_block_time'] = time.time()
                current_state = self._proxy_state['last_state']
                
                # Update circuit breaker for the current state
                circuit = self._proxy_state['circuit_breaker'][current_state]
                circuit['failure_count'] += 1
                circuit['last_attempt'] = time.time()
                
                # Increment block count for this specific state
                self._proxy_state['state_blocks'][current_state] += 1
                
                # Handle rate limiting with more aggressive backoff
                if is_rate_limited:
                    # Increase delay factor more aggressively for rate limiting
                    self._proxy_state['state_delays'][current_state] = min(
                        240,  # Cap at 4 minutes for rate limiting
                        self._proxy_state['state_delays'][current_state] * 2.0
                    )
                    
                    # Open circuit breaker immediately for rate limiting
                    circuit['is_open'] = True
                    circuit['reset_timeout'] = 600  # 10 minutes timeout for rate-limited states
                    print(f"Circuit breaker OPEN for {current_state} - rate limited (429). Will try again in {circuit['reset_timeout']}s")
                    
                    # Increase global backoff factor more aggressively
                    self._proxy_state['global_backoff'] = min(10, self._proxy_state['global_backoff'] * 2.0)
                else:
                    # Normal error handling for other status codes
                    self._proxy_state['state_delays'][current_state] = min(
                        120,  # Cap at 2 minutes
                        self._proxy_state['state_delays'][current_state] * 1.5
                    )
                    
                    # Open circuit breaker if too many consecutive failures
                    if circuit['failure_count'] >= 3:
                        circuit['is_open'] = True
                        circuit['reset_timeout'] = min(1800, 300 * (2 ** (circuit['failure_count'] - 3)))
                        print(f"Circuit breaker OPEN for {current_state} - too many errors. Will try again in {circuit['reset_timeout']}s")
                    
                    # Increase global backoff factor
                    self._proxy_state['global_backoff'] = min(8, self._proxy_state['global_backoff'] * 1.5)
                
                # Find states with closed circuit breakers
                available_states = []
                for state in us_states:
                    if state != current_state and not self._proxy_state['circuit_breaker'][state]['is_open']:
                        available_states.append(state)
                
                # If no available states, reset circuit breakers as last resort
                if not available_states:
                    print("WARNING: All states blocked, resetting least-recently blocked state")
                    # Find the state with the oldest last_attempt
                    oldest_state = min(us_states, key=lambda s: self._proxy_state['circuit_breaker'][s]['last_attempt'])
                    self._proxy_state['circuit_breaker'][oldest_state]['is_open'] = False
                    available_states = [oldest_state]
                
                # Sort by block count and delay (prefer states with fewer blocks)
                available_states.sort(key=lambda s: (self._proxy_state['state_blocks'][s], self._proxy_state['state_delays'][s]))
                
                # Choose from the top 3 least-blocked states
                selection_pool = available_states[:min(3, len(available_states))]
                new_state = random.choice(selection_pool)
                
                self._proxy_state['last_state'] = new_state
                self._proxy_state['used_states'].add(new_state)
                self._proxy_state['last_rotation'] = time.time()
                
                print(f"Immediate proxy rotation due to error {response.status_code}: Switching to US state {new_state} (blocks: {self._proxy_state['state_blocks'][new_state]}, delay: {self._proxy_state['state_delays'][new_state]}s)")
                
                # Calculate backoff time based on global backoff and state-specific delay
                backoff_base = 5.0 if is_rate_limited else 2.0
                backoff_time = random.uniform(backoff_base, backoff_base * 2) * self._proxy_state['global_backoff'] * self._proxy_state['state_delays'][new_state]
                backoff_time = min(120, backoff_time)  # Cap at 2 minutes
                
                await asyncio.sleep(backoff_time)
                print(f"Backing off for {backoff_time:.2f}s before retry")
        
        except Exception as e:
            print(f"Error using direct HTTP request with Oxylabs proxy: {str(e)}")
            # Try with a different state on exception
            self._last_state_index = (self._last_state_index + 1) % len(us_states)
        
        return search_results
    
    async def _search_with_oxylabs_serp_api(self, query, num_results=6):
        """
        Search Google using Oxylabs SERP API
        """
        search_results = []
        
        try:
            # Prepare the payload for Oxylabs SERP API
            payload = {
                "source": "google_search",
                "domain": "com",
                "query": query,
                "parse": True,
                "pages": 1,
                "start_page": 1,
                "results_per_page": num_results,
                "geo_location": COUNTRY or "United States",
                "user_agent_type": "desktop"
            }
            
            # Make the request to Oxylabs SERP API
            response = requests.post(
                SERP_API_URL,
                json=payload,
                auth=(OXYLABS_USERNAME, OXYLABS_PASSWORD),
                headers={
                    "Content-Type": "application/json"
                }
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                data = response.json()
                
                # Extract organic search results
                if "results" in data and len(data["results"]) > 0:
                    results_data = data["results"][0]
                    
                    if "organic_results" in results_data:
                        organic_results = results_data["organic_results"]
                        
                        for result in organic_results[:num_results]:
                            search_results.append({
                                "title": result.get("title", ""),
                                "url": result.get("url", ""),
                                "snippet": result.get("description", "")
                            })
                        
                        print(f"Found {len(search_results)} results via Oxylabs SERP API")
                    else:
                        print("No organic results found in Oxylabs SERP API response")
                else:
                    print("No results found in Oxylabs SERP API response")
            else:
                print(f"Error from Oxylabs SERP API: {response.status_code} - {response.text}")
        
        except Exception as e:
            print(f"Error using Oxylabs SERP API: {str(e)}")
        
        return search_results
    
    async def _search_with_oxylabs_proxy(self, query, search_url, num_results=6):
        """
        Search Google using Oxylabs proxy with our crawler
        """
        search_results = []
        
        # List of common user agents to rotate through
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.55 Safari/537.36"
        ]
        
        import random
        
        # Configure browser options with Oxylabs proxy
        browser_options = {
            "headless": self.headless,
            "cache_mode": "bypass",
            "wait_until": "networkidle",
            "page_timeout": 90000,
            "delay_before_return_html": 2.0,
            "word_count_threshold": 100,
            "scan_full_page": True,
            "scroll_delay": random.uniform(0.7, 1.5),
            "process_iframes": False,
            "remove_overlay_elements": True,
            "magic": True,
            "user_agent": random.choice(user_agents),
            "extra_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.google.com/",
                "DNT": "1"
            },
            "viewport": {
                "width": random.choice([1366, 1440, 1536, 1920]),
                "height": random.choice([768, 900, 1080])
            },
            # Add Oxylabs proxy configuration - improved format
            "proxy": {
                "server": f"http://{PROXY_URL}",
                "username": OXYLABS_USERNAME,
                "password": OXYLABS_PASSWORD
            },
            # Add additional headers for proxy
            "extra_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.google.com/",
                "DNT": "1",
                "X-Crawlera-Session": f"create",
                "X-Crawlera-Cookies": "disable"
            }
        }
        
        try:
            # Create a new crawler with no config to avoid the verbose parameter conflict
            async with AsyncWebCrawler() as crawler:
                # Use the browser_options we defined above
                browser_options["url"] = search_url
                print(f"Starting crawler with Oxylabs proxy")
                result = await crawler.arun(**browser_options)
            
            if not result.success:
                print(f"Error searching Google with Oxylabs proxy: {result.error_message}")
                return search_results
                
            # Process the HTML response
            return await self._process_google_html(result.html, query, num_results)
            
        except Exception as e:
            print(f"Error during search with Oxylabs proxy: {str(e)}")
            return search_results
    
    async def _direct_search_google(self, query, search_url, num_results=6):
        """
        Search Google directly without proxies
        """
        search_results = []
        
        # List of common user agents to rotate through
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.55 Safari/537.36"
        ]
        
        import random
        
        # Configure browser options with anti-bot detection improvements
        browser_options = {
            "headless": self.headless,
            "cache_mode": "bypass",
            "wait_until": "networkidle",
            "page_timeout": 90000,  # Increased timeout for slower connections
            "delay_before_return_html": 2.0,  # Increased delay for better rendering
            "word_count_threshold": 100,
            "scan_full_page": True,
            "scroll_delay": random.uniform(0.7, 1.5),  # Randomized scroll delay for more human-like behavior
            "process_iframes": False,
            "remove_overlay_elements": True,
            "magic": True,
            "user_agent": random.choice(user_agents),  # Use a random user agent
            "extra_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.google.com/",
                "DNT": "1"
            },
            "viewport": {
                "width": random.choice([1366, 1440, 1536, 1920]),  # Random common screen width
                "height": random.choice([768, 900, 1080])  # Random common screen height
            }
        }
        
        # Add Heroku-specific options
        if self.is_heroku:
            print("Using Heroku-specific browser options")
            browser_options.update({
                "chromium_sandbox": False,
                "browser_args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                    f"--user-data-dir={self.browser_cache_dir}"
                ],
                "ignore_default_args": ["--disable-extensions"]
            })
            
            # Set environment variables for Playwright
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/app/.playwright'
        
        try:
            # Create a new crawler with no config to avoid the verbose parameter conflict
            async with AsyncWebCrawler() as crawler:
                # Use the browser_options we defined above
                browser_options["url"] = search_url
                print(f"Starting crawler with options: {browser_options}")
                result = await crawler.arun(**browser_options)
            
            if not result.success:
                print(f"Error searching Google: {result.error_message}")
                return search_results
                
            # Process the HTML response
            return await self._process_google_html(result.html, query, num_results)
            
        except Exception as e:
            print(f"Error during search: {str(e)}")
            return search_results
        
    async def _process_google_html(self, html, query, num_results=6):
        """
        Process Google search HTML to extract search results
        """
        search_results = []
        
        # Parse the HTML with BeautifulSoup
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Save the HTML for debugging (only in development)
        if not self.is_heroku:
            debug_dir = os.path.join(os.getcwd(), 'debug')
            os.makedirs(debug_dir, exist_ok=True)
            with open(os.path.join(debug_dir, f'google_search_{query.replace(" ", "_")}.html'), 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"Saved HTML response for debugging")
        
        # Add debug info - print a small sample of the HTML to see what we're getting
        html_preview = html[:500] + "..." if len(html) > 500 else html
        print(f"HTML preview: {html_preview}")
        
        # Check for common Google blocks or CAPTCHAs
        if "Our systems have detected unusual traffic" in html or "captcha" in html.lower():
            print("DETECTED: Google CAPTCHA page - we're being blocked")
            # Try the regex method as a last resort
            return await self._extract_results_with_regex(html, num_results)
            
        if "sorry..." in html.lower() and "page you requested was not found" in html.lower():
            print("DETECTED: Google error page")
            return []
                
        # Try different selectors to find search results
        # Google's HTML structure changes frequently, so we need to try multiple selectors
        selectors = [
            "div.g",
            "div.tF2Cxc", 
            "div.yuRUbf", 
            "div[data-sokoban-container]",
            "div.rc",
            "div.g div.rc",
            "div.jtfYYd",
            "div.MjjYud",
            "div.v7W49e",
            "div.Gx5Zad",
            "div.egMi0",
            "div.BYM4Nd",
            "div.ULSxyf",
            "div.hlcw0c",
            "div.g div",  # More generic fallback
            "[data-header-feature]",
            "[data-content-feature]"
        ]
        
        # Try each selector until we find results
        result_elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                print(f"Found {len(elements)} results with selector '{selector}'")
                result_elements = elements[:num_results]
                break
                
        if not result_elements:
            # If we still can't find results, look for h3 tags (which usually contain titles)
            h3_elements = soup.select("h3")
            if h3_elements:
                print(f"Found {len(h3_elements)} h3 elements, trying to find parent result containers")
                # For each h3, try to find its parent container
                for h3 in h3_elements[:num_results]:
                    parent = h3.parent
                    for _ in range(3):  # Go up to 3 levels up to find a container
                        if parent and parent.name == 'div':
                            result_elements.append(parent)
                            break
                        parent = parent.parent if parent else None
            
            # If still no results, try to find any links on the page
            if not result_elements:
                print("No results found with standard selectors, looking for any links...")
                links = soup.select("a[href^='http']")  # Links that start with http
                if links:
                    print(f"Found {len(links)} links on the page")
                    # Filter out Google's own links
                    external_links = [link for link in links if not "google.com" in link['href']]
                    print(f"Found {len(external_links)} external links")
                    
                    # Create simple result elements from these links
                    for link in external_links[:num_results]:
                        title = link.get_text().strip() or link['href']
                        result_elements.append({
                            'title': title,
                            'url': link['href'],
                            'is_direct_link': True  # Flag to handle differently in the processing below
                        })
        
        # If we still don't have results, try the regex method
        if not result_elements:
            print("No results found with any selectors, trying regex pattern matching")
            return await self._extract_results_with_regex(html, num_results)
        
        for element in result_elements:
            try:
                # Check if this is a direct link from our fallback method
                if isinstance(element, dict) and element.get('is_direct_link'):
                    search_results.append({
                        'title': element.get('title', 'Unknown Title'),
                        'url': element.get('url', ''),
                        'snippet': 'No snippet available (direct link extraction)'
                    })
                    continue
                
                # Extract title, URL, and snippet
                title_element = element.select_one("h3")
                link_element = element.select_one("a")
                
                # Try multiple snippet selectors
                snippet_selectors = ["div.VwiC3b", "span.aCOpRe", "div.lyLwlc", "div[data-content-feature='1']", "div.s3v9rd", "div.lEBKkf"]
                snippet_element = None
                for selector in snippet_selectors:
                    snippet_element = element.select_one(selector)
                    if snippet_element:
                        break
                
                # If we couldn't find a title element but there's a link with text, use that
                if not title_element and link_element and link_element.get_text().strip():
                    title = link_element.get_text().strip()
                elif title_element:
                    title = title_element.get_text().strip()
                else:
                    title = "Unknown Title"
                
                # Get URL
                url = ''
                if link_element:
                    url = link_element.get('href', '')
                    
                    # Clean up the URL if it's a Google redirect
                    if url.startswith('/url?'):
                        url = url.split('&sa=')[0].replace('/url?q=', '')
                        url = unquote(url)  # Decode URL-encoded characters
                
                # Get snippet if available
                snippet = ""
                if snippet_element:
                    snippet = snippet_element.get_text().strip()
                
                # Only add if we have at least a URL
                if url:
                    # Add to results
                    search_results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })
                    
                    if len(search_results) >= num_results:
                        break
            except Exception as e:
                print(f"Error extracting search result: {str(e)}")
                continue
                
        print(f"Found {len(search_results)} search results")
        print(f"Search results type: {type(search_results)}")
        print(f"Search results count: {len(search_results)}")
        return search_results
        
    async def _extract_results_with_regex(self, html, num_results=6):
        """
        Extract search results using regex patterns when BeautifulSoup selectors fail
        This is a last resort method for when Google's HTML structure is completely different
        """
        import re
        search_results = []
        
        print("Attempting to extract results with regex patterns")
        
        # Try to find URLs in the HTML
        # Look for http/https URLs that might be search results
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[\w/\-?=%.&~#]*'
        urls = re.findall(url_pattern, html)
        
        # Filter out Google's own URLs and common resource URLs
        filtered_urls = []
        excluded_domains = ['google.com', 'gstatic.com', 'googleapis.com', 'youtube.com/favicon', 'googleusercontent.com']
        
        for url in urls:
            if not any(domain in url for domain in excluded_domains):
                # Clean up the URL if it's part of a larger string
                url = url.split('"')[0].split("'")[0].split('&amp;')[0]
                filtered_urls.append(url)
        
        # Remove duplicates while preserving order
        unique_urls = []
        for url in filtered_urls:
            if url not in unique_urls:
                unique_urls.append(url)
        
        print(f"Found {len(unique_urls)} unique URLs with regex")
        
        # For each URL, try to find a title nearby in the HTML
        for url in unique_urls[:num_results]:
            # Create a simple result with just the URL if we can't find a title
            result = {
                'title': url.split('//')[1].split('/')[0],  # Use domain as title
                'url': url,
                'snippet': 'No snippet available (extracted with regex)'
            }
            
            # Try to find a title near this URL in the HTML
            # Look for text between tags near the URL
            url_index = html.find(url)
            if url_index > 0:
                # Look for text in a reasonable window around the URL
                window_start = max(0, url_index - 200)
                window_end = min(len(html), url_index + 200)
                window = html[window_start:window_end]
                
                # Try to find text between tags that might be a title
                title_matches = re.findall(r'>([^<>]{5,100})<', window)
                if title_matches:
                    # Use the longest match as the title (usually more descriptive)
                    title = max(title_matches, key=len).strip()
                    if title and len(title) > 5:  # Ensure it's a reasonable title
                        result['title'] = title
            
            search_results.append(result)
        
        print(f"Extracted {len(search_results)} results with regex method")
        return search_results
    
    async def analyze_page(self, url):
        """
        Analyze a single page to extract SEO and content data.
        
        Args:
            url (str): URL of the page to analyze
            
        Returns:
            dict: Dictionary containing page analysis data
        """
        print(f"Analyzing page: {url}")
        
        # Check if this is a known problematic site that might cause timeouts
        problematic_domains = ["reddit.com", "twitter.com", "facebook.com", "instagram.com"]
        if any(domain in url.lower() for domain in problematic_domains):
            print(f"Warning: {url} is a potentially slow site that might cause timeouts")
            # Set a shorter timeout for problematic sites
            page_timeout = 45000  # 45 seconds
        else:
            page_timeout = 90000  # 90 seconds for normal sites
        
        # Initialize default result structure with empty values
        default_result = {
            "url": url,
            "success": False,
            "title": "",
            "meta_description": "",
            "meta_keywords": "",
            "h1_tags": [],
            "h2_tags": [],
            "h3_tags": [],
            "internal_links": [],
            "external_links": [],
            "images": [],
            "word_count": 0,
            "content_preview": ""
        }
        
        # Configure browser options with longer timeouts for Render.com
        browser_options = {
            "url": url,
            "headless": self.headless,
            "cache_mode": "bypass",
            "wait_until": "networkidle",
            "page_timeout": page_timeout,
            "delay_before_return_html": 2.0,
            "word_count_threshold": 100,
            "scan_full_page": True,
            "scroll_delay": 1.0,
            "process_iframes": False,
            "remove_overlay_elements": True,
            "magic": True
        }
        
        # Add Heroku-specific options if needed
        if self.is_heroku:
            browser_options.update({
                "chromium_sandbox": False,
                "browser_args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                    f"--user-data-dir={self.browser_cache_dir}"
                ],
                "ignore_default_args": ["--disable-extensions"]
            })
        
        try:
            # Create a new crawler with no config to avoid the verbose parameter conflict
            async with AsyncWebCrawler() as crawler:
                print(f"Starting crawler with options: {browser_options}")
                result = await crawler.arun(**browser_options)
            
            if not result.success:
                print(f"Error analyzing page: {result.error_message}")
                return default_result
                
            # Extract HTML content
            html = result.html
            
            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract page title
            title = soup.title.text.strip() if soup.title else ""
            
            # Extract meta description
            meta_description = ""
            meta_desc_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            if meta_desc_tag and meta_desc_tag.get('content'):
                meta_description = meta_desc_tag['content']
            
            # Extract meta keywords
            meta_keywords = ""
            meta_keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords_tag and meta_keywords_tag.get('content'):
                meta_keywords = meta_keywords_tag['content']
            
            # Extract heading tags
            h1_tags = [h1.text.strip() for h1 in soup.find_all('h1') if h1.text.strip()]
            h2_tags = [h2.text.strip() for h2 in soup.find_all('h2') if h2.text.strip()]
            h3_tags = [h3.text.strip() for h3 in soup.find_all('h3') if h3.text.strip()]
            
            # Extract links
            internal_links = []
            external_links = []
            
            # Get the domain of the current page
            from urllib.parse import urlparse
            current_domain = urlparse(url).netloc
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Skip empty, javascript, or anchor links
                if not href or href.startswith('javascript:') or href.startswith('#'):
                    continue
                
                # Make relative URLs absolute
                if href.startswith('/'):
                    href = f"{urlparse(url).scheme}://{current_domain}{href}"
                elif not href.startswith('http'):
                    href = f"{url.rstrip('/')}/{href.lstrip('/')}"
                
                # Check if the link is internal or external
                link_domain = urlparse(href).netloc
                link_text = link.text.strip()
                
                link_info = {
                    'url': href,
                    'text': link_text if link_text else href
                }
                
                if link_domain == current_domain or not link_domain:
                    internal_links.append(link_info)
                else:
                    external_links.append(link_info)
            
            # Extract images
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                
                # Make relative URLs absolute
                if src.startswith('/'):
                    src = f"{urlparse(url).scheme}://{current_domain}{src}"
                elif not src.startswith('http'):
                    src = f"{url.rstrip('/')}/{src.lstrip('/')}"
                
                alt = img.get('alt', '')
                
                images.append({
                    'src': src,
                    'alt': alt
                })
            
            # Extract word count and content preview
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text content
            text_content = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text_content = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Calculate word count
            words = text_content.split()
            word_count = len(words)
            
            # Create content preview (first 200 words)
            content_preview = ' '.join(words[:200]) + '...' if len(words) > 200 else text_content
            
            # Compile the result
            analysis_result = {
                "url": url,
                "success": True,
                "title": title,
                "meta_description": meta_description,
                "meta_keywords": meta_keywords,
                "h1_tags": h1_tags,
                "h2_tags": h2_tags,
                "h3_tags": h3_tags,
                "internal_links": internal_links,
                "external_links": external_links,
                "images": images,
                "word_count": word_count,
                "content_preview": content_preview
            }
            
            return analysis_result
            
        except Exception as e:
            print(f"Error analyzing page {url}: {str(e)}")
            return default_result
    
    async def analyze_serp(self, query, num_results=6):
        """
        Perform a complete SERP analysis for a query.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to analyze
            
        Returns:
            dict: Dictionary containing SERP analysis data
        """
        # Search Google and get top results
        try:
            print(f"Analyzing SERP for query: {query}")
            search_results = await self.search_google(query, num_results)
            
            # Debug information
            print(f"Search results type: {type(search_results)}")
            print(f"Search results count: {len(search_results) if search_results else 0}")
            
            if not search_results or len(search_results) == 0:
                print(f"No search results found for query: {query}")
                return {
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "error": "No search results found",
                    "results": []
                }
        except Exception as e:
            print(f"Error during search_google: {str(e)}")
            return {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": f"Error during search: {str(e)}",
                "results": []
            }
        
        # Analyze each result page
        analyzed_results = []
        for result in search_results:
            try:
                print(f"Analyzing page: {result['url']}")
                analysis = await self.analyze_page(result["url"])
                
                # Combine search result data with page analysis
                full_result = {
                    **result,
                    **analysis
                }
                
                analyzed_results.append(full_result)
            except Exception as e:
                print(f"Error analyzing page {result['url']}: {str(e)}")
                # Add the result with error information
                error_result = {
                    **result,
                    "success": False,
                    "error": f"Error during analysis: {str(e)}"
                }
                analyzed_results.append(error_result)
        
        # Compile complete SERP analysis
        serp_analysis = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "results_count": len(analyzed_results),
            "results": analyzed_results
        }
        
        return serp_analysis
    
    def save_results(self, serp_analysis, output_format="json"):
        """
        Save SERP analysis results to file.
        
        Args:
            serp_analysis (dict): SERP analysis data
            output_format (str): Output format (json or csv)
            
        Returns:
            str: Path to saved file
        """
        query = serp_analysis["query"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sanitize query for filename
        sanitized_query = "".join(c if c.isalnum() else "_" for c in query)
        
        if output_format == "json":
            # Save full results to JSON
            filename = f"results/serp_{sanitized_query}_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(serp_analysis, f, indent=2, ensure_ascii=False)
            
            print(f"Saved JSON results to {filename}")
            return filename
            
        elif output_format == "csv":
            # Create a flattened DataFrame for CSV export
            rows = []
            for result in serp_analysis["results"]:
                row = {
                    "query": query,
                    "position": serp_analysis["results"].index(result) + 1,
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "success": result.get("success", False),
                    "word_count": result.get("word_count", 0),
                    "internal_links_count": result.get("internal_links_count", 0),
                    "external_links_count": result.get("external_links_count", 0),
                    "images_count": result.get("images_count", 0),
                    "meta_description": result.get("meta_description", ""),
                    "meta_keywords": result.get("meta_keywords", ""),
                    "h1_count": len(result.get("h1_tags", [])),
                    "h2_count": len(result.get("h2_tags", [])),
                    "h3_count": len(result.get("h3_tags", []))
                }
                rows.append(row)
            
            df = pd.DataFrame(rows)
            filename = f"results/serp_{sanitized_query}_{timestamp}.csv"
            df.to_csv(filename, index=False, encoding="utf-8")
            
            print(f"Saved CSV results to {filename}")
            return filename
        
        else:
            print(f"Unsupported output format: {output_format}")
            return None


async def main():
    # Initialize the SERP Analyzer
    analyzer = SerpAnalyzer(headless=False)  # Set to True for headless mode
    
    # Get search query from user
    query = input("Enter your search query: ")
    num_results = int(input("Number of results to analyze (default 6): ") or "6")
    
    # Perform SERP analysis
    serp_analysis = await analyzer.analyze_serp(query, num_results)
    
    # Save results
    analyzer.save_results(serp_analysis, "json")
    analyzer.save_results(serp_analysis, "csv")
    
    print("\nAnalysis complete!")
    print(f"Analyzed {len(serp_analysis['results'])} search results for query: {query}")


if __name__ == "__main__":
    asyncio.run(main())
