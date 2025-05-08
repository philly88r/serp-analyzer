import os
import sys
import json
import csv
import time
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
        
        try:
            # Prepare the search URL
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&gl=us&hl=en&pws=0&safe=off&num={num_results}"
            
            # Generate a unique session ID to maintain the same IP for multiple requests
            import uuid
            session_id = str(uuid.uuid4())[:12]
            
            # Create username with country and session parameters
            # Format: customer-USERNAME-cc-US-sessid-SESSION_ID-sesstime-10
            # This targets US proxies and maintains the same IP for 10 minutes
            enhanced_username = f"{OXYLABS_USERNAME}-cc-US-sessid-{session_id}-sesstime-10"
            
            print(f"Using Oxylabs with enhanced parameters: country=US, session={session_id}")
            
            # Set up the proxy with enhanced authentication
            # Using the proxy port 7777 which is recommended for country-specific targeting
            proxy_url = "pr.oxylabs.io:7777"
            proxies = {
                "http": f"http://{enhanced_username}:{OXYLABS_PASSWORD}@{proxy_url}",
                "https": f"http://{enhanced_username}:{OXYLABS_PASSWORD}@{proxy_url}"
            }
            
            # Set up headers to look like a real browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.google.com/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0"
            }
            
            print(f"Making direct HTTP request to {search_url} via Oxylabs country-specific proxy")
            
            # Make the request
            response = requests.get(
                search_url,
                proxies=proxies,
                headers=headers,
                timeout=30
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                # Save the HTML for debugging
                html_content = response.text
                print(f"HTML preview: {html_content[:500]}...")
                
                # Check if we got a CAPTCHA page
                if "captcha" in html_content.lower() or "unusual traffic" in html_content.lower():
                    print("DETECTED: Google CAPTCHA page in direct HTTP request")
                    return []
                
                # Process the HTML response
                return await self._process_google_html(html_content, query, num_results)
            else:
                print(f"Error from Google: {response.status_code} - {response.reason}")
        
        except Exception as e:
            print(f"Error using direct HTTP request with Oxylabs proxy: {str(e)}")
        
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
                "ignore_default_args": ["--disable-extensions"],
                "timeout": 90000  # Extended timeout for Heroku
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
            "page_timeout": 90000,  # Increased timeout for slower connections
            "delay_before_return_html": 2.0,  # Increased delay for better rendering
            "word_count_threshold": 100,
            "scan_full_page": True,
            "scroll_delay": 0.8,
            "process_iframes": False,
            "remove_overlay_elements": True,
            "magic": True
        }
        
        # Add Heroku-specific options
        if self.is_heroku:
            print(f"Using Heroku-specific browser options for analyzing {url}")
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
                "ignore_default_args": ["--disable-extensions"],
                "timeout": 90000  # Extended timeout for Heroku
            })
        
        try:
            # Create a new crawler with no config to avoid the verbose parameter conflict
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(**browser_options)
                
                # Check if the result was successful
                if not hasattr(result, 'success') or not result.success:
                    error_message = getattr(result, 'error_message', 'Unknown error')
                    print(f"Error analyzing page: {error_message}")
                    default_result["error"] = error_message
                    return default_result
                
                # Check if HTML content exists
                if not hasattr(result, 'html') or not result.html:
                    print("Could not find HTML content in the result object")
                    default_result["error"] = "No HTML content found"
                    return default_result
                
                # Parse the HTML with BeautifulSoup
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.html, 'html.parser')
                
                # Basic SEO data - with error handling for each step
                try:
                    default_result["title"] = soup.title.get_text() if soup.title else ""
                except Exception as e:
                    print(f"Error extracting title: {str(e)}")
                
                # Extract meta tags
                try:
                    for meta in soup.find_all("meta"):
                        if meta.get("name", "").lower() == "description":
                            default_result["meta_description"] = meta.get("content", "")
                        elif meta.get("name", "").lower() == "keywords":
                            default_result["meta_keywords"] = meta.get("content", "")
                except Exception as e:
                    print(f"Error extracting meta tags: {str(e)}")
                
                # Extract headings
                try:
                    default_result["h1_tags"] = [h1.get_text().strip() for h1 in soup.find_all("h1")]
                    default_result["h2_tags"] = [h2.get_text().strip() for h2 in soup.find_all("h2")]
                    default_result["h3_tags"] = [h3.get_text().strip() for h3 in soup.find_all("h3")]
                except Exception as e:
                    print(f"Error extracting headings: {str(e)}")
                
                # Extract links
                try:
                    internal_links = []
                    external_links = []
                    base_domain = url.split("//")[-1].split("/")[0]
                    
                    for link in soup.find_all("a", href=True):
                        href = link["href"]
                        if href.startswith("#") or not href or href == "/":
                            continue
                        
                        # Normalize URL
                        if href.startswith("/"):
                            full_url = f"{url.split('//')[0]}//{base_domain}{href}"
                            internal_links.append(full_url)
                        elif base_domain in href:
                            internal_links.append(href)
                        elif href.startswith("http"):
                            external_links.append(href)
                    
                    default_result["internal_links"] = internal_links
                    default_result["external_links"] = external_links
                except Exception as e:
                    print(f"Error extracting links: {str(e)}")
                
                # Extract images
                try:
                    images = []
                    for img in soup.find_all("img", src=True):
                        try:
                            src = img["src"]
                            alt = img.get("alt", "")
                            
                            # Normalize image URL
                            if src.startswith("/"):
                                src = f"{url.split('//')[0]}//{base_domain}{src}"
                            elif not src.startswith("http"):
                                src = f"{url.rstrip('/')}/{src.lstrip('/')}"
                            
                            images.append({
                                "src": src,
                                "alt": alt
                            })
                        except Exception as img_error:
                            print(f"Error processing image: {str(img_error)}")
                            continue
                    
                    default_result["images"] = images
                except Exception as e:
                    print(f"Error extracting images: {str(e)}")
                
                # Page content analysis
                try:
                    # Extract text from the soup object
                    content_text = soup.get_text()
                    default_result["word_count"] = len(content_text.split())
                    
                    # Get a preview of the content
                    content_preview = " ".join(content_text.split()[:100])
                    default_result["content_preview"] = content_preview
                except Exception as e:
                    print(f"Error analyzing content: {str(e)}")
                
                # Mark as successful
                default_result["success"] = True
                
                return default_result
                
        except Exception as e:
            print(f"Error analyzing page {url}: {str(e)}")
            default_result["error"] = str(e)
            return default_result
            
            # Get clean markdown content
            # Check if the result has a markdown attribute
            markdown_content = ""
            if hasattr(result, 'markdown'):
                markdown_content = result.markdown
            else:
                # If markdown is not available, use the text content
                markdown_content = content_text
            
            # Compile analysis data
            analysis = {
                "url": url,
                "success": True,
                "title": title,
                "meta_description": meta_description,
                "meta_keywords": meta_keywords,
                "h1_tags": h1_tags,
                "h2_tags": h2_tags,
                "h3_tags": h3_tags,
                "word_count": word_count,
                "internal_links_count": len(internal_links),
                "external_links_count": len(external_links),
                "images_count": len(images),
                "content_text": content_text,
                "markdown_content": markdown_content,
                "internal_links": internal_links[:10],  # Limit to first 10 links
                "external_links": external_links[:10],  # Limit to first 10 links
                "images": images[:10]  # Limit to first 10 images
            }
            
            return analysis
    
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
