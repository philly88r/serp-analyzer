import asyncio
import json
import os
import random
import time
import traceback
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup
import re
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("serp_analyzer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SerpAnalyzer")

class ImprovedSerpAnalyzer:
    """
    An improved SERP analyzer that uses advanced techniques to avoid Google's anti-bot detection.
    """
    
    def __init__(self, headless=True):
        """Initialize the improved SERP analyzer."""
        self.headless = headless
        self._initialize_stealth_config()
        self.last_request_time = 0
        self.min_request_interval = 5  # Minimum seconds between requests
        self.session = requests.Session()  # Use a persistent session
        self.captcha_detected = False
        self.block_count = 0
        self.max_retries = 3
    
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
        
        # Common referrers
        self.referrers = [
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://duckduckgo.com/",
            "https://www.yahoo.com/",
            "https://www.reddit.com/",
            "https://www.facebook.com/",
            "https://twitter.com/",
            "https://www.linkedin.com/"
        ]
        
        # Common languages
        self.languages = [
            "en-US,en;q=0.9",
            "en-GB,en;q=0.9",
            "en-CA,en;q=0.9",
            "en-AU,en;q=0.9"
        ]
    
    def _get_random_user_agent(self):
        """Get a random user agent from the list."""
        return random.choice(self.user_agents)
    
    def _get_random_referrer(self):
        """Get a random referrer from the list."""
        return random.choice(self.referrers)
    
    def _get_random_language(self):
        """Get a random language from the list."""
        return random.choice(self.languages)
    
    def _get_stealth_headers(self):
        """Get stealth headers for HTTP requests."""
        return {
            "User-Agent": self._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": self._get_random_language(),
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": self._get_random_referrer(),
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
    
    def _respect_rate_limits(self):
        """Respect rate limits by adding delays between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            # Add a random delay to avoid detection patterns
            delay = self.min_request_interval - time_since_last_request + random.uniform(1.0, 3.0)
            logger.info(f"Rate limiting: Waiting {delay:.2f} seconds before next request")
            time.sleep(delay)
        
        self.last_request_time = time.time()
    
    async def search_google(self, query, num_results=6):
        """
        Search Google for a query and return the results.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to return
            
        Returns:
            list: A list of search result dictionaries
        """
        try:
            logger.info(f"Searching Google for: {query}")
            
            # Reset captcha detection
            self.captcha_detected = False
            
            # Try multiple methods with retries
            for attempt in range(self.max_retries):
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt+1}/{self.max_retries} for query: {query}")
                    # Add increasing delay between retries
                    delay = 5 + (attempt * 5) + random.uniform(1.0, 5.0)
                    logger.info(f"Waiting {delay:.2f} seconds before retry")
                    await asyncio.sleep(delay)
                
                # Try stealth HTTP request first
                results = await self._search_with_stealth_http(query, num_results)
                
                if results and len(results) > 0:
                    logger.info(f"Stealth HTTP request returned {len(results)} results")
                    return results
                
                if self.captcha_detected:
                    logger.warning(f"CAPTCHA detected on attempt {attempt+1}. Adding longer delay before retry.")
                    self.block_count += 1
                    # Add longer delay if CAPTCHA was detected
                    await asyncio.sleep(10 + (attempt * 10))
                
                # Try with AsyncWebCrawler if HTTP request failed
                logger.info(f"Stealth HTTP request failed. Trying with AsyncWebCrawler...")
                results = await self._search_with_crawler(query, num_results)
                
                if results and len(results) > 0:
                    logger.info(f"AsyncWebCrawler returned {len(results)} results")
                    return results
            
            logger.error(f"All search methods and retries failed for query: {query}")
            return []
            
        except Exception as e:
            logger.error(f"Error searching Google: {str(e)}")
            traceback.print_exc()
            return []
    
    async def _search_with_stealth_http(self, query, num_results=6):
        """
        Search Google using a stealth HTTP request.
        """
        try:
            # Respect rate limits
            self._respect_rate_limits()
            
            # Construct the search URL with randomized parameters
            params = {
                "q": query,
                "num": num_results * 2,  # Request more results than needed
                "hl": "en",
                "gl": "us",
                "pws": "0"  # Disable personalized results
            }
            
            # Add random parameters to avoid detection patterns
            if random.random() < 0.5:
                params["safe"] = "off"
            
            if random.random() < 0.7:
                params["source"] = "hp"
            
            # Randomize the order of parameters
            param_items = list(params.items())
            random.shuffle(param_items)
            shuffled_params = dict(param_items)
            
            # Build the query string
            query_string = "&".join([f"{k}={v}" for k, v in shuffled_params.items()])
            search_url = f"https://www.google.com/search?{query_string}"
            
            logger.info(f"Making stealth HTTP request to: {search_url}")
            
            # Get stealth headers
            headers = self._get_stealth_headers()
            
            # Make the request with our session
            response = self.session.get(search_url, headers=headers, timeout=15)
            
            logger.info(f"Stealth HTTP request status code: {response.status_code}")
            
            # Check if the request was successful
            if response.status_code != 200:
                logger.error(f"Stealth HTTP request failed with status code {response.status_code}")
                return []
            
            # Get the HTML content
            html_content = response.text
            
            # Check for CAPTCHA or block page
            if self._is_captcha_or_block(html_content):
                self.captcha_detected = True
                logger.warning("CAPTCHA or block detected in stealth HTTP response")
                return []
            
            # Save the HTML for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"stealth_http_{timestamp}.html"
            try:
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"Saved HTML to {debug_file} for debugging")
            except Exception as e:
                logger.error(f"Could not save HTML for debugging: {str(e)}")
            
            # Extract search results
            return await self._extract_results_from_html(html_content, query, num_results)
            
        except Exception as e:
            logger.error(f"Error in stealth HTTP request: {str(e)}")
            traceback.print_exc()
            return []
    
    async def _search_with_crawler(self, query, num_results=6):
        """
        Search Google using AsyncWebCrawler with stealth techniques.
        """
        try:
            from crawl4ai import AsyncWebCrawler
            
            # Respect rate limits
            self._respect_rate_limits()
            
            # Construct the search URL with randomized parameters
            params = {
                "q": query,
                "num": num_results * 2,
                "hl": "en",
                "gl": "us",
                "pws": "0"
            }
            
            # Add random parameters to avoid detection patterns
            if random.random() < 0.5:
                params["safe"] = "off"
            
            if random.random() < 0.7:
                params["source"] = "hp"
            
            # Randomize the order of parameters
            param_items = list(params.items())
            random.shuffle(param_items)
            shuffled_params = dict(param_items)
            
            # Build the query string
            query_string = "&".join([f"{k}={v}" for k, v in shuffled_params.items()])
            search_url = f"https://www.google.com/search?{query_string}"
            
            logger.info(f"Initializing AsyncWebCrawler for URL: {search_url}")
            
            # Get random parameters for this search
            user_agent = self._get_random_user_agent()
            
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
                            delay_before_return_html=random.uniform(1.0, 3.0),
                            word_count_threshold=100,
                            scan_full_page=True,
                            scroll_delay=random.uniform(0.3, 1.0),
                            remove_overlay_elements=True,
                            browser_args=browser_args
                        ),
                        timeout=30.0  # 30 second timeout for the entire operation
                    )
                    logger.info("AsyncWebCrawler completed successfully")
                except asyncio.TimeoutError:
                    logger.error("AsyncWebCrawler operation timed out")
                    return []
                except Exception as e:
                    logger.error(f"Error using AsyncWebCrawler: {str(e)}")
                    traceback.print_exc()
                    return []
            
            # Check if the result was successful
            if not result or not result.success:
                logger.error(f"Error searching with AsyncWebCrawler: {result.error_message if result else 'No result'}")
                return []
            
            # Get the HTML content
            html_content = result.html
            if not html_content or len(html_content) < 1000:
                logger.error(f"AsyncWebCrawler did not return valid HTML content (length: {len(html_content) if html_content else 0})")
                return []
            
            # Save the HTML for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"crawler_{timestamp}.html"
            try:
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"Saved HTML to {debug_file} for debugging")
            except Exception as e:
                logger.error(f"Could not save HTML for debugging: {str(e)}")
            
            # Check for CAPTCHA or block page
            if self._is_captcha_or_block(html_content):
                self.captcha_detected = True
                logger.warning("CAPTCHA or block detected in AsyncWebCrawler response")
                return []
            
            # Extract search results
            return await self._extract_results_from_html(html_content, query, num_results)
            
        except Exception as e:
            logger.error(f"Error in AsyncWebCrawler search: {str(e)}")
            traceback.print_exc()
            return []
    
    def _is_captcha_or_block(self, html_content):
        """Check if the HTML content contains CAPTCHA or block indicators."""
        if not html_content:
            return False
            
        # Common indicators of CAPTCHA or block pages
        indicators = [
            "captcha",
            "unusual traffic",
            "automated queries",
            "suspicious activity",
            "security check",
            "confirm you're not a robot",
            "detected unusual activity",
            "solve this puzzle",
            "verify you are a human"
        ]
        
        # Check for indicators in the HTML content
        html_lower = html_content.lower()
        for indicator in indicators:
            if indicator in html_lower:
                logger.warning(f"Detected block indicator: '{indicator}'")
                return True
        
        # Check for reCAPTCHA scripts
        if "www.google.com/recaptcha/api.js" in html_content:
            logger.warning("Detected reCAPTCHA script")
            return True
        
        # Check for typical CAPTCHA image patterns
        if re.search(r'(captcha|recaptcha)\.(jpg|png|gif)', html_content, re.IGNORECASE):
            logger.warning("Detected CAPTCHA image")
            return True
        
        return False
    
    async def _extract_results_from_html(self, html_content, query, num_results=6):
        """
        Extract search results from HTML content using multiple methods.
        """
        try:
            # Parse the HTML
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Try multiple extraction methods
            
            # Method 1: Look for standard Google result containers
            logger.info("Trying extraction method 1: Standard Google result containers")
            results = self._extract_with_containers(soup, query, num_results)
            if results and len(results) > 0:
                logger.info(f"Method 1 found {len(results)} results")
                return results
            
            # Method 2: Look for all links
            logger.info("Trying extraction method 2: All links")
            results = self._extract_with_links(soup, query, num_results)
            if results and len(results) > 0:
                logger.info(f"Method 2 found {len(results)} results")
                return results
            
            # Method 3: Use regex patterns
            logger.info("Trying extraction method 3: Regex patterns")
            results = self._extract_with_regex(html_content, query, num_results)
            if results and len(results) > 0:
                logger.info(f"Method 3 found {len(results)} results")
                return results
            
            logger.warning("All extraction methods failed to find results")
            return []
            
        except Exception as e:
            logger.error(f"Error extracting results from HTML: {str(e)}")
            traceback.print_exc()
            return []
    
    def _extract_with_containers(self, soup, query, num_results=6):
        """Extract search results using standard Google result containers."""
        try:
            # Common selectors for Google result containers
            selectors = [
                'div.g', 'div.tF2Cxc', 'div.yuRUbf', 'div.rc', 
                'div[data-header-feature]', 'div.MjjYud', 'div.Gx5Zad',
                'div.v7W49e', 'div.jtfYYd', 'div.Z26q7c'
            ]
            
            result_links = []
            
            for selector in selectors:
                containers = soup.select(selector)
                logger.info(f"Selector '{selector}' found {len(containers)} elements")
                
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
                    result_links.append({
                        "title": title,
                        "url": url,
                        "description": description,
                        "position": len(result_links) + 1,
                        "query": query
                    })
                    
                    # Stop once we have enough results
                    if len(result_links) >= num_results:
                        break
                
                # If we found results with this selector, stop trying others
                if result_links:
                    break
            
            return result_links
            
        except Exception as e:
            logger.error(f"Error in container extraction: {str(e)}")
            return []
    
    def _extract_with_links(self, soup, query, num_results=6):
        """Extract search results by analyzing all links in the page."""
        try:
            # Get all links
            links = soup.find_all("a")
            logger.info(f"Found {len(links)} links in HTML")
            
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
            
            return result_links
            
        except Exception as e:
            logger.error(f"Error in link extraction: {str(e)}")
            return []
    
    def _extract_with_regex(self, html_content, query, num_results=6):
        """Extract search results using regex patterns."""
        try:
            logger.info("Attempting to extract results with regex patterns")
            
            # Pattern to match URLs in Google search results
            url_pattern = r'<a href="(https?://[^"]+)"[^>]*>([^<]+)</a>'
            matches = re.findall(url_pattern, html_content)
            
            # Filter unique URLs
            unique_urls = set()
            search_results = []
            
            for url, title in matches:
                # Filter out Google's own URLs and other non-result URLs
                if 'google.com' in url or 'accounts.google' in url or 'support.google' in url:
                    continue
                    
                # Skip if URL already processed
                if url in unique_urls:
                    continue
                    
                unique_urls.add(url)
                
                # Clean up title
                title = title.strip()
                if not title:
                    continue
                
                # Try to find description using regex
                description = ""
                desc_pattern = f'<div[^>]*>([^<]{50,500})</div>'
                desc_matches = re.findall(desc_pattern, html_content)
                if desc_matches:
                    description = desc_matches[0].strip()
                
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
            
            logger.info(f"Found {len(unique_urls)} unique URLs with regex")
            logger.info(f"Extracted {len(search_results)} results with regex method")
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error extracting results with regex: {str(e)}")
            return []
    
    async def analyze_serp(self, query, num_results=6):
        """
        Analyze SERP for a given query.
        This is a wrapper around search_google for compatibility with existing code.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to return
            
        Returns:
            dict: A dictionary containing the search results and metadata
        """
        try:
            logger.info(f"Analyzing SERP for query: {query}")
            
            # Get search results
            results = await self.search_google(query, num_results)
            
            # Print debugging information
            logger.info(f"Search results type: {type(results)}")
            logger.info(f"Search results count: {len(results) if results else 0}")
            
            if not results or len(results) == 0:
                logger.warning(f"No search results found for query: {query}")
                return {"query": query, "results": []}
            
            # Format the results in the expected structure
            serp_analysis = {
                "query": query,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "results": results
            }
            
            # Save the results to files
            self._save_results(serp_analysis)
            
            # Return the results
            return serp_analysis
            
        except Exception as e:
            logger.error(f"Error in analyze_serp: {str(e)}")
            traceback.print_exc()
            return {"query": query, "results": []}
    
    def _save_results(self, serp_analysis, output_format="json"):
        """Save search results to files."""
        try:
            # Create results directory if it doesn't exist
            os.makedirs("results", exist_ok=True)
            
            # Generate timestamp and safe query string
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            query = serp_analysis["query"]
            safe_query = query.replace(' ', '_')
            
            if output_format == "json" or output_format == "all":
                # Save JSON results
                json_file = f"results/serp_{safe_query}_{timestamp}.json"
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(serp_analysis, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved JSON results to {json_file}")
            
            if output_format == "csv" or output_format == "all":
                # Save CSV results
                csv_file = f"results/serp_{safe_query}_{timestamp}.csv"
                with open(csv_file, "w", encoding="utf-8") as f:
                    # Write header
                    f.write("position,title,url,description,query\n")
                    
                    # Write data
                    for result in serp_analysis["results"]:
                        position = result.get("position", "")
                        title = result.get("title", "").replace('"', '""')
                        url = result.get("url", "")
                        description = result.get("description", "").replace('"', '""')
                        result_query = result.get("query", "").replace('"', '""')
                        
                        f.write(f'"{position}","{title}","{url}","{description}","{result_query}"\n')
                
                logger.info(f"Saved CSV results to {csv_file}")
            
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")

# For testing
async def test_improved_analyzer():
    """Test the improved SERP analyzer with a sample query."""
    print("\n" + "="*80)
    print(" IMPROVED SERP ANALYZER TEST ".center(80, "="))
    print("="*80 + "\n")
    
    # Initialize the analyzer
    analyzer = ImprovedSerpAnalyzer(headless=True)
    
    # Test query
    query = "python tutorial"
    
    print(f"Testing query: '{query}'")
    
    # Search for the query
    results = await analyzer.analyze_serp(query)
    
    # Print results summary
    print("\n" + "="*80)
    print(f" FOUND {len(results['results'])} RESULTS ".center(80, "="))
    print("="*80 + "\n")
    
    if results['results']:
        # Print each result with clear separation
        for i, result in enumerate(results['results']):
            print(f"RESULT #{i+1}:")
            print(f"TITLE: {result.get('title', 'No title')}")
            print(f"URL: {result.get('url', 'No URL')}")
            print(f"DESCRIPTION: {result.get('description', 'No description')[:150]}")
            print("-"*80)
    else:
        print("NO RESULTS FOUND.")
        print("Please check the logs for any errors.")

if __name__ == "__main__":
    asyncio.run(test_improved_analyzer())
