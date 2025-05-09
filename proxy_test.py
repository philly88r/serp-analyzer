import asyncio
import json
import os
import random
import time
from urllib.parse import quote_plus
import sys
import aiohttp
from bs4 import BeautifulSoup
import re

# Add the current directory to the path so we can import the SerpAnalyzer class
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from serp_analyzer import SerpAnalyzer

class ProxySerpAnalyzer(SerpAnalyzer):
    """
    Enhanced version of SerpAnalyzer with improved proxy rotation
    to bypass Google's anti-bot detection.
    """
    
    def __init__(self, headless=True):
        """Initialize the proxy SERP analyzer."""
        super().__init__(headless=headless)
        self._initialize_enhanced_proxy_state()
    
    def _initialize_enhanced_proxy_state(self):
        """Initialize enhanced proxy state with more frequent rotation."""
        # Initialize the standard proxy state
        self._initialize_proxy_state()
        
        # Override with enhanced settings
        self.proxy_rotation_interval = random.randint(60, 120)  # 1-2 minutes
        
        # Track blocks more aggressively
        self._proxy_state = {
            "block_count": 0,
            "last_block_time": 0,
            "last_rotation_time": 0,
            "global_backoff": 1.0,
            "rotation_interval": self.proxy_rotation_interval
        }
        
        print(f"Initialized enhanced proxy state with rotation interval: {self.proxy_rotation_interval}s")
    
    def _get_random_user_agent(self):
        """Get a random modern user agent."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.83 Safari/537.36"
        ]
        return random.choice(user_agents)
    
    async def search_google(self, query, num_results=6):
        """
        Search Google with enhanced proxy rotation.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to return
            
        Returns:
            list: A list of search result dictionaries
        """
        print(f"Enhanced proxy search for '{query}'")
        
        # Force proxy rotation before search
        self._rotate_proxy_if_needed(force_rotation=True)
        
        # Create the search URL
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results*2}&gl=us&hl=en"
        
        # Try direct search first
        results = await self._direct_search_google(query, search_url, num_results)
        
        # If direct search failed, try with Oxylabs proxy
        if not results or len(results) == 0:
            print("Direct search failed. Trying with Oxylabs proxy...")
            results = await self._search_with_oxylabs_proxy(query, search_url, num_results)
        
        # Print summary of results
        if results and len(results) > 0:
            print(f"Found {len(results)} results")
            
            # Save results to a file for debugging
            try:
                with open("proxy_search_results.json", "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print("Saved results to proxy_search_results.json")
            except Exception as e:
                print(f"Error saving results: {str(e)}")
        else:
            print("No results found")
        
        return results
    
    async def _search_with_oxylabs_proxy(self, query, search_url, num_results=6):
        """
        Search Google using Oxylabs proxy with improved error handling.
        """
        # Get the current proxy state
        current_state = self._rotate_proxy_if_needed()
        if not current_state:
            print("No valid proxy state available")
            return []
        
        print(f"Using Oxylabs proxy with state: {current_state}")
        
        # Get the proxy configuration
        proxy_config = self._get_proxy_config(current_state)
        if not proxy_config:
            print("Failed to get proxy configuration")
            return []
        
        # Get the circuit breaker for this state
        circuit = self._proxy_state.get('circuits', {}).get(current_state)
        
        try:
            from crawl4ai import AsyncWebCrawler
            
            print(f"Initializing AsyncWebCrawler with proxy: {proxy_config['proxy_url']}")
            
            async with AsyncWebCrawler(proxy=proxy_config['proxy_url']) as crawler:
                try:
                    print(f"Starting proxy crawl with timeout...")
                    
                    # Use a random user agent
                    user_agent = self._get_random_user_agent()
                    print(f"Using user agent: {user_agent[:30]}...")
                    
                    # Add random delay before search
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                    
                    # Perform the search with enhanced parameters
                    result_obj = await asyncio.wait_for(
                        crawler.arun(
                            search_url,
                            headless=self.headless,
                            user_agent=user_agent,
                            cache_mode="bypass",
                            wait_until="networkidle",
                            page_timeout=20000,  # 20 seconds timeout
                            delay_before_return_html=random.uniform(1.0, 2.0),
                            word_count_threshold=100,
                            scan_full_page=True,
                            scroll_delay=random.uniform(0.3, 0.7),
                            remove_overlay_elements=True
                        ),
                        timeout=30.0  # 30 second timeout for the entire operation
                    )
                    print(f"Proxy crawl completed successfully")
                except asyncio.TimeoutError:
                    print(f"Proxy crawl operation timed out after 30 seconds")
                    if circuit:
                        circuit['failure_count'] += 1
                    self._proxy_state['block_count'] += 1
                    self._proxy_state['last_block_time'] = time.time()
                    return []
                except Exception as e:
                    print(f"Error during proxy crawl: {str(e)}")
                    if circuit:
                        circuit['failure_count'] += 1
                    return []
            
            # Check if the result was successful
            if not result_obj or not result_obj.success:
                print(f"Error searching with proxy: {result_obj.error_message if result_obj else 'No result'}")
                if circuit:
                    circuit['failure_count'] += 1
                return []
            
            # Get the HTML content
            html_content = result_obj.html
            if not html_content or len(html_content) < 1000:
                print(f"Proxy crawl did not return valid HTML content (length: {len(html_content) if html_content else 0})")
                if circuit:
                    circuit['failure_count'] += 1
                return []
            
            # Save the HTML for debugging
            try:
                with open("proxy_google_search.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("Saved HTML to proxy_google_search.html for debugging")
            except Exception as e:
                print(f"Could not save HTML for debugging: {str(e)}")
            
            # Check for CAPTCHA or block page
            if "captcha" in html_content.lower() or "unusual traffic" in html_content.lower():
                print(f"CAPTCHA or block detected in HTML content")
                if circuit:
                    circuit['failure_count'] += 1
                self._proxy_state['block_count'] += 1
                self._proxy_state['last_block_time'] = time.time()
                return []
            
            # Reset circuit breaker on success
            if circuit:
                circuit['failure_count'] = 0
                circuit['is_open'] = False
            
            # Process the HTML to extract search results
            search_results = await self._process_google_html(html_content, query, num_results)
            
            if search_results and len(search_results) > 0:
                return search_results
            else:
                # Try regex extraction as a last resort
                return await self._extract_results_with_regex(html_content, num_results)
            
        except Exception as e:
            print(f"Overall error in proxy search: {str(e)}")
            import traceback
            traceback.print_exc()
            if circuit:
                circuit['failure_count'] += 1
            return []

async def test_proxy_analyzer():
    """Test the proxy SERP analyzer with a sample query."""
    print("\n" + "="*80)
    print(" PROXY SERP ANALYZER TEST ".center(80, "="))
    print("="*80 + "\n")
    
    # Initialize the proxy analyzer
    analyzer = ProxySerpAnalyzer(headless=True)
    
    # Test query
    query = "python tutorial"
    
    print(f"Testing query: '{query}'")
    
    # Search for the query
    results = await analyzer.search_google(query)
    
    # Print results summary
    print("\n" + "="*80)
    print(f" FOUND {len(results)} RESULTS ".center(80, "="))
    print("="*80 + "\n")
    
    if results:
        # Print each result with clear separation
        for i, result in enumerate(results):
            print(f"RESULT #{i+1}:")
            print(f"TITLE: {result.get('title', 'No title')}")
            print(f"URL: {result.get('url', 'No URL')}")
            print(f"DESCRIPTION: {result.get('description', 'No description')[:150]}")
            print("-"*80)
        
        # Save results to a JSON file with clear formatting
        output_file = "proxy_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved complete results to {output_file}")
    else:
        print("NO RESULTS FOUND.")
        print("Please check the logs for any errors.")

if __name__ == "__main__":
    asyncio.run(test_proxy_analyzer())
