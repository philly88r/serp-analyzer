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
        
        self.is_heroku = 'DYNO' in os.environ
        self.is_render = 'RENDER' in os.environ
        print(f"Running on Heroku: {self.is_heroku}, Running on Render: {self.is_render}")
        
        self.browser_cache_dir = os.path.join(os.getcwd(), '.browser_cache')
        os.makedirs(self.browser_cache_dir, exist_ok=True)
        os.makedirs("results", exist_ok=True)
        
        # Define US states for proxy rotation as an instance attribute
        self.us_states = [
            "us_florida", "us_california", "us_massachusetts", "us_north_carolina", 
            "us_south_carolina", "us_nevada", "us_new_york", "us_texas", 
            "us_washington", "us_illinois", "us_arizona", "us_colorado",
            "us_georgia", "us_michigan", "us_ohio", "us_pennsylvania",
            "us_virginia", "us_new_jersey", "us_minnesota", "us_oregon"
        ]
        
        # Initialize proxy state tracking dictionary
        self._proxy_state = {
            'last_state': None,
            'last_used_proxy_index': -1, # Start before the first state
            'used_states': set(), # Not currently used by _rotate_proxy_if_needed, but good to keep
            'state_blocks': {state: 0 for state in self.us_states}, # Not currently used by _rotate_proxy_if_needed
            'state_delays': {state: 1 for state in self.us_states},  # Not currently used by _rotate_proxy_if_needed
            'circuits': {state: {'is_open': False, 'failure_count': 0, 'last_failure_time': 0, 'reset_timeout': 180} for state in self.us_states},
            'rotation_interval': 60,  # Base interval in seconds
            'last_rotation_time': 0, # Initialize to 0 to ensure first rotation happens
            'last_rotation': 0,  # For compatibility with existing code
            'consecutive_blocks': 0, # Not currently used by _rotate_proxy_if_needed
            'global_backoff': 1,  # Global backoff multiplier
            'block_count': 0,  # Count of recent blocks, used by _rotate_proxy_if_needed
            'last_block_time': 0  # Time of the last block, initialize to 0
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
        print(f"\n===== STARTING SEARCH FOR: {query} =====\n")
        print(f"DEBUG: search_google initiated for query: '{query}'") # DEBUG
        
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&gl=us&hl=en&cr=countryUS&pws=0"
        print(f"Search URL: {search_url}")
        
        all_methods_tried = False
        results = [] # Initialize results as an empty list

        if OXYLABS_CONFIGURED:
            print("DEBUG: OXYLABS_CONFIGURED is True. Trying Oxylabs methods.") # DEBUG
            print("Using Oxylabs for reliable Google search results")
            
            print("DEBUG: Attempting _search_with_oxylabs_direct_http") # DEBUG
            results = await self._search_with_oxylabs_direct_http(query, num_results)
            print(f"DEBUG: _search_with_oxylabs_direct_http returned: {len(results) if results else 'None' } results.") # DEBUG
            
            if results and len(results) > 0:
                print(f"Found {len(results)} results with Oxylabs direct HTTP method")
                return results
            
            print("DEBUG: Oxylabs direct HTTP failed. Attempting _search_with_oxylabs_proxy (crawler)") # DEBUG
            results = await self._search_with_oxylabs_proxy(query, search_url, num_results)
            print(f"DEBUG: _search_with_oxylabs_proxy returned: {len(results) if results else 'None'} results.") # DEBUG

            if results and len(results) > 0:
                print(f"Found {len(results)} results with Oxylabs proxy crawler")
                return results
            
            all_methods_tried = True
            print("DEBUG: Both Oxylabs methods failed or returned no results.") # DEBUG
        
        else: # DEBUG
            print("DEBUG: OXYLABS_CONFIGURED is False.") # DEBUG

        # Always try direct search as a fallback, regardless of whether Oxylabs was tried
        print("DEBUG: Attempting _direct_search_google as fallback.") # DEBUG
        results = await self._direct_search_google(query, search_url, num_results)
        print(f"DEBUG: _direct_search_google returned: {len(results) if results else 'None'} results.") # DEBUG
        
        if results and len(results) > 0:
            print(f"Found {len(results)} results with direct search method")
            return results
        
        print("DEBUG: All search methods attempted and failed to yield results.") # DEBUG
        print("All search methods failed. Please try again later or with a different query.")
        return []

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
        
        # Moderate rotation: 45-75 seconds
        base_interval = random.randint(45, 75)
        
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
            for state in self.us_states: # Use self.us_states instead of us_states
                circuit = self._proxy_state['circuits'][state] # Use 'circuits' instead of 'circuit_breaker'
                
                # Check if circuit is open (state is blocked)
                if circuit['is_open']:
                    # Check if it's time to try the state again (circuit half-open)
                    if current_time - circuit['last_failure_time'] > circuit['reset_timeout']: # Use 'last_failure_time' instead of 'last_attempt'
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
                
            # Add request throttling to avoid triggering Google's rate limiting
            # Wait a small random time before making the request
            throttle_time = random.uniform(0.5, 2.0)
            await asyncio.sleep(throttle_time)
            print(f"Request throttling: Waited {throttle_time:.2f}s before making request")
            
            # Get a random user agent
            selected_user_agent = self._get_random_user_agent()
            
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
                        print(f"Circuit breaker OPEN for {current_state}")
                    
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
        print(f"DEBUG: _process_google_html called for query: '{query}'. HTML snippet (first 500 chars): {html[:500] if html else 'None'}") # DEBUG
        search_results = []
        
        try:
            if not html or len(html) < 1000:
                print(f"Error: HTML content too short or empty for query '{query}'")
                return []
            
            # Use BeautifulSoup to parse the HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # More comprehensive check for CAPTCHA or block page
            captcha_indicators = [
                'Our systems have detected unusual traffic',
                'unusual traffic from your computer network',
                'Please try your request again later',
                'Type the text',
                'captcha',
                'security check',
                'confirm you\'re not a robot',
                'sorry for the inconvenience',
                'automated queries',
                'please click here if you are not redirected',
                'enable javascript',
                'detected unusual activity'
            ]
            
            html_lower = html.lower()
            for indicator in captcha_indicators:
                if indicator.lower() in html_lower:
                    print(f"Detected CAPTCHA or block page for query '{query}': {indicator}")
                    return []
            
            # Check for actual search result indicators
            search_indicators = ['search results', 'results for', 'showing results for']
            has_search_results = any(indicator in html_lower for indicator in search_indicators)
            
            if not has_search_results:
                print(f"Warning: HTML may not contain search results for query '{query}'")
                # Continue anyway, as some Google pages don't have these indicators
            
            # Try different selectors to find search results
            # Google periodically changes their HTML structure, so we need multiple approaches
            
            # Approach 1: Standard search result containers
            results = soup.select('div.tF2Cxc')
            if results:
                print(f"Found {len(results)} results with selector: div.tF2Cxc")
                
                # Extract data from each result
                urls = set()
                for result in results[:num_results*2]:  # Look at more results to find enough valid ones
                    # Extract URL
                    url_element = result.select_one('a')
                    if not url_element or not url_element.has_attr('href'):
                        continue
                        
                    url = url_element['href']
                    if not url.startswith('http') or 'google.com' in url:
                        continue
                        
                    # Skip if we already have this URL
                    if url in urls:
                        continue
                    urls.add(url)
                    
                    # Extract title
                    title_element = result.select_one('h3')
                    title = title_element.get_text() if title_element else 'No Title'
                    
                    # Extract snippet
                    snippet_element = result.select_one('div.VwiC3b')
                    snippet = snippet_element.get_text() if snippet_element else ''
                    
                    # Add to results
                    search_results.append({
                        'position': len(search_results) + 1,
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })
                    
                    # Stop if we have enough results
                    if len(search_results) >= num_results:
                        break
                
                print(f"Found {len(urls)} unique URLs")
                if search_results:
                    return search_results
            
            # Approach 2: Try alternative selectors if the first approach failed
            print("No results found with standard selectors, trying alternative methods")
            
            # Try a more generic selector - ordered by specificity
            selector_attempts = [
                'div.g',
                'div[data-sokoban-container]',
                'div.rc',
                'div[data-hveid]',
                # More generic fallbacks
                'div.yuRUbf',  # Another common container
                'h3.LC20lb',   # Title elements
                'div.NJo7tc',  # Another result container
                'div.v7W49e',  # Search result block
                'div.MjjYud',  # Outer container for results
                'a[href^="http"]'  # Last resort: any link
            ]
            
            for selector in selector_attempts:
                results = soup.select(selector)
                if results and len(results) > 0:
                    print(f"Found {len(results)} results with selector: {selector}")
                    break
                
            if results:
                # Extract URLs from generic results
                urls = set()
                for result in results[:num_results*3]:  # Look at more results to find enough valid ones
                    # For title elements, get the parent
                    if selector == 'h3.LC20lb':
                        result = result.parent.parent  # Navigate up to container
                    
                    # For direct links, use the element itself
                    if selector == 'a[href^="http"]':
                        url_element = result
                    else:
                        # Extract URL - try multiple approaches
                        url_element = (result.select_one('a[href^="http"]') or 
                                      result.select_one('a[ping]') or
                                      result.select_one('a'))
                    
                    if not url_element or not url_element.has_attr('href'):
                        continue
                        
                    url = url_element['href']
                    # Skip Google internal links and non-http links
                    if not url.startswith('http') or 'google.com' in url or '/search?' in url or '/url?' in url:
                        continue
                        
                    # Skip if we already have this URL
                    if url in urls:
                        continue
                    urls.add(url)
                    
                    # Extract title - try multiple approaches
                    title_element = (result.select_one('h3') or 
                                    result.select_one('h4') or 
                                    result.select_one('a > div') or
                                    url_element)  # Use link text as last resort
                    
                    title = title_element.get_text().strip() if title_element else 'No Title'
                    if not title or title == 'No Title':
                        # Try to extract from URL as last resort
                        from urllib.parse import urlparse
                        domain = urlparse(url).netloc
                        title = domain.replace('www.', '')
                    
                    # Extract snippet - try multiple approaches
                    snippet_selectors = [
                        'div[style*="-webkit-line-clamp"]',
                        'span.st', 
                        'div.s',
                        'div.VwiC3b',
                        'div.lEBKkf',
                        'div.yXK7lf',
                        'span.MUxGbd',
                        'div.lyLwlc'
                    ]
                    
                    snippet = ''
                    for s_selector in snippet_selectors:
                        snippet_element = result.select_one(s_selector)
                        if snippet_element:
                            snippet = snippet_element.get_text().strip()
                            break
                    
                    # Add to results
                    search_results.append({
                        'position': len(search_results) + 1,
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })
                    
                    # Stop if we have enough results
                    if len(search_results) >= num_results:
                        break
                
                print(f"Found {len(urls)} unique URLs")
                if search_results:
                    return search_results
            
            # If we still don't have results, try regex extraction
            print("Attempting to extract results with regex patterns")
            regex_results = await self._extract_results_with_regex(html, num_results)
            
            if regex_results and len(regex_results) > 0:
                return regex_results
                
            # Last resort: try to extract any URLs from the page
            print("Attempting last resort URL extraction")
            all_links = soup.find_all('a', href=True)
            urls = set()
            
            for link in all_links:
                url = link['href']
                if url.startswith('http') and 'google.com' not in url and '/search?' not in url and '/url?' not in url:
                    urls.add(url)
            
            if urls:
                print(f"Last resort found {len(urls)} potential URLs")
                results = []
                for i, url in enumerate(list(urls)[:num_results]):
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc
                    title = domain.replace('www.', '')
                    
                    results.append({
                        'position': i + 1,
                        'title': title,
                        'url': url,
                        'snippet': ''
                    })
                return results
            
            return []
            
        except Exception as e:
            print(f"Error processing Google HTML for query '{query}': {str(e)}")
            import traceback
            traceback.print_exc()
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
        print(f"DEBUG: _search_with_oxylabs_proxy TOP for query: '{query}'") # Initial Entry Log
        current_state = None
        proxy_config = None
        circuit = None
        try:
            print(f"DEBUG: Attempting proxy selection and config for query: '{query}'") # DEBUG
            current_state = self._rotate_proxy_if_needed(force_rotation=False)
            if not current_state:
                print("DEBUG: _rotate_proxy_if_needed returned no state. Exiting _search_with_oxylabs_proxy.") # DEBUG
                return []
            print(f"DEBUG: current_state selected: {current_state}") # DEBUG

            proxy_config = self._get_proxy_config(current_state)
            if not proxy_config:
                print(f"DEBUG: _get_proxy_config failed for state {current_state}. Exiting _search_with_oxylabs_proxy.") # DEBUG
                return []
            print(f"DEBUG: proxy_config obtained: {proxy_config.get('proxy_url')[:30]}...") # DEBUG
            
            circuit = self._proxy_state['circuits'].get(current_state)
            print(f"DEBUG: Circuit for {current_state}: {'Exists' if circuit else 'Not Found'}") # DEBUG
            if circuit and circuit['is_open'] and time.time() < circuit['last_failure_time'] + circuit['reset_timeout']:
                print(f"Circuit breaker OPEN for {current_state}. Skipping proxy.")
                return []
            print(f"DEBUG: Proxy setup complete for {current_state}. Proceeding to crawl.") # DEBUG

        except Exception as e_init:
            print(f"CRITICAL ERROR during proxy setup in _search_with_oxylabs_proxy: {str(e_init)}")
            import traceback
            traceback.print_exc() # Print full traceback for setup errors
            return []

        # Remainder of the method starts here, using current_state, proxy_config, circuit
        print(f"Using Oxylabs proxy with crawler: {current_state} (Session: {proxy_config['session_id'] if proxy_config else 'N/A'})")
        
        result_obj = None # For storing the result from crawler.arun()
        try:
            async with AsyncWebCrawler(proxy=proxy_config['proxy_url']) as crawler:
                print(f"DEBUG: AsyncWebCrawler (proxy) initialized. Proxy: {proxy_config['proxy_url']}") # DEBUG
                try:
                    print(f"DEBUG: Starting Oxylabs proxy crawl4ai with timeout...") # DEBUG
                    result_obj = await asyncio.wait_for(
                        crawler.arun(
                            search_url,
                            headless=self.headless,
                            user_agent=self._get_random_user_agent(),
                            cache_mode="bypass",
                            wait_until="networkidle",
                            page_timeout=20000, # Increased page timeout to 20s
                            delay_before_return_html=1.0, # Increased delay to 1s
                            word_count_threshold=100,
                            scan_full_page=True,
                            scroll_delay=0.5,
                            remove_overlay_elements=True
                        ),
                        timeout=30.0  # Overall timeout 30s
                    )
                    print(f"DEBUG: Oxylabs proxy crawl4ai completed.") # DEBUG
                except asyncio.TimeoutError:
                    print(f"Oxylabs proxy crawl4ai operation timed out after 30 seconds for {current_state}")
                    if circuit: circuit['failure_count'] += 1
                    self._proxy_state['block_count'] += 1
                    self._proxy_state['last_block_time'] = time.time()
                    self._proxy_state['global_backoff'] = min(10, self._proxy_state['global_backoff'] * 1.5)
                    return []
                except Exception as e:
                    print(f"Error during Oxylabs proxy crawl4ai operation for {current_state}: {str(e)}")
                    if circuit: circuit['failure_count'] += 1
                    return []

            # DEBUG: Inspect the result_obj from crawler.arun()
            if result_obj:
                print(f"DEBUG (proxy crawler): result_obj.success: {result_obj.success}")
                print(f"DEBUG (proxy crawler): result_obj.error_message: {result_obj.error_message if hasattr(result_obj, 'error_message') else 'No error message'}")
                print(f"DEBUG (proxy crawler): result_obj.status_code: {result_obj.status_code if hasattr(result_obj, 'status_code') else 'No status code'}")
                
                # Check if result_obj has html attribute
                if hasattr(result_obj, 'html') and result_obj.html:
                    html_snippet = result_obj.html[:500]
                    print(f"DEBUG (proxy crawler): result_obj.html snippet length: {len(result_obj.html)}")
                    print(f"DEBUG (proxy crawler): result_obj.html snippet: {html_snippet}")
                    
                    # Check for CAPTCHA or block indicators in the HTML
                    block_indicators = [
                        "captcha", "unusual traffic", "sorry", "automated", "robot", 
                        "security check", "confirm you're not a robot", "detected unusual activity"
                    ]
                    is_blocked = any(indicator in result_obj.html.lower() for indicator in block_indicators)
                    if is_blocked:
                        print(f"DEBUG (proxy crawler): CAPTCHA or block detected in HTML content")
                else:
                    print("DEBUG (proxy crawler): result_obj.html is None or not available")
            else:
                print("DEBUG (proxy crawler): result_obj is None after crawl.")
                if circuit: circuit['failure_count'] += 1 # Count as failure if result_obj is None
                return []

            if not result_obj.success:
                print(f"Error searching with Oxylabs proxy crawler ({current_state}): {result_obj.error_message}")
                if circuit: 
                    circuit['failure_count'] += 1
                    circuit['last_failure_time'] = time.time()
                    if "captcha" in str(result_obj.error_message).lower() or "block" in str(result_obj.error_message).lower() or (result_obj.status_code and result_obj.status_code == 403):
                        print(f"CAPTCHA or block detected for {current_state}. Incrementing failure count aggressively.")
                        circuit['failure_count'] = max(circuit['failure_count'], 2) # Treat as major failure
                        self._proxy_state['block_count'] += 1
                        self._proxy_state['last_block_time'] = time.time()
                        self._proxy_state['global_backoff'] = min(10, self._proxy_state['global_backoff'] * 2)
                        # Force immediate proxy rotation on next suitable call
                        self._proxy_state['last_rotation'] = 0 

                    if circuit['failure_count'] >= 2:
                        circuit['is_open'] = True
                        circuit['reset_timeout'] = min(900, 180 * (2 ** (circuit['failure_count'] - 2)))
                        print(f"Circuit breaker OPEN for {current_state}")
                return []
            
            if circuit: # Reset failure count on success
                circuit['failure_count'] = 0
                circuit['is_open'] = False 
                print(f"Successful crawl with {current_state}, circuit breaker reset.")

            html_content = result_obj.html
            search_results = await self._process_google_html(html_content, query, num_results)
            
            if search_results and len(search_results) > 0:
                return search_results
            else:
                # Try regex extraction as a last resort if HTML processing yields no results
                return await self._extract_results_with_regex(html_content, num_results)
                
        except Exception as e:
            print(f"Overall error in _search_with_oxylabs_proxy ({current_state}): {str(e)}")
            if circuit: circuit['failure_count'] += 1
            return []

    def _get_proxy_config(self, state):
        """
        Generate proxy configuration for a given state.
        Returns a dictionary with proxy_url and session_id.
        """
        if not state or not OXYLABS_CONFIGURED:
            return None
            
        # Generate a unique session ID for this request
        session_id = random.randint(10000, 99999)
        
        # Set up the proxy with enhanced authentication
        # Format: username-country-state-session_id-session_duration
        proxy_username = f"{OXYLABS_USERNAME}-st-{state}-sessid-{session_id}-sesstime-3"
        proxy_url = f"http://{proxy_username}:{OXYLABS_PASSWORD}@pr.oxylabs.io:7777"
        
        return {
            'proxy_url': proxy_url,
            'session_id': session_id,
            'state': state
        }
        
    def _rotate_proxy_if_needed(self, force_rotation=False):
        """
        Determine if proxy rotation is needed and select the next proxy state.
        Manages rotation intervals, block counts, and circuit breakers.
        Returns the selected proxy state (e.g., 'us_florida') or None if no suitable proxy is found.
        """
        current_time = time.time()
        
        # Define the list of US states for proxy rotation
        # This should ideally be part of self._proxy_state initialization or a class constant
        us_states = [
            "us_florida", "us_california", "us_massachusetts", "us_north_carolina",
            "us_south_carolina", "us_nevada", "us_new_york", "us_texas",
            "us_illinois", "us_washington", "us_arizona", "us_colorado",
            "us_georgia", "us_michigan", "us_ohio", "us_pennsylvania",
            "us_virginia", "us_new_jersey", "us_minnesota", "us_oregon"
        ]
        
        # Initialize 'circuits' and 'last_used_proxy_index' if they don't exist
        if 'circuits' not in self._proxy_state:
            self._proxy_state['circuits'] = {state: {'is_open': False, 'failure_count': 0, 'last_failure_time': 0, 'reset_timeout': 180} for state in us_states}
        if 'last_used_proxy_index' not in self._proxy_state:
            self._proxy_state['last_used_proxy_index'] = -1 # Start before the first state

        rotation_interval = self._proxy_state.get('rotation_interval', 60) 
        # Adjust interval based on global backoff and recent blocks
        effective_interval = rotation_interval * self._proxy_state.get('global_backoff', 1)
        if self._proxy_state.get('block_count', 0) > 2:
             # Reduce interval significantly if many blocks
            effective_interval = min(effective_interval, random.randint(15, 45)) 
        
        time_since_last_rotation = current_time - self._proxy_state.get('last_rotation_time', 0)
        
        if not force_rotation and time_since_last_rotation < effective_interval:
            # No rotation needed, return current state if valid
            last_state = self._proxy_state.get('last_state')
            if last_state and self._proxy_state['circuits'].get(last_state, {}).get('is_open', False) == False:
                # print(f"DEBUG: No rotation needed. Using last state: {last_state}")
                return last_state
            # If last state is invalid or circuit is open, force rotation
            # print(f"DEBUG: Last state '{last_state}' invalid or circuit open. Forcing rotation.")
            force_rotation = True 

        # Attempt to find the next available proxy
        for _ in range(len(us_states) + 1): # Iterate through states, plus one to try resetting if all fail
            self._proxy_state['last_used_proxy_index'] = (self._proxy_state['last_used_proxy_index'] + 1) % len(us_states)
            next_state = us_states[self._proxy_state['last_used_proxy_index']]
            
            circuit = self._proxy_state['circuits'].get(next_state)
            if not circuit: # Initialize if missing (should not happen with proper init)
                self._proxy_state['circuits'][next_state] = {'is_open': False, 'failure_count': 0, 'last_failure_time': 0, 'reset_timeout': 180}
                circuit = self._proxy_state['circuits'][next_state]

            if circuit['is_open']:
                if current_time > circuit.get('last_failure_time', 0) + circuit.get('reset_timeout', 180):
                    print(f"Circuit breaker for {next_state} has reset. Trying again.")
                    circuit['is_open'] = False
                    circuit['failure_count'] = 0
                else:
                    # print(f"DEBUG: Skipping {next_state}, circuit breaker is open.")
                    continue # Skip this state, try next
            
            # This state is available
            print(f"DEBUG: Rotating proxy to: {next_state}. Effective interval: {effective_interval:.2f}s. Forced: {force_rotation}")
            self._proxy_state['last_state'] = next_state
            self._proxy_state['last_rotation_time'] = current_time
            return next_state

        print("WARNING: All proxy states have open circuit breakers or failed. Resetting all and trying default.")
        # If all proxies are in a bad state, reset all circuit breakers as a last resort
        for state_key in self._proxy_state['circuits']:
            self._proxy_state['circuits'][state_key]['is_open'] = False
            self._proxy_state['circuits'][state_key]['failure_count'] = 0
        self._proxy_state['last_used_proxy_index'] = 0 # Reset index
        default_state = us_states[0]
        self._proxy_state['last_state'] = default_state
        self._proxy_state['last_rotation_time'] = current_time
        print(f"DEBUG: All circuits reset. Using default state: {default_state}")
        return default_state

    async def _direct_search_google(self, query, search_url, num_results=6):
        """
        Search Google directly without proxies
        """
        # Initialize result to handle cases where crawler setup might fail
        result = None 
        try:
            print(f"Using direct search method for query: {query}")
            
            # Use AsyncWebCrawler without a proxy
            try:
                print(f"Starting direct crawl4ai with timeout...")
                import asyncio
                async with AsyncWebCrawler() as crawler:
                    # Create a task for the crawler operation with a timeout
                    try:
                        result = await asyncio.wait_for(
                            crawler.arun(
                                search_url,
                                headless=self.headless,
                                user_agent=self._get_random_user_agent(), # Ensure this calls the class method
                                cache_mode="bypass",
                                wait_until="networkidle",
                                page_timeout=15000,  # Reduced timeout to 15 seconds
                                delay_before_return_html=0.5,
                                word_count_threshold=100,
                                scan_full_page=True,
                                scroll_delay=0.3,
                                remove_overlay_elements=True
                            ),
                            timeout=20.0  # 20 second timeout for the entire operation
                        )
                        print(f"Direct crawl4ai completed successfully")
                    except asyncio.TimeoutError:
                        print(f"Direct crawl4ai operation timed out after 20 seconds")
                        return []
            except Exception as e:
                print(f"Error setting up or running direct crawl4ai: {str(e)}")
                return []
                
            if result is None: # Check if crawler operation failed to assign result
                print(f"Direct crawl4ai did not return a result, possibly due to setup error.")
                return []

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
            print(f"Overall error in _direct_search_google: {str(e)}")
            return []

    def _get_random_user_agent(self):
        """
        Return a random user agent string to avoid detection.
        Uses more modern browser versions to appear legitimate.
        """
        user_agents = [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
        ]
        return random.choice(user_agents)

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
        print(f"Calling search_google with query: {query}, num_results: {num_results}")
        search_results = await self.search_google(query, num_results)
        print(f"Returned from search_google call")
        
        # Print diagnostic information
        print(f"Search results type: {type(search_results)}")
        
        # Handle case where search_results is None
        if search_results is None:
            print(f"Search results is None")
            search_results = []
        
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
    print("Initializing SERP Analyzer...")
    analyzer = SerpAnalyzer(headless=False)  # Set to True for headless mode
    
    # Check for command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='SERP Analyzer Tool')
    parser.add_argument('query', nargs='?', help='Search query to analyze')
    parser.add_argument('--results', '-r', type=int, default=6, help='Number of results to analyze (default: 6)')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    print(f"Command line args: query='{args.query}', results={args.results}, debug={args.debug}")
    
    # Get query from command line args or user input
    query = args.query
    if not query:
        query = input("Enter your search query: ")
    
    # Get number of results from command line args or user input
    num_results = args.results
    if not num_results:
        num_results = int(input("Number of results to analyze (default 6): ") or "6")
    
    # Perform SERP analysis
    print(f"Starting SERP analysis for query: {query}")
    serp_analysis = await analyzer.analyze_serp(query, num_results)
    print(f"SERP analysis completed")
    
    # Save results
    print(f"Saving results to JSON...")
    analyzer.save_results(serp_analysis, "json")
    print(f"Saving results to CSV...")
    analyzer.save_results(serp_analysis, "csv")
    print(f"Results saved")
    
    print("\nAnalysis complete!")
    print(f"Analyzed {len(serp_analysis['results'])} search results for query: {query}")


if __name__ == "__main__":
    asyncio.run(main())
