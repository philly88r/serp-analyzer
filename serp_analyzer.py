import os
import sys
import json
import csv
import time
import random
import asyncio
import logging
import requests
import pandas as pd
import re
from urllib.parse import quote_plus, unquote, urlparse
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
        
        # Check if we're running on Heroku or Render
        self.is_heroku = 'DYNO' in os.environ
        self.is_render = 'RENDER' in os.environ
        print(f"Running on Heroku: {self.is_heroku}, Running on Render: {self.is_render}")
        
        # Create a directory for browser cache if it doesn't exist
        self.browser_cache_dir = os.path.join(os.getcwd(), '.browser_cache')
        os.makedirs(self.browser_cache_dir, exist_ok=True)
        
        # Create necessary directories
        os.makedirs("results", exist_ok=True)
        
        # Initialize proxy rotation variables
        self._last_state_index = 0
        
        # Initialize proxy state tracking
        us_states = [
            "us_florida", "us_california", "us_massachusetts", "us_north_carolina", 
            "us_south_carolina", "us_nevada", "us_new_york", "us_texas", 
            "us_washington", "us_illinois", "us_arizona", "us_colorado",
            "us_georgia", "us_michigan", "us_ohio", "us_pennsylvania",
            "us_virginia", "us_new_jersey", "us_minnesota", "us_oregon"
        ]
        
        # Initialize proxy state tracking dictionary with more aggressive rotation
        self._proxy_state = {
            'last_state': None,
            'used_states': set(),
            'state_blocks': {state: 0 for state in us_states},
            'state_delays': {state: 1 for state in us_states},  # Default 1 second delay
            'circuit_breaker': {state: {'is_open': False, 'reset_timeout': 180, 'last_attempt': time.time(), 'failure_count': 0} for state in us_states},
            'rotation_interval': 60,  # 1 minute default (more aggressive)
            'last_rotation_time': time.time(),
            'last_rotation': time.time(),  # For compatibility with existing code
            'consecutive_blocks': 0,
            'global_backoff': 1,  # Global backoff multiplier
            'block_count': 0,  # Count of recent blocks
            'last_block_time': time.time()  # Time of the last block
        }
    
    async def search_google(self, query, num_results=6):
        """
        Search Google for a query and extract the top results.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to extract
            
        Returns:
            list: List of dictionaries containing search results, or empty list if error
        """
        # Add US-specific parameters to the search URL
        # gl=us: Sets Google's country to US
        # hl=en: Sets language to English
        # cr=countryUS: Restricts results to US
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&gl=us&hl=en&cr=countryUS&pws=0"
        
        # If Oxylabs is configured, use it for reliable results
        if OXYLABS_CONFIGURED:
            print("Using Oxylabs for reliable Google search results")
            
            # Try the direct HTTP method first (most reliable)
            print("Trying direct HTTP method with Oxylabs proxy")
            results = await self._search_with_oxylabs_direct_http(query, num_results)
            
            # If we got results, return them
            if results and len(results) > 0:
                print(f"Found {len(results)} results with direct HTTP method")
                return results
            
            # If direct HTTP failed, try the proxy method with crawler
            print("Direct HTTP method failed, trying Oxylabs proxy with crawler")
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
        
        # Determine rotation interval based on block history
        current_time = time.time()
        
        # More aggressive rotation: 30-60 seconds instead of 1-2 minutes
        base_interval = random.randint(30, 60)
        
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
        else:
            # Use the current state
            current_state = self._proxy_state['last_state']
            if not current_state:
                # If no current state, choose a random one
                current_state = random.choice(us_states)
                self._proxy_state['last_state'] = current_state
            
            print(f"Using current proxy state: {current_state}")
            
        try:
            # Create a session for better connection reuse
            session = requests.Session()
            
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
                accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            elif is_firefox:
                accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            else:
                accept = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            
            # Set up headers with more realistic values
            headers = {
                "User-Agent": selected_user_agent,
                "Accept": accept,
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.google.com/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Sec-CH-UA": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": '"Windows"',
                "Cache-Control": "max-age=0"
            }
            
            # Add URL parameters that real browsers would include
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
                    
                    # Get current state, use a default if None
                    current_state = self._proxy_state['last_state']
                    if current_state is None:
                        # Use the first state in the list as default
                        us_states = list(self._proxy_state['circuit_breaker'].keys())
                        if us_states:
                            current_state = us_states[0]
                            self._proxy_state['last_state'] = current_state
                        else:
                            # Fallback to a default state
                            current_state = "us_default"
                            self._proxy_state['circuit_breaker'][current_state] = {
                                'is_open': False,
                                'reset_timeout': 180,
                                'last_attempt': time.time(),
                                'failure_count': 0
                            }
                            self._proxy_state['last_state'] = current_state
                    
                    # Update circuit breaker for the current state
                    try:
                        circuit = self._proxy_state['circuit_breaker'][current_state]
                        
                        # Ensure failure_count exists
                        if 'failure_count' not in circuit:
                            circuit['failure_count'] = 0
                            
                        circuit['failure_count'] += 1
                        circuit['last_attempt'] = time.time()
                    except Exception as e:
                        print(f"Error updating circuit breaker: {str(e)}")
                        # Create a new circuit breaker entry if needed
                        self._proxy_state['circuit_breaker'][current_state] = {
                            'is_open': False,
                            'reset_timeout': 180,
                            'last_attempt': time.time(),
                            'failure_count': 1
                        }
                    
                    # Increment block count for this specific state
                    self._proxy_state['state_blocks'][current_state] += 1
                    
                    # Increase delay factor for this state (exponential backoff)
                    self._proxy_state['state_delays'][current_state] = min(
                        120,  # Cap at 2 minutes
                        self._proxy_state['state_delays'][current_state] * 1.5
                    )
                    
                    # More aggressive circuit breaker: Open after just 2 consecutive failures
                    if circuit['failure_count'] >= 2:
                        circuit['is_open'] = True
                        # Shorter timeout to try more states faster
                        circuit['reset_timeout'] = min(900, 180 * (2 ** (circuit['failure_count'] - 2)))
                        print(f"Circuit breaker OPEN for {current_state} - too many blocks. Will try again in {circuit['reset_timeout']}s")
                    
                    # More aggressive global backoff factor
                    self._proxy_state['global_backoff'] = min(5, self._proxy_state['global_backoff'] * 1.3)
                    
                    # Force immediate proxy rotation
                    self._proxy_state['last_rotation'] = 0
                    
                    # Return empty results to trigger fallback methods
                    return []
                
                # Process the HTML to extract search results
                search_results = await self._process_google_html(html_content, query, num_results)
                
                # If we got results, reset failure count for this state
                if search_results and len(search_results) > 0:
                    if current_state in self._proxy_state['circuit_breaker']:
                        self._proxy_state['circuit_breaker'][current_state]['failure_count'] = 0
                    print(f"Successfully extracted {len(search_results)} results with direct HTTP method")
                    return search_results
                else:
                    print("No results found in the HTML response")
                    return []
            else:
                print(f"Error from Google: {response.status_code} - {response.reason}")
                
                # Check for specific error codes
                is_rate_limited = response.status_code == 429
                is_blocked = response.status_code in [403, 429, 503]
                
                if is_blocked or is_rate_limited:
                    # Handle block similar to CAPTCHA detection
                    print(f"Blocked by status code: {response.status_code}")
                    
                    # Track the block for adaptive rotation
                    self._proxy_state['block_count'] += 1
                    self._proxy_state['last_block_time'] = time.time()
                    
                    # Get current state, use a default if None
                    current_state = self._proxy_state['last_state']
                    if current_state is None:
                        # Use the first state in the list as default
                        us_states = list(self._proxy_state['circuit_breaker'].keys())
                        if us_states:
                            current_state = us_states[0]
                            self._proxy_state['last_state'] = current_state
                        else:
                            # Fallback to a default state
                            current_state = "us_default"
                            self._proxy_state['circuit_breaker'][current_state] = {
                                'is_open': False,
                                'reset_timeout': 180,
                                'last_attempt': time.time(),
                                'failure_count': 0
                            }
                            self._proxy_state['last_state'] = current_state
                    
                    # Update circuit breaker for the current state
                    try:
                        circuit = self._proxy_state['circuit_breaker'][current_state]
                        
                        # Ensure failure_count exists
                        if 'failure_count' not in circuit:
                            circuit['failure_count'] = 0
                            
                        circuit['failure_count'] += 1
                        circuit['last_attempt'] = time.time()
                    except Exception as e:
                        print(f"Error updating circuit breaker: {str(e)}")
                        # Create a new circuit breaker entry if needed
                        self._proxy_state['circuit_breaker'][current_state] = {
                            'is_open': False,
                            'reset_timeout': 180,
                            'last_attempt': time.time(),
                            'failure_count': 1
                        }
                    
                    # Increment block count for this specific state
                    self._proxy_state['state_blocks'][current_state] += 1
                    
                    # More aggressive circuit breaker: Open after just 2 consecutive failures
                    if circuit['failure_count'] >= 2:
                        circuit['is_open'] = True
                        circuit['reset_timeout'] = min(900, 180 * (2 ** (circuit['failure_count'] - 2)))
                        print(f"Circuit breaker OPEN for {current_state} - too many blocks. Will try again in {circuit['reset_timeout']}s")
                    
                    # Force immediate proxy rotation
                    self._proxy_state['last_rotation'] = 0
                
                return []
        except Exception as e:
            print(f"Error during direct HTTP request: {str(e)}")
            return []
        
        # Process each result element
        for element in result_elements:
            try:
                # Extract the title and URL
                title_element = element.select_one("h3") or element.select_one("a h3") or element.select_one("a")
                title = title_element.get_text().strip() if title_element else "Unknown Title"
                
                # Find the URL - try multiple approaches
                url_element = element.select_one("a") or element.select_one("div.yuRUbf a") or element.select_one("div.rc a")
                url = url_element.get("href") if url_element else ""
                
                # Clean the URL (remove tracking parameters)
                if url.startswith("/url?q="):
                    url = url.split("/url?q=")[1].split("&")[0]
                
                # Skip if URL is not valid
                if not url or not url.startswith("http"):
                    continue
                
                # Extract the snippet
                snippet_element = element.select_one("div.VwiC3b") or element.select_one("span.st") or element.select_one("div.s")
                snippet = snippet_element.get_text().strip() if snippet_element else ""
                
                # Add this result
                search_results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })
            except Exception as e:
                print(f"Error extracting result: {str(e)}")
                continue
        
        # Remove duplicates based on URL
        unique_urls = set()
        unique_results = []
        for result in search_results:
            if result["url"] not in unique_urls:
                unique_urls.add(result["url"])
                unique_results.append(result)
        
        print(f"Found {len(unique_results)} unique URLs")
        return unique_results[:num_results]  # Return only the requested number of results
        
    async def _process_google_html(self, html, query, num_results=6):
        """
        Process Google HTML to extract search results
        
        Args:
            html (str): HTML content from Google search
            query (str): The search query
            num_results (int): Number of results to extract
            
        Returns:
            list: List of dictionaries containing search results
        """
        search_results = []
        
        try:
            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try multiple selectors for Google search results
            selectors = ["div.g", "div.Gx5Zad", "div.tF2Cxc", "div.yuRUbf", "div[jscontroller]", "div.rc"]
            result_elements = []
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"Found {len(elements)} results with selector: {selector}")
                    result_elements = elements
                    break
            
            if not result_elements:
                print("No results found with standard selectors, trying alternative methods")
                # Try a more generic approach
                result_elements = soup.select("div > a")
                if result_elements:
                    print(f"Found {len(result_elements)} results with generic selector")
            
            # Process each result element
            for element in result_elements:
                try:
                    # Extract the title and URL
                    title_element = element.select_one("h3") or element.select_one("a h3") or element.select_one("a")
                    title = title_element.get_text().strip() if title_element else "Unknown Title"
                    
                    # Find the URL - try multiple approaches
                    url_element = element.select_one("a") or element.select_one("div.yuRUbf a") or element.select_one("div.rc a")
                    url = url_element.get("href") if url_element else ""
                    
                    # Clean the URL (remove tracking parameters)
                    if url.startswith("/url?q="):
                        url = url.split("/url?q=")[1].split("&")[0]
                    
                    # Skip if URL is not valid
                    if not url or not url.startswith("http"):
                        continue
                    
                    # Extract the snippet
                    snippet_element = element.select_one("div.VwiC3b") or element.select_one("span.st") or element.select_one("div.s")
                    snippet = snippet_element.get_text().strip() if snippet_element else ""
                    
                    # Add this result
                    search_results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
                except Exception as e:
                    print(f"Error extracting result: {str(e)}")
                    continue
            
            # Remove duplicates based on URL
            unique_urls = set()
            unique_results = []
            for result in search_results:
                if result["url"] not in unique_urls:
                    unique_urls.add(result["url"])
                    unique_results.append(result)
            
            print(f"Found {len(unique_results)} unique URLs")
            return unique_results[:num_results]  # Return only the requested number of results
            
        except Exception as e:
            print(f"Error processing Google HTML: {str(e)}")
            return []
    
    async def _extract_results_with_regex(self, html, num_results=6):
        """
        Extract search results using regex patterns when BeautifulSoup selectors fail
        This is a last resort method for when Google's HTML structure is completely different
        """
        print("Attempting to extract results with regex patterns")
        search_results = []
        unique_urls = set()
        
        try:
            # Pattern to match URLs in Google search results
            import re
            url_pattern = r'href="(https?://[^"]+)"'
            urls = re.findall(url_pattern, html)
            
            # Filter out Google URLs and other non-result URLs
            filtered_urls = []
            for url in urls:
                # Skip Google URLs and other common non-result URLs
                if any(domain in url for domain in ["google.com", "gstatic.com", "youtube.com", "accounts.google", "policies.google"]):
                    continue
                    
                # Skip image, video, map results
                if any(path in url for path in ["/images", "/videos", "/maps"]):
                    continue
                    
                # Add to filtered list if not already seen
                if url not in unique_urls:
                    unique_urls.add(url)
                    filtered_urls.append(url)
            
            print(f"Found {len(unique_urls)} unique URLs with regex")
            
            # For each URL, try to find a title and snippet
            for url in filtered_urls[:num_results]:  # Limit to requested number
                # Try to find title near this URL
                title_pattern = f'href="{re.escape(url)}"[^>]*>([^<]+)</a>'
                title_matches = re.findall(title_pattern, html)
                title = title_matches[0] if title_matches else "Unknown Title"
                
                # Add this result
                search_results.append({
                    "title": title,
                    "url": url,
                    "snippet": ""  # Regex extraction of snippets is unreliable
                })
            
            print(f"Extracted {len(search_results)} results with regex method")
            return search_results
            
        except Exception as e:
            print(f"Error extracting results with regex: {str(e)}")
            return []
            
    async def _search_with_oxylabs_serp_api(self, query, num_results=6):
        """
        Search Google using Oxylabs SERP API
        """
        try:
            print(f"Using Oxylabs SERP API for query: {query}")
            
            # Prepare the request payload
            payload = {
                "source": "google_search",
                "domain": "com",
                "query": query,
                "parse": True,
                "pages": 1,
                "context": [
                    {"key": "gl", "value": "us"},
                    {"key": "hl", "value": "en"},
                    {"key": "google_domain", "value": "google.com"},
                    {"key": "device", "value": "desktop"}
                ]
            }
            
            # Set up authentication and headers
            auth = (OXYLABS_USERNAME, OXYLABS_PASSWORD)
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Make the request to the SERP API
            response = requests.post(
                SERP_API_URL,
                json=payload,
                auth=auth,
                headers=headers,
                timeout=60
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                data = response.json()
                
                # Check if we have results
                if 'results' in data and len(data['results']) > 0:
                    result = data['results'][0]
                    
                    # Check if we have organic results
                    if 'organic' in result and len(result['organic']) > 0:
                        # Extract the search results
                        search_results = []
                        for item in result['organic'][:num_results]:
                            search_results.append({
                                'title': item.get('title', ''),
                                'url': item.get('url', ''),
                                'snippet': item.get('description', '')
                            })
                        
                        print(f"Found {len(search_results)} results with SERP API")
                        return search_results
                    else:
                        print("No organic results found in SERP API response")
                else:
                    print("No results found in SERP API response")
            else:
                print(f"Error from SERP API: {response.status_code} - {response.text}")
            
            return []
        except Exception as e:
            print(f"Error using SERP API: {str(e)}")
            return []
            
    async def _search_with_oxylabs_proxy(self, query, search_url, num_results=6):
        """
        Search Google using Oxylabs proxy with crawl4ai browser automation
        """
        try:
            print(f"Using Oxylabs proxy with crawler for query: {query}")
            
            # Determine which US state to use based on our rotation strategy
            current_time = time.time()
            current_state = self._proxy_state.get('current_state')
            
            # If we need to rotate or don't have a current state, choose a new one
            if not current_state or current_time - self._proxy_state['last_rotation'] > self._proxy_state['rotation_interval']:
                # Use the same logic as in _search_with_oxylabs_direct_http
                us_states = [
                    "us_florida", "us_california", "us_massachusetts", "us_north_carolina", 
                    "us_south_carolina", "us_nevada", "us_new_york", "us_texas", 
                    "us_illinois", "us_washington", "us_colorado", "us_arizona", 
                    "us_oregon", "us_virginia", "us_georgia", "us_michigan", 
                    "us_ohio", "us_pennsylvania", "us_new_jersey", "us_minnesota"
                ]
                
                # Filter out states with open circuit breakers
                working_states = [s for s in us_states if not self._proxy_state['circuit_breaker'].get(s, {}).get('is_open', False)]
                
                # If no working states, reset all circuit breakers
                if not working_states:
                    for state in us_states:
                        self._proxy_state['circuit_breaker'][state] = {'is_open': False, 'failure_count': 0, 'last_attempt': time.time()}
                    working_states = us_states
                
                # Sort by block count and choose from the best options
                working_states.sort(key=lambda s: self._proxy_state['state_blocks'].get(s, 0))
                selection_pool = working_states[:min(3, len(working_states))]
                current_state = random.choice(selection_pool)
                
                # Update state tracking
                self._proxy_state['last_rotation'] = current_time
                self._proxy_state['current_state'] = current_state
                
                print(f"Rotating proxy for crawler: Using {current_state}")
            
            # Generate a unique session ID
            session_id = random.randint(10000, 99999)
            
            # Set up the proxy with enhanced authentication
            proxy_username = f"{OXYLABS_USERNAME}-st-{current_state}-sessid-{session_id}-sesstime-3"
            proxy_url = f"http://{proxy_username}:{OXYLABS_PASSWORD}@pr.oxylabs.io:7777"
            
            print(f"Using proxy with state {current_state} and session {session_id}")
            
            # Use AsyncWebCrawler with the proxy
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(
                    search_url,
                    headless=self.headless,
                    proxy=proxy_url,
                    cache_mode="bypass",
                    wait_until="networkidle",
                    page_timeout=30000,
                    delay_before_return_html=0.5,
                    word_count_threshold=100,
                    scan_full_page=True,
                    scroll_delay=0.3,
                    remove_overlay_elements=True
                )
                
                if not result.success:
                    print(f"Error searching with crawler: {result.error_message}")
                    
                    # Check if the error indicates a block
                    block_indicators = ["captcha", "unusual traffic", "sorry", "automated", "robot"]
                    is_blocked = any(indicator in result.error_message.lower() for indicator in block_indicators)
                    
                    if is_blocked:
                        print("Detected block in crawler error message")
                        # Update block tracking
                        self._proxy_state['block_count'] = self._proxy_state.get('block_count', 0) + 1
                        self._proxy_state['last_block_time'] = time.time()
                        self._proxy_state['state_blocks'][current_state] = self._proxy_state['state_blocks'].get(current_state, 0) + 1
                        
                        # Update circuit breaker
                        # Make sure current_state is valid
                        if current_state is None:
                            # Use a default state if none is set
                            us_states = list(self._proxy_state['circuit_breaker'].keys())
                            if us_states:
                                current_state = us_states[0]
                                self._proxy_state['current_state'] = current_state
                            else:
                                # If no states available, create a default one
                                current_state = "us_default"
                                self._proxy_state['circuit_breaker'][current_state] = {
                                    'is_open': False,
                                    'reset_timeout': 180,
                                    'last_attempt': time.time(),
                                    'failure_count': 0
                                }
                                self._proxy_state['current_state'] = current_state
                        
                        # Ensure the circuit breaker exists for this state
                        if current_state not in self._proxy_state['circuit_breaker']:
                            self._proxy_state['circuit_breaker'][current_state] = {
                                'is_open': False,
                                'reset_timeout': 180,
                                'last_attempt': time.time(),
                                'failure_count': 0
                            }
                        
                        # Get the circuit breaker and update it
                        circuit = self._proxy_state['circuit_breaker'][current_state]
                        
                        # Ensure failure_count exists
                        if 'failure_count' not in circuit:
                            circuit['failure_count'] = 0
                            
                        circuit['failure_count'] += 1
                        circuit['last_attempt'] = time.time()
                        
                        # Open circuit breaker if too many failures
                        if circuit['failure_count'] >= 2:
                            circuit['is_open'] = True
                            circuit['reset_timeout'] = min(900, 180 * (2 ** (circuit['failure_count'] - 2)))
                            print(f"Circuit breaker OPEN for {current_state}")
                        
                        # Force immediate rotation
                        self._proxy_state['last_rotation'] = 0
                    
                    return []
                
                # Process the HTML
                html_content = result.html
                search_results = await self._process_google_html(html_content, query, num_results)
                
                # If we got results, reset failure count
                if search_results and len(search_results) > 0:
                    try:
                        if current_state in self._proxy_state['circuit_breaker']:
                            # Ensure the circuit breaker has the expected structure
                            if 'failure_count' not in self._proxy_state['circuit_breaker'][current_state]:
                                self._proxy_state['circuit_breaker'][current_state]['failure_count'] = 0
                            else:
                                self._proxy_state['circuit_breaker'][current_state]['failure_count'] = 0
                    except Exception as e:
                        print(f"Error resetting failure count: {str(e)}")
                        # Non-critical error, continue anyway
                    return search_results
                else:
                    # Try regex extraction as a last resort
                    return await self._extract_results_with_regex(html_content, num_results)
        except Exception as e:
            print(f"Error using Oxylabs proxy with crawler: {str(e)}")
            return []
            
    async def _direct_search_google(self, query, search_url, num_results=6):
        """
        Search Google directly without proxies
        """
        try:
            print(f"Using direct search method for query: {query}")
            
            # Use AsyncWebCrawler without a proxy
            async with AsyncWebCrawler() as crawler:
                # Rotate user agents
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/112.0"
                ]
                
                result = await crawler.arun(
                    search_url,
                    headless=self.headless,
                    user_agent=random.choice(user_agents),
                    cache_mode="bypass",
                    wait_until="networkidle",
                    page_timeout=30000,
                    delay_before_return_html=0.5,
                    word_count_threshold=100,
                    scan_full_page=True,
                    scroll_delay=0.3,
                    remove_overlay_elements=True
                )
                
                if not result.success:
                    print(f"Error searching with direct method: {result.error_message}")
                    return []
                
                # Process the HTML
                html_content = result.html
                search_results = await self._process_google_html(html_content, query, num_results)
                
                if search_results and len(search_results) > 0:
                    return search_results
                else:
                    # Try regex extraction as a last resort
                    return await self._extract_results_with_regex(html_content, num_results)
        except Exception as e:
            print(f"Error using direct search method: {str(e)}")
            return []
            
    async def analyze_page(self, url):
        """
        Analyze a single page to extract SEO and content data.
        
        Args:
            url (str): URL of the page to analyze
            
        Returns:
            dict: Dictionary containing page analysis data
        """
        try:
            print(f"Analyzing page: {url}")
            
            # Use AsyncWebCrawler to fetch and analyze the page
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(
                    url,
                    headless=self.headless,
                    cache_mode="bypass",
                    wait_until="networkidle",
                    page_timeout=30000,
                    delay_before_return_html=1.0,
                    word_count_threshold=100,
                    scan_full_page=True,
                    scroll_delay=0.5,
                    remove_overlay_elements=True,
                    extract_metadata=True
                )
                
                if not result.success:
                    print(f"Error analyzing page: {result.error_message}")
                    return {
                        "success": False,
                        "error": result.error_message
                    }
                
                # Extract data from the result
                soup = BeautifulSoup(result.html, 'html.parser')
                
                # Extract metadata
                meta_description = ""
                meta_keywords = ""
                meta_tags = soup.find_all('meta')
                for tag in meta_tags:
                    if tag.get('name') == 'description':
                        meta_description = tag.get('content', '')
                    elif tag.get('name') == 'keywords':
                        meta_keywords = tag.get('content', '')
                
                # Extract headings
                h1_tags = [h1.get_text().strip() for h1 in soup.find_all('h1')]
                h2_tags = [h2.get_text().strip() for h2 in soup.find_all('h2')]
                h3_tags = [h3.get_text().strip() for h3 in soup.find_all('h3')]
                
                # Count links
                all_links = soup.find_all('a')
                internal_links = []
                external_links = []
                
                # Parse the URL to get the domain
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                
                for link in all_links:
                    href = link.get('href')
                    if not href:
                        continue
                        
                    # Normalize the href
                    if href.startswith('/'):
                        # Convert relative URL to absolute
                        href = f"{parsed_url.scheme}://{domain}{href}"
                    elif not href.startswith('http'):
                        # Skip anchors and other non-http links
                        continue
                    
                    # Check if internal or external
                    parsed_href = urlparse(href)
                    if parsed_href.netloc == domain:
                        internal_links.append(href)
                    else:
                        external_links.append(href)
                
                # Count images
                images = soup.find_all('img')
                
                # Calculate word count from the HTML content
                text_content = soup.get_text()
                words = text_content.split()
                word_count = len(words)
                
                # Get content preview
                content_preview = ' '.join(words[:500]) + '...' if len(words) > 500 else text_content
                
                # Compile the analysis data
                analysis = {
                    "success": True,
                    "url": url,
                    "title": soup.title.string.strip() if soup.title else "", 
                    "meta_description": meta_description,
                    "meta_keywords": meta_keywords,
                    "h1_tags": h1_tags,
                    "h2_tags": h2_tags,
                    "h3_tags": h3_tags,
                    "word_count": word_count,
                    "internal_links": internal_links,
                    "external_links": external_links,
                    "internal_links_count": len(internal_links),
                    "external_links_count": len(external_links),
                    "images_count": len(images),
                    "content": content_preview  # Limit content to preview
                }
                
                return analysis
                
        except Exception as e:
            print(f"Error analyzing page {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def analyze_serp(self, query, num_results=6):
        """
        Perform a complete SERP analysis for a query.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to analyze
            
        Returns:
            dict: Dictionary containing SERP analysis data
        """
        print(f"\n===== ANALYZING SERP FOR QUERY: {query} =====\n")
        
        # Search Google for the query
        search_results = await self.search_google(query, num_results)
        
        # Print diagnostic information
        print(f"Search results type: {type(search_results)}")
        print(f"Search results count: {len(search_results)}")
        
        # Check if we got any results
        if not search_results or len(search_results) == 0:
            print(f"No search results found for query: {query}")
            return {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "No search results found",
                "results_count": 0,
                "results": []
            }
        
        # Analyze each result page
        analyzed_results = []
        for result in search_results:
            try:
                # Analyze the page
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
