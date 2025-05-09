import asyncio
import json
import os
import random
import time
from urllib.parse import quote_plus
import sys
from bs4 import BeautifulSoup
import re

# Add the current directory to the path so we can import the SerpAnalyzer class
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from serp_analyzer import SerpAnalyzer

class StealthSerpAnalyzer(SerpAnalyzer):
    """
    Enhanced version of SerpAnalyzer with improved stealth techniques
    to bypass Google's anti-bot detection.
    """
    
    def __init__(self, headless=True):
        """Initialize the stealth SERP analyzer."""
        super().__init__(headless=headless)
        self._initialize_stealth_config()
    
    def _initialize_stealth_config(self):
        """Initialize stealth configuration parameters."""
        # More realistic user agents
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
        ]
        
        # Increased delays for more human-like behavior
        self.page_load_delay = random.uniform(2.0, 4.0)
        self.scroll_delay = random.uniform(0.5, 1.5)
        self.typing_delay = random.uniform(0.1, 0.3)
        
        # Random viewport sizes for desktop
        self.viewport_sizes = [
            {"width": 1366, "height": 768},
            {"width": 1920, "height": 1080},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 720}
        ]
    
    def _get_random_user_agent(self):
        """Get a random user agent from the list."""
        return random.choice(self.user_agents)
    
    def _get_random_viewport(self):
        """Get a random viewport size."""
        return random.choice(self.viewport_sizes)
    
    async def _direct_search_google(self, query, search_url, num_results=6):
        """
        Search Google directly with enhanced stealth techniques.
        """
        try:
            print(f"Using stealth search method for query: {query}")
            
            import asyncio
            from crawl4ai import AsyncWebCrawler
            
            # Get random parameters for this search
            user_agent = self._get_random_user_agent()
            viewport = self._get_random_viewport()
            
            print(f"Using user agent: {user_agent[:30]}...")
            print(f"Using viewport: {viewport}")
            
            try:
                print(f"Starting AsyncWebCrawler with stealth mode...")
                
                # Create custom browser arguments to enhance stealth
                browser_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                    "--disable-web-security",
                    f"--user-agent={user_agent}"
                ]
                
                async with AsyncWebCrawler() as crawler:
                    try:
                        # Apply stealth techniques before navigation
                        await crawler.setup_page(
                            viewport_width=viewport["width"],
                            viewport_height=viewport["height"],
                            browser_args=browser_args
                        )
                        
                        # Add random delay before search
                        await asyncio.sleep(random.uniform(1.0, 3.0))
                        
                        # Perform the search with enhanced parameters
                        result = await asyncio.wait_for(
                            crawler.arun(
                                search_url,
                                headless=self.headless,
                                user_agent=user_agent,
                                cache_mode="bypass",
                                wait_until="networkidle",
                                page_timeout=20000,  # 20 seconds timeout
                                delay_before_return_html=self.page_load_delay,
                                word_count_threshold=100,
                                scan_full_page=True,
                                scroll_delay=self.scroll_delay,
                                remove_overlay_elements=True,
                                browser_args=browser_args
                            ),
                            timeout=30.0  # 30 second timeout for the entire operation
                        )
                        print(f"AsyncWebCrawler completed successfully")
                    except asyncio.TimeoutError:
                        print(f"AsyncWebCrawler operation timed out after 30 seconds")
                        return []
                
                if not result.success:
                    print(f"Error searching with AsyncWebCrawler: {result.error_message}")
                    return []
                
                # Get the HTML content
                html_content = result.html
                if not html_content or len(html_content) < 1000:
                    print(f"AsyncWebCrawler did not return valid HTML content (length: {len(html_content) if html_content else 0})")
                    return []
                
                # Save the HTML for debugging
                try:
                    with open("stealth_google_search.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                    print("Saved HTML to stealth_google_search.html for debugging")
                except Exception as e:
                    print(f"Could not save HTML for debugging: {str(e)}")
                
                # Check for CAPTCHA or block page
                if "captcha" in html_content.lower() or "unusual traffic" in html_content.lower():
                    print(f"CAPTCHA or block detected in HTML content")
                    return []
                
                # Try multiple extraction methods
                
                # Method 1: Direct extraction
                search_results = self._extract_results_direct(html_content, query, num_results)
                if search_results and len(search_results) > 0:
                    print(f"Direct extraction method found {len(search_results)} results")
                    return search_results
                
                # Method 2: Process with BeautifulSoup
                search_results = await self._process_google_html(html_content, query, num_results)
                if search_results and len(search_results) > 0:
                    print(f"BeautifulSoup processing found {len(search_results)} results")
                    return search_results
                
                # Method 3: Regex extraction as last resort
                search_results = await self._extract_results_with_regex(html_content, num_results)
                if search_results and len(search_results) > 0:
                    print(f"Regex extraction found {len(search_results)} results")
                    return search_results
                
                print("All extraction methods failed to find results")
                return []
                
            except Exception as e:
                print(f"Error using AsyncWebCrawler: {str(e)}")
                import traceback
                traceback.print_exc()
                return []
        except Exception as e:
            print(f"Overall error in stealth search: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_results_direct(self, html_content, query, num_results=6):
        """
        Extract search results directly from HTML using BeautifulSoup.
        This method tries multiple selectors and approaches.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            search_results = []
            
            # 1. Try to find all result containers
            selectors = [
                'div.g', 'div.tF2Cxc', 'div.yuRUbf', 'div.rc', 
                'div[data-header-feature]', 'div.MjjYud', 'div.Gx5Zad',
                'div.v7W49e', 'div.jtfYYd', 'div.Z26q7c'
            ]
            
            for selector in selectors:
                containers = soup.select(selector)
                print(f"Selector '{selector}' found {len(containers)} elements")
                
                for container in containers:
                    # Try to extract title
                    title_elem = container.select_one('h3')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text().strip()
                    
                    # Try to extract URL
                    link_elem = container.select_one('a')
                    if not link_elem:
                        continue
                    
                    url = link_elem.get('href', '')
                    if not url.startswith('http'):
                        continue
                    
                    # Try to extract description
                    description = ""
                    desc_selectors = ['div.VwiC3b', 'span.st', 'div.s', 'div[data-content-feature="1"]']
                    for desc_selector in desc_selectors:
                        desc_elem = container.select_one(desc_selector)
                        if desc_elem:
                            description = desc_elem.get_text().strip()
                            break
                    
                    # Add to results
                    search_results.append({
                        "title": title,
                        "url": url,
                        "description": description,
                        "position": len(search_results) + 1,
                        "query": query
                    })
                    
                    # Stop once we have enough results
                    if len(search_results) >= num_results:
                        break
                
                # If we found results with this selector, stop trying others
                if search_results:
                    break
            
            # 2. If no results found with containers, try to extract all links
            if not search_results:
                links = soup.find_all('a')
                print(f"Found {len(links)} links in total")
                
                for link in links:
                    href = link.get('href', '')
                    # Skip Google's own links and other non-result URLs
                    if not href.startswith('http') or 'google' in href.lower():
                        continue
                    
                    # Get the title from the link text or nearby h3
                    title = link.get_text().strip()
                    if not title and link.find('h3'):
                        title = link.find('h3').get_text().strip()
                    
                    # Skip if no title
                    if not title:
                        continue
                    
                    # Try to find a description
                    description = ""
                    parent = link.parent
                    for _ in range(3):  # Look up to 3 levels up
                        if parent:
                            # Find any div that might contain a description
                            desc_div = parent.find('div', class_=lambda c: c and ('desc' in c.lower() or 'snippet' in c.lower()))
                            if desc_div:
                                description = desc_div.get_text().strip()
                                break
                            parent = parent.parent
                    
                    # Add to results
                    search_results.append({
                        "title": title,
                        "url": href,
                        "description": description,
                        "position": len(search_results) + 1,
                        "query": query
                    })
                    
                    # Stop once we have enough results
                    if len(search_results) >= num_results:
                        break
            
            # Save the results for debugging
            if search_results:
                try:
                    with open("direct_extraction_results.json", "w", encoding="utf-8") as f:
                        json.dump(search_results, f, indent=2, ensure_ascii=False)
                    print(f"Saved {len(search_results)} results to direct_extraction_results.json")
                except Exception as e:
                    print(f"Could not save results: {str(e)}")
            
            return search_results
            
        except Exception as e:
            print(f"Error in direct extraction: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

async def test_stealth_analyzer():
    """Test the stealth SERP analyzer with a sample query."""
    print("\n" + "="*80)
    print(" STEALTH SERP ANALYZER TEST ".center(80, "="))
    print("="*80 + "\n")
    
    # Initialize the stealth analyzer
    analyzer = StealthSerpAnalyzer(headless=True)
    
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
        output_file = "stealth_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved complete results to {output_file}")
    else:
        print("NO RESULTS FOUND.")
        print("Please check the logs for any errors.")

if __name__ == "__main__":
    asyncio.run(test_stealth_analyzer())
