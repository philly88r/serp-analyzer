import asyncio
import json
import os
import random
import time
import traceback
from urllib.parse import quote_plus, urlencode
import requests
from bs4 import BeautifulSoup
import re
import logging
from datetime import datetime
import aiohttp
from urllib.parse import urlparse, urljoin
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bypass_serp.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BypassSERP")

class BypassSerpAnalyzer:
    """
    A SERP analyzer that uses multiple methods to bypass Google's anti-bot detection.
    """
    
    def __init__(self, headless=True):
        """Initialize the bypass SERP analyzer."""
        self.headless = headless
        self._initialize_stealth_config()
        self.last_request_time = 0
        self.min_request_interval = 5  # Minimum seconds between requests
        self.session = requests.Session()  # Use a persistent session
        self.captcha_detected = False
        self.block_count = 0
        self.max_retries = 3
        
        # Create necessary directories
        os.makedirs("results", exist_ok=True)
        os.makedirs("debug", exist_ok=True)
    
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
    
    def _get_random_user_agent(self):
        """Get a random user agent from the list."""
        return random.choice(self.user_agents)
    
    def _get_random_referrer(self):
        """Get a random referrer from the list."""
        return random.choice(self.referrers)
    
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
        Uses multiple methods to bypass anti-bot detection.
        
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
                
                # Method 1: Try using DuckDuckGo as a proxy to Google
                results = await self._search_with_duckduckgo(query, num_results)
                
                if results and len(results) > 0:
                    logger.info(f"DuckDuckGo search returned {len(results)} results")
                    return results
                
                # Method 2: Try using Bing
                results = await self._search_with_bing(query, num_results)
                
                if results and len(results) > 0:
                    logger.info(f"Bing search returned {len(results)} results")
                    return results
                
                # Method 3: Try using a direct HTTP request to Google
                results = await self._search_with_direct_http(query, num_results)
                
                if results and len(results) > 0:
                    logger.info(f"Direct HTTP request returned {len(results)} results")
                    return results
            
            logger.error(f"All search methods and retries failed for query: {query}")
            return []
            
        except Exception as e:
            logger.error(f"Error searching Google: {str(e)}")
            traceback.print_exc()
            return []

    async def analyze_page(self, url, session):
        """
        Analyze a page for SEO metrics
        """
        headers = {
            "User-Agent": self._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": self._get_random_referrer()
        }
        try:
            logger.info(f"Analyzing page: {url}")
            self._respect_rate_limits() # Ensure we don't hit sites too fast either
            async with session.get(url, headers=headers, timeout=20) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}, status: {response.status}")
                    return {"url": url, "title": "", "meta_description": "", "error": f"HTTP {response.status}"}
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, "html.parser")
                
                # Basic data
                title = soup.title.string.strip() if soup.title else ""
                
                # Meta description
                description_tag = soup.find("meta", attrs={"name": "description"})
                meta_description = description_tag["content"].strip() if description_tag and description_tag.get("content") else ""
                
                # Meta keywords
                meta_keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
                meta_keywords = meta_keywords_tag['content'].strip() if meta_keywords_tag and meta_keywords_tag.get('content') else ""
                
                # Headings
                h1_tags = [h1.get_text(strip=True) for h1 in soup.find_all('h1')]
                h2_tags = [h2.get_text(strip=True) for h2 in soup.find_all('h2')]
                h3_tags = [h3.get_text(strip=True) for h3 in soup.find_all('h3')]
                h4_tags = [h4.get_text(strip=True) for h4 in soup.find_all('h4')]
                h5_tags = [h5.get_text(strip=True) for h5 in soup.find_all('h5')]
                h6_tags = [h6.get_text(strip=True) for h6 in soup.find_all('h6')]
                
                # Links analysis
                internal_links = []
                external_links = []
                page_domain = urlparse(url).netloc
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    text = link.get_text(strip=True)
                    rel = link.get('rel', [])
                    nofollow = 'nofollow' in rel if rel else False
                    
                    # Process URL
                    try:
                        if href.startswith('/'):
                            full_url = urljoin(url, href)
                            is_internal = True
                        elif not href.startswith(('http://', 'https://')):
                            full_url = urljoin(url + ('/' if not url.endswith('/') else ''), href)
                            is_internal = True
                        else:
                            full_url = href
                            link_domain = urlparse(href).netloc
                            is_internal = link_domain == page_domain
                        
                        link_data = {
                            'url': full_url,
                            'text': text,
                            'nofollow': nofollow
                        }
                        
                        if is_internal:
                            internal_links.append(link_data)
                        else:
                            external_links.append(link_data)
                    except Exception:
                        # If URL parsing fails, skip this link
                        pass
                
                # Images analysis
                images = []
                images_with_alt_count = 0
                
                for img in soup.find_all('img'):
                    src = img.get('src', '')
                    alt = img.get('alt', '')
                    
                    # Ensure full URL for relative image src
                    if src:
                        if src.startswith('/'):
                            src = urljoin(url, src)
                        elif not src.startswith(('http://', 'https://')):
                            src = urljoin(url + ('/' if not url.endswith('/') else ''), src)
                    
                    if alt:
                        images_with_alt_count += 1
                    
                    images.append({'src': src, 'alt': alt})
                
                # Schema.org structured data
                schema_data = []
                for script in soup.find_all('script', type='application/ld+json'):
                    try:
                        schema_json = json.loads(script.string)
                        if isinstance(schema_json, dict):
                            schema_type = schema_json.get('@type', 'Unknown')
                            schema_data.append({
                                'type': schema_type,
                                'properties': schema_json
                            })
                        elif isinstance(schema_json, list):
                            for item in schema_json:
                                if isinstance(item, dict):
                                    schema_type = item.get('@type', 'Unknown')
                                    schema_data.append({
                                        'type': schema_type,
                                        'properties': item
                                    })
                    except Exception:
                        # If JSON parsing fails, skip this schema
                        pass
                
                # Content analysis
                body_text = soup.body.get_text(" ", strip=True) if soup.body else ""
                word_count = len(body_text.split()) if body_text else 0
                content_sample = " ".join(body_text.split()[:150]) # First 150 words
                
                # Keyword analysis (basic)
                keyword = ""  # This would typically come from the search query
                keyword_count = body_text.lower().count(keyword.lower()) if keyword and body_text else 0
                keyword_density = (keyword_count / word_count * 100) if word_count > 0 and keyword_count > 0 else 0
                
                logger.info(f"Successfully analyzed: {url}, Title: {title[:50]}...")
                
                # Return data in a format compatible with the original SEO analyzer
                return {
                    "url": url,
                    "title": title,
                    "meta_description": meta_description,
                    "meta_keywords": meta_keywords,
                    "h1_tags": h1_tags,
                    "h2_tags": h2_tags,
                    "h3_tags": h3_tags,
                    "h4_tags": h4_tags,
                    "h5_tags": h5_tags,
                    "h6_tags": h6_tags,
                    "h1_count": len(h1_tags),
                    "h2_count": len(h2_tags),
                    "h3_count": len(h3_tags),
                    "h4_count": len(h4_tags),
                    "h5_count": len(h5_tags),
                    "h6_count": len(h6_tags),
                    "word_count": word_count,
                    "internal_links_count": len(internal_links),
                    "external_links_count": len(external_links),
                    "internal_links": internal_links,
                    "external_links": external_links,
                    "images_count": len(images),
                    "images_with_alt_count": images_with_alt_count,
                    "schema_count": len(schema_data),
                    "schema_data": schema_data,
                    "keyword": keyword,
                    "keyword_count": keyword_count,
                    "keyword_density": keyword_density,
                    "content_sample": content_sample,
                    "error": None
                }
        except asyncio.TimeoutError:
            logger.warning(f"Timeout analyzing page: {url}")
            return {"url": url, "title": "", "meta_description": "", "error": "Timeout"}
        except Exception as e:
            logger.error(f"Error analyzing page {url}: {str(e)}", exc_info=True)
            return {"url": url, "title": "", "meta_description": "", "error": str(e)}

    async def analyze_serp_for_api(self, query, num_results=10):
        """
        Analyze SERP results for API
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            dict: SERP analysis results
        """
        try:
            logger.info(f"Analyzing SERP for query: {query}, num_results: {num_results}")
            
            # Get raw search results
            raw_search_results = await self.search_google(query, num_results)
            
            # Process results
            results = []
            async with aiohttp.ClientSession() as session:
                for result in raw_search_results:
                    url = result.get("url")
                    if not url:
                        continue
                    
                    # Add basic info from search results
                    processed_result = {
                        "url": url,
                        "title": result.get("title", ""),
                        "description": result.get("description", ""),
                        "position": result.get("position", 0),
                    }
                    
                    # Analyze the page
                    try:
                        page_analysis = await self.analyze_page(url, session)
                        # Update with page analysis data
                        processed_result.update(page_analysis)
                        # Set keyword to the search query for keyword analysis
                        processed_result["keyword"] = query
                        # Recalculate keyword metrics with the actual query
                        if "content_sample" in processed_result and processed_result["content_sample"]:
                            body_text = processed_result["content_sample"]
                            word_count = processed_result.get("word_count", 0)
                            keyword_count = body_text.lower().count(query.lower()) if query and body_text else 0
                            keyword_density = (keyword_count / word_count * 100) if word_count > 0 and keyword_count > 0 else 0
                            processed_result["keyword_count"] = keyword_count
                            processed_result["keyword_density"] = keyword_density
                    except Exception as e:
                        logger.error(f"Error analyzing page {url}: {str(e)}", exc_info=True)
                        processed_result["error"] = str(e)
                    
                    results.append(processed_result)
            
            # Format the response similar to the original SEO analyzer
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            response = {
                "query": query,
                "timestamp": timestamp,
                "results": results,
                "num_results": len(results)
            }
            
            logger.info(f"SERP analysis completed for query: {query}, found {len(results)} results")
            return response
            
        except Exception as e:
            logger.error(f"Error in analyze_serp_for_api: {str(e)}", exc_info=True)
            return {
                "query": query,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "results": [],
                "num_results": 0,
                "error": str(e)
            }

    async def _search_with_duckduckgo(self, query, num_results=6):
        """
        Search using DuckDuckGo as a proxy to get Google-like results.
        """
        try:
            # Respect rate limits
            self._respect_rate_limits()
            
            # Construct the search URL
            params = {
                "q": f"{query} site:.com",  # Add site:.com to get more web results
                "kl": "us-en",  # US English results
                "kp": "-2",     # No safe search
                "kaf": "1"      # Show full content
            }
            
            search_url = f"https://html.duckduckgo.com/html/?{urlencode(params)}"
            
            logger.info(f"Making DuckDuckGo request to: {search_url}")
            
            # Set up headers
            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": self._get_random_referrer(),
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            # Make the request
            response = self.session.get(search_url, headers=headers, timeout=15)
            
            logger.info(f"DuckDuckGo request status code: {response.status_code}")
            
            # Check if the request was successful
            if response.status_code != 200:
                logger.error(f"DuckDuckGo request failed with status code {response.status_code}")
                return []
            
            # Get the HTML content
            html_content = response.text
            
            # Save the HTML for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"debug/duckduckgo_{timestamp}.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Saved HTML to {debug_file} for debugging")
            
            # Parse the HTML
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Extract search results
            results = []
            result_elements = soup.select(".result")
            
            for i, result in enumerate(result_elements):
                if i >= num_results:
                    break
                
                # Extract title and URL
                title_element = result.select_one(".result__title")
                if not title_element:
                    continue
                
                title = title_element.get_text().strip()
                
                # Extract URL
                url_element = result.select_one(".result__url")
                if not url_element:
                    link_element = title_element.select_one("a")
                    if not link_element:
                        continue
                    url = link_element.get("href", "")
                else:
                    url = "https://" + url_element.get_text().strip()
                
                # Extract description
                description_element = result.select_one(".result__snippet")
                description = description_element.get_text().strip() if description_element else ""
                
                # Add to results
                results.append({
                    "title": title,
                    "url": url,
                    "description": description,
                    "position": i + 1,
                    "query": query
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in DuckDuckGo search: {str(e)}")
            traceback.print_exc()
            return []
    
    async def _search_with_bing(self, query, num_results=6):
        """
        Search using Bing to get Google-like results.
        """
        try:
            # Respect rate limits
            self._respect_rate_limits()
            
            # Construct the search URL with randomized parameters
            params = {
                "q": query,
                "count": num_results * 2,  # Request more results than needed
                "setlang": "en-US"
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
            search_url = f"https://www.bing.com/search?{query_string}"
            
            logger.info(f"Making Bing request to: {search_url}")
            
            # Set up headers
            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": self._get_random_referrer(),
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            # Make the request
            response = self.session.get(search_url, headers=headers, timeout=15)
            
            logger.info(f"Bing request status code: {response.status_code}")
            
            # Check if the request was successful
            if response.status_code != 200:
                logger.error(f"Bing request failed with status code {response.status_code}")
                return []
            
            # Get the HTML content
            html_content = response.text
            
            # Save the HTML for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"debug/bing_{timestamp}.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Saved HTML to {debug_file} for debugging")
            
            # Parse the HTML
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Extract search results
            results = []
            result_elements = soup.select(".b_algo")
            
            for i, result in enumerate(result_elements):
                if i >= num_results:
                    break
                
                # Extract title and URL
                title_element = result.select_one("h2")
                if not title_element:
                    continue
                
                title = title_element.get_text().strip()
                
                # Extract URL
                link_element = title_element.select_one("a")
                if not link_element:
                    continue
                
                url = link_element.get("href", "")
                if not url.startswith("http"):
                    continue
                
                # Extract description
                description_element = result.select_one(".b_caption p")
                description = description_element.get_text().strip() if description_element else ""
                
                # Add to results
                results.append({
                    "title": title,
                    "url": url,
                    "description": description,
                    "position": i + 1,
                    "query": query
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in Bing search: {str(e)}")
            traceback.print_exc()
            return []
    
    async def _search_with_direct_http(self, query, num_results=6):
        """
        Search Google using a direct HTTP request with enhanced stealth techniques.
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
            
            logger.info(f"Making direct HTTP request to: {search_url}")
            
            # Set up headers with enhanced stealth
            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
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
            
            # Add cookies to simulate a real browser
            cookies = {
                "CONSENT": f"YES+cb.{int(time.time())}-04-p0.en+FX+{random.randint(100, 999)}",
                "NID": ''.join(random.choice('0123456789abcdef') for _ in range(32)),
                "1P_JAR": datetime.now().strftime("%Y-%m-%d-%H")
            }
            
            # Make the request with a longer timeout
            response = self.session.get(
                search_url, 
                headers=headers, 
                cookies=cookies,
                timeout=20
            )
            
            logger.info(f"Direct HTTP request status code: {response.status_code}")
            
            # Check if the request was successful
            if response.status_code != 200:
                logger.error(f"Direct HTTP request failed with status code {response.status_code}")
                return []
            
            # Get the HTML content
            html_content = response.text
            
            # Check for CAPTCHA or block page
            if "captcha" in html_content.lower() or "unusual traffic" in html_content.lower():
                logger.warning("CAPTCHA or block detected in direct HTTP response")
                self.captcha_detected = True
                return []
            
            # Save the HTML for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"debug/google_{timestamp}.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Saved HTML to {debug_file} for debugging")
            
            # Parse the HTML
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Extract search results
            results = []
            
            # Method 1: Look for standard Google result containers
            selectors = [
                'div.g', 'div.tF2Cxc', 'div.yuRUbf', 'div.rc', 
                'div[data-header-feature]', 'div.MjjYud', 'div.Gx5Zad'
            ]
            
            for selector in selectors:
                containers = soup.select(selector)
                logger.info(f"Selector '{selector}' found {len(containers)} elements")
                
                for container in containers:
                    # Extract title
                    title_element = container.select_one('h3')
                    if not title_element:
                        continue
                    
                    title = title_element.get_text().strip()
                    
                    # Extract URL
                    link_element = container.select_one('a')
                    if not link_element:
                        continue
                    
                    url = link_element.get('href', '')
                    if not url.startswith('http'):
                        continue
                    
                    # Extract description
                    description = ""
                    desc_selectors = ['div.VwiC3b', 'span.st', 'div.s']
                    for desc_selector in desc_selectors:
                        desc_element = container.select_one(desc_selector)
                        if desc_element:
                            description = desc_element.get_text().strip()
                            break
                    
                    # Add to results
                    results.append({
                        "title": title,
                        "url": url,
                        "description": description,
                        "position": len(results) + 1,
                        "query": query
                    })
                    
                    # Stop once we have enough results
                    if len(results) >= num_results:
                        break
                
                # If we found results with this selector, stop trying others
                if len(results) >= num_results:
                    break
            
            # If we didn't find enough results with the selectors, try extracting all links
            if len(results) < num_results:
                # Get all links
                links = soup.find_all('a')
                logger.info(f"Found {len(links)} links in HTML")
                
                # Filter links that look like search results
                for link in links:
                    # Skip if we already have enough results
                    if len(results) >= num_results:
                        break
                    
                    href = link.get('href', '')
                    # Skip Google's own links and other non-result URLs
                    if not href.startswith('http') or 'google' in href.lower():
                        continue
                    
                    # Get the title
                    title = link.get_text().strip()
                    if not title:
                        continue
                    
                    # Check if this URL is already in the results
                    if any(r['url'] == href for r in results):
                        continue
                    
                    # Add to results
                    results.append({
                        "title": title,
                        "url": href,
                        "description": "",
                        "position": len(results) + 1,
                        "query": query
                    })
            
            logger.info(f"Extracted {len(results)} results from direct HTTP request")
            return results
            
        except Exception as e:
            logger.error(f"Error in direct HTTP request: {str(e)}")
            traceback.print_exc()
            return []
    
    async def analyze_serp(self, query, num_results=6):
        """
        Analyze SERP for a given query.
        
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
    
    def _save_results(self, serp_analysis):
        """Save search results to JSON and CSV files."""
        try:
            # Generate timestamp and safe query string
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            query = serp_analysis["query"]
            safe_query = query.replace(' ', '_')
            
            # Save JSON results
            json_file = f"results/serp_{safe_query}_{timestamp}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(serp_analysis, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved JSON results to {json_file}")
            
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
async def test_bypass_analyzer():
    """Test the bypass SERP analyzer with a sample query."""
    print("\n" + "="*80)
    print(" BYPASS SERP ANALYZER TEST ".center(80, "="))
    print("="*80 + "\n")
    
    # Initialize the analyzer
    analyzer = BypassSerpAnalyzer(headless=True)
    
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
    asyncio.run(test_bypass_analyzer())
