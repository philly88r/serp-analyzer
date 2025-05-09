import asyncio
import json
import os
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import random
import traceback
import time

class FixedSerpAnalyzer:
    """
    Fixed version of SerpAnalyzer that uses direct HTTP requests
    to reliably extract search results from Google while avoiding detection.
    """
    
    def __init__(self, headless=True):
        """Initialize the fixed SERP analyzer."""
        self.headless = headless
        self._initialize_user_agents()
        self._initialize_proxy_state()
    
    def _initialize_user_agents(self):
        """Initialize a list of modern user agents."""
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.83 Safari/537.36"
        ]
    
    def _initialize_proxy_state(self):
        """
        Initialize the proxy state tracking dictionary with diverse US states
        """
        self.proxy_states = {
            "california": {"blocks": 0, "last_used": None},
            "new_york": {"blocks": 0, "last_used": None},
            "texas": {"blocks": 0, "last_used": None},
            "florida": {"blocks": 0, "last_used": None},
            "illinois": {"blocks": 0, "last_used": None},
            "washington": {"blocks": 0, "last_used": None},
            "massachusetts": {"blocks": 0, "last_used": None},
            "virginia": {"blocks": 0, "last_used": None},
            "colorado": {"blocks": 0, "last_used": None},
            "georgia": {"blocks": 0, "last_used": None},
            "oregon": {"blocks": 0, "last_used": None},
            "arizona": {"blocks": 0, "last_used": None},
            "pennsylvania": {"blocks": 0, "last_used": None},
            "michigan": {"blocks": 0, "last_used": None},
            "ohio": {"blocks": 0, "last_used": None},
        }
        self.current_proxy_state = random.choice(list(self.proxy_states.keys()))  # Start with a random state
        self.proxy_rotation_interval = 60  # 1 minute in seconds - more frequent rotation
    
    def _get_random_user_agent(self):
        """Get a random user agent from the list."""
        return random.choice(self.user_agents)
    
    async def search_google(self, query, num_results=6):
        """
        Search Google for a query and return the results.
        Uses direct HTTP request for reliable extraction.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to return
            
        Returns:
            list: A list of search result dictionaries
        """
        try:
            print(f"Searching Google for: {query}")
            
            # Construct the search URL
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results*2}&gl=us&hl=en&cr=countryUS&pws=0"
            
            # Try direct HTTP request first (most reliable method based on testing)
            results = await self._search_with_direct_http(query, search_url, num_results)
            
            # If direct HTTP request succeeds, return the results
            if results and len(results) > 0:
                print(f"Direct HTTP request returned {len(results)} results")
                return results
            
            # If direct HTTP request fails, try with AsyncWebCrawler
            print(f"Direct HTTP request failed. Trying with AsyncWebCrawler...")
            results = await self._search_with_crawler(query, search_url, num_results)
            
            # Print summary of results
            if results and len(results) > 0:
                print(f"Found {len(results)} results for query: {query}")
            else:
                print(f"No results found for query: {query}")
            
            return results
            
        except Exception as e:
            print(f"Error searching Google: {str(e)}")
            traceback.print_exc()
            return []
    
    async def _search_with_direct_http(self, query, search_url, num_results=6):
        """
        Search Google using a direct HTTP request.
        This method has proven more reliable for extracting search results.
        """
        try:
            # Set up headers with a random user agent
            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.google.com/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            print(f"Making direct HTTP request to: {search_url}")
            
            # Make the request
            response = requests.get(search_url, headers=headers, timeout=10)
            
            print(f"Direct HTTP request status code: {response.status_code}")
            
            # Check if the request was successful
            if response.status_code != 200:
                print(f"Direct HTTP request failed with status code {response.status_code}")
                return []
            
            # Get the HTML content
            html_content = response.text
            
            # Check for CAPTCHA or block page
            if "captcha" in html_content.lower() or "unusual traffic" in html_content.lower():
                print("CAPTCHA or block detected in direct HTTP response")
                return []
            
            # Save the HTML for debugging
            try:
                with open("direct_http_response.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("Saved HTML to direct_http_response.html for debugging")
            except Exception as e:
                print(f"Could not save HTML for debugging: {str(e)}")
            
            # Extract search results
            return await self._extract_results_from_html(html_content, query, num_results)
            
        except Exception as e:
            print(f"Error in direct HTTP request: {str(e)}")
            traceback.print_exc()
            return []
    
    async def _search_with_crawler(self, query, search_url, num_results=6):
        """
        Search Google using AsyncWebCrawler.
        """
        try:
            from crawl4ai import AsyncWebCrawler
            
            print("Initializing AsyncWebCrawler...")
            
            async with AsyncWebCrawler() as crawler:
                try:
                    # Use a random user agent
                    user_agent = self._get_random_user_agent()
                    
                    # Add random delay before search
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                    
                    # Perform the search
                    result = await asyncio.wait_for(
                        crawler.arun(
                            search_url,
                            headless=self.headless,
                            user_agent=user_agent,
                            cache_mode="bypass",
                            wait_until="networkidle",
                            page_timeout=15000,  # 15 seconds timeout
                            delay_before_return_html=random.uniform(1.0, 2.0),
                            word_count_threshold=100,
                            scan_full_page=True,
                            scroll_delay=random.uniform(0.3, 0.7),
                            remove_overlay_elements=True
                        ),
                        timeout=20.0  # 20 second timeout for the entire operation
                    )
                    print("AsyncWebCrawler completed successfully")
                except asyncio.TimeoutError:
                    print("AsyncWebCrawler operation timed out")
                    return []
                except Exception as e:
                    print(f"Error using AsyncWebCrawler: {str(e)}")
                    traceback.print_exc()
                    return []
            
            # Check if the result was successful
            if not result or not result.success:
                print(f"Error searching with AsyncWebCrawler: {result.error_message if result else 'No result'}")
                return []
            
            # Get the HTML content
            html_content = result.html
            if not html_content or len(html_content) < 1000:
                print(f"AsyncWebCrawler did not return valid HTML content (length: {len(html_content) if html_content else 0})")
                return []
            
            # Save the HTML for debugging
            with open("crawler_response.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("Saved HTML to crawler_response.html for debugging")
            
            # Check for CAPTCHA or block page
            if "captcha" in html_content.lower() or "unusual traffic" in html_content.lower():
                print("CAPTCHA or block detected in AsyncWebCrawler response")
                return []
            
            # Extract search results
            return await self._extract_results_from_html(html_content, query, num_results)
            
        except Exception as e:
            print(f"Error in AsyncWebCrawler search: {str(e)}")
            traceback.print_exc()
            return []
    
    async def _extract_results_from_html(self, html_content, query, num_results=6):
        """
        Extract search results from HTML content using multiple methods.
        This is a more robust extraction method that works with various HTML structures.
        """
        try:
            # Parse the HTML
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Method 1: Look for all links
            links = soup.find_all("a")
            print(f"Found {len(links)} links in HTML")
            
            # Filter links that look like search results
            result_links = []
            for link in links:
                href = link.get("href", "")
                if href.startswith("http") and "google" not in href.lower():
                    # Get the title from the link text or nearby h3
                    title = link.get_text().strip()
                    if not title:
                        # Try to find a nearby h3
                        parent = link.parent
                        for _ in range(3):  # Look up to 3 levels up
                            if parent and parent.find("h3"):
                                title = parent.find("h3").get_text().strip()
                                break
                            if parent:
                                parent = parent.parent
                    
                    # Skip if no title
                    if not title:
                        continue
                    
                    # Try to find a description
                    description = ""
                    parent = link.parent
                    for _ in range(3):  # Look up to 3 levels up
                        if parent:
                            # Find any div that might contain a description
                            for div in parent.find_all("div"):
                                text = div.get_text().strip()
                                if len(text) > 50 and text != title:  # Reasonable description length
                                    description = text
                                    break
                            if description:
                                break
                            parent = parent.parent
                    
                    # Add to results
                    result_links.append({
                        "title": title,
                        "url": href,
                        "description": description,
                        "position": len(result_links) + 1,
                        "query": query
                    })
                    
                    # Stop once we have enough results
                    if len(result_links) >= num_results:
                        break
            
            print(f"Extracted {len(result_links)} search results")
            
            # Save the results for debugging
            try:
                with open("extracted_results.json", "w", encoding="utf-8") as f:
                    json.dump(result_links, f, indent=2, ensure_ascii=False)
                print("Saved results to extracted_results.json")
            except Exception as e:
                print(f"Could not save results: {str(e)}")
            
            return result_links
            
        except Exception as e:
            print(f"Error extracting results from HTML: {str(e)}")
            traceback.print_exc()
            return []
    
    async def analyze_serp(self, query, num_results=6):
        """
        Analyze SERP for a given query.
        This is a wrapper around search_google for compatibility with existing code.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to return
            
        Returns:
            list: A list of search result dictionaries
        """
        try:
            print(f"Analyzing SERP for query: {query}")
            
            # Get search results
            results = await self.search_google(query, num_results)
            
            # Print debugging information
            print(f"analyze_serp found {len(results) if results else 0} results")
            print(f"Results type: {type(results)}")
            
            # Return the results
            return results
        except Exception as e:
            print(f"Error in analyze_serp: {str(e)}")
            traceback.print_exc()
            return []

async def test_fixed_analyzer():
    """Test the fixed SERP analyzer with a sample query."""
    print("\n" + "="*80)
    print(" FIXED SERP ANALYZER TEST ".center(80, "="))
    print("="*80 + "\n")
    
    # Initialize the analyzer
    analyzer = FixedSerpAnalyzer(headless=True)
    
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
        output_file = "fixed_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved complete results to {output_file}")
    else:
        print("NO RESULTS FOUND.")
        print("Please check the logs for any errors.")

if __name__ == "__main__":
    asyncio.run(test_fixed_analyzer())
