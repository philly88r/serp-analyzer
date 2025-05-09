import asyncio
import json
import os
import random
import time
import sys
import io
import cv2
import numpy as np
from PIL import Image
import pytesseract
from playwright.async_api import async_playwright
import traceback
from urllib.parse import quote_plus, urlencode, urlparse
import requests
from bs4 import BeautifulSoup
import re
import logging
from datetime import datetime
import aiohttp
from urllib.parse import urlparse, urljoin

# Import our new modules
try:
    from database import init_db, get_session, close_session, save_search_query, save_search_results, save_page_analysis
    from proxy_manager import proxy_manager
    from ai_recommendations import generate_seo_recommendations, prioritize_recommendations
    from competitor_analysis import CompetitorAnalyzer
    from bulk_analyzer import BulkAnalyzer
except ImportError:
    # If modules aren't available yet, log warning but continue
    logging.warning("New modules not found. Some features will be disabled.")

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
        self.current_query_id = None  # Track current query ID for database integration
        
        # Create necessary directories
        os.makedirs("results", exist_ok=True)
        os.makedirs("debug", exist_ok=True)
        
        # Initialize new components if available
        try:
            # Initialize database
            init_db()
            
            # Initialize competitor analyzer
            self.competitor_analyzer = CompetitorAnalyzer(self)
            
            # Initialize bulk analyzer
            self.bulk_analyzer = BulkAnalyzer(self)
            
            logger.info("Enhanced features initialized successfully")
        except NameError:
            logger.warning("Enhanced features not available")
        except Exception as e:
            logger.error(f"Error initializing enhanced features: {str(e)}")
            traceback.print_exc()
    
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
                
                # Method 1: Try using Playwright for Google search
                try:
                    results = await self._search_with_playwright(query, num_results)
                    
                    if results and len(results) > 0:
                        logger.info(f"Playwright Google search returned {len(results)} results")
                        return results
                except Exception as e:
                    logger.error(f"Playwright search failed: {str(e)}")
                    logger.info("Falling back to other search methods")
                
                # Method 2: Try using a direct HTTP request to Google
                results = await self._search_with_direct_http(query, num_results)
                
                if results and len(results) > 0:
                    logger.info(f"Direct HTTP request returned {len(results)} results")
                    return results

                # Method 3: Try using Bing
                results = await self._search_with_bing(query, num_results)
                
                if results and len(results) > 0:
                    logger.info(f"Bing search returned {len(results)} results")
                    return results
                
                # Method 4: Try using DuckDuckGo as a proxy to Google
                results = await self._search_with_duckduckgo(query, num_results)
                
                if results and len(results) > 0:
                    logger.info(f"DuckDuckGo search returned {len(results)} results")
                    return results
            
            logger.error(f"All search methods and retries failed for query: {query}")
            return []
            
        except Exception as e:
            logger.error(f"Error searching Google: {str(e)}")
            traceback.print_exc()
            return []

    def _extract_schema_markup(self, soup):
        """Extract schema markup from HTML."""
        schema_types = []
        has_schema = False
        
        # Look for JSON-LD schema
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if '@type' in data:
                    schema_types.append(data['@type'])
                    has_schema = True
                elif '@graph' in data:
                    for item in data['@graph']:
                        if '@type' in item:
                            schema_types.append(item['@type'])
                            has_schema = True
            except:
                pass
        
        # Look for microdata schema
        microdata_elements = soup.find_all(attrs={"itemtype": True})
        for element in microdata_elements:
            itemtype = element.get('itemtype', '')
            if itemtype:
                schema_types.append(itemtype.split('/')[-1])
                has_schema = True
        
        # Look for RDFa schema
        rdfa_elements = soup.find_all(attrs={"typeof": True})
        for element in rdfa_elements:
            typeof = element.get('typeof', '')
            if typeof:
                schema_types.append(typeof)
                has_schema = True
        
        return {
            "has_schema": has_schema,
            "schema_types": schema_types
        }
    
    async def analyze_page(self, url, session, save_to_db=True):
        """
        Analyze a single page for SEO data.
        Uses aiohttp for asynchronous requests with retry mechanism.
        
        Args:
            url (str): The URL to analyze
            session: aiohttp.ClientSession or None (will create one if None)
            save_to_db (bool): Whether to save results to database
            
        Returns:
            dict: A dictionary containing the page analysis data
        """
        headers = {
            "User-Agent": self._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": self._get_random_referrer(),
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # Retry parameters
        max_retries = 3
        base_timeout = 70  # Base timeout in seconds
        
        # Create a session if one wasn't provided
        session_created = False
        _session = session
        
        if session is None:
            _session = aiohttp.ClientSession()
            session_created = True
        
        # Use a finally block to ensure session is closed if we created it
        try:
            for attempt in range(max_retries):
                try:
                    # Calculate timeout with exponential backoff
                    current_timeout = base_timeout * (1.5 ** attempt)
                
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt+1}/{max_retries} for {url} with timeout {current_timeout:.1f}s")
                    else:
                        logger.info(f"Analyzing page: {url} with timeout {current_timeout:.1f}s")
                    
                    self._respect_rate_limits() # Ensure we don't hit sites too fast either
                
                    # Get a proxy from the proxy manager if available
                    proxy_url = None
                    try:
                        proxy_url = proxy_manager.get_proxy() # Get string URL directly
                        # Removed: proxy_manager.report_success(proxy_url, response_time_ms)
                        if proxy_url:
                            logger.info(f"Using proxy for page analysis: {proxy_url}")
                        else:
                            logger.info("No proxy returned by proxy_manager for page analysis.")
                    except NameError:
                        # proxy_manager not available
                        logger.warning("proxy_manager not available for page analysis")
                        pass
                    except Exception as e:
                        logger.error(f"Error getting proxy for page analysis: {str(e)}")
                    
                    # Start timing for proxy response time calculation
                    start_time = time.time()
                
                    async with _session.get(url, headers=headers, timeout=current_timeout, proxy=proxy_url) as response:
                        # Stop timing
                        end_time = time.time()
                        response_time_ms = (end_time - start_time) * 1000
                        
                        # Check if the request was successful
                        if response.status != 200:
                            logger.warning(f"HTTP error {response.status} for {url}")
                            # Removed: if proxy_url: proxy_manager.report_failure(proxy_url, is_block=(response.status == 403 or response.status == 429))
                            if attempt == max_retries - 1:
                                return {"url": url, "title": "", "description": "", "error": f"HTTP error {response.status}", "seo_details": {}}
                            await asyncio.sleep(2 * (attempt + 1)) # Exponential backoff for retries
                            continue # Try next attempt

                        # Removed: if proxy_url: proxy_manager.report_success(proxy_url, response_time_ms)

                        # Get the HTML content
                        html_content = await response.text()
                        soup = BeautifulSoup(html_content, "html.parser")
                    
                        title = soup.title.string.strip() if soup.title else ""
                        description_tag = soup.find("meta", attrs={"name": "description"})
                        description = description_tag["content"].strip() if description_tag and description_tag.get("content") else ""
                        
                        meta_keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
                        keywords = meta_keywords_tag['content'].strip() if meta_keywords_tag and meta_keywords_tag.get('content') else ""

                        h1_tags = [h1.get_text(strip=True) for h1 in soup.find_all('h1')]
                        h2_tags = [h2.get_text(strip=True) for h2 in soup.find_all('h2')]
                        h3_tags = [h3.get_text(strip=True) for h3 in soup.find_all('h3')]

                        links_data = []
                        page_domain = urlparse(url).netloc
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            text = link.get_text(strip=True)
                            is_internal = False
                            try:
                                link_domain = urlparse(href).netloc
                                if not link_domain or link_domain == page_domain:
                                    is_internal = True
                                # Ensure full URL for relative links
                                if href.startswith('/'):
                                   href = urljoin(url, href)
                                elif not href.startswith(('http://', 'https://')):
                                   href = urljoin(url + ('/' if not url.endswith('/') else ''), href)
                            except Exception:
                                # If URL parsing fails, assume external or problematic
                                pass 
                                
                            links_data.append({
                                'text': text,
                                'url': href,
                                'is_internal': is_internal
                            })
                        
                        internal_links_count = sum(1 for link in links_data if link['is_internal'])
                        external_links_count = len(links_data) - internal_links_count

                        images_data = []
                        for img in soup.find_all('img'):
                            src = img.get('src', '')
                            alt = img.get('alt', '')
                            # Ensure full URL for relative image src
                            if src:
                                if src.startswith('/'):
                                    src = urljoin(url, src)
                                elif not src.startswith(('http://', 'https://')):
                                    src = urljoin(url + ('/' if not url.endswith('/') else ''), src)
                            images_data.append({'src': src, 'alt': alt})
                        
                        images_with_alt_count = sum(1 for img in images_data if img['alt'])

                        body_text = soup.body.get_text(" ", strip=True) if soup.body else ""
                        word_count = len(body_text.split()) if body_text else 0
                        content_sample = " ".join(body_text.split()[:150]) # First 150 words
                        
                        # Extract schema markup
                        schema_markup = self._extract_schema_markup(soup)
                        
                        # Calculate page size and technical metrics
                        page_size_kb = len(html_content) / 1024

                        # Create technical data section
                        technical_data = {
                            "page_size_kb": page_size_kb,
                            "load_time_ms": response_time_ms,
                            "status_code": response.status,
                            "content_type": response.headers.get('Content-Type', '')
                        }
                        
                        # Assemble the complete analysis data
                        analysis_data = {
                            "url": url,
                            "title": title,
                            "description": description,
                            "keywords": keywords,
                            "headings": {
                                "h1": h1_tags,
                                "h2": h2_tags,
                                "h3": h3_tags
                            },
                            "links": {
                                "total": len(links_data),
                                "internal": internal_links_count,
                                "external": external_links_count,
                                "sample": links_data[:10] 
                            },
                            "images": {
                                "total": len(images_data),
                                "with_alt": images_with_alt_count,
                                "without_alt": len(images_data) - images_with_alt_count,
                                "sample": images_data[:5]
                            },
                            "content": {
                                "word_count": word_count,
                                "sample": content_sample
                            },
                            "schema_markup": schema_markup,
                            "technical": technical_data,
                            "error": None # Explicitly set error to None on success
                        }
                        
                        logger.info(f"Successfully analyzed: {url}, Title: {title[:50]}...")
                        
                        # Save to database if requested
                        if save_to_db:
                            try:
                                # Find the search result ID if available
                                search_result_id = None
                                if hasattr(self, 'current_query_id') and self.current_query_id:
                                    try:
                                        from database import get_session, close_session, SearchResult, save_page_analysis
                                        session = get_session()
                                        try:
                                            search_result = session.query(SearchResult).filter(
                                                SearchResult.query_id == self.current_query_id,
                                                SearchResult.url.like(f"%{urlparse(url).netloc}%")
                                            ).first()
                                            
                                            if search_result:
                                                search_result_id = search_result.id
                                        finally:
                                            close_session(session)
                                    except (ImportError, NameError):
                                        logger.warning("Database modules not available for saving page analysis")
                                    except Exception as e:
                                        logger.error(f"Error finding search result ID: {str(e)}")
                                
                                if search_result_id:
                                    try:
                                        from database import save_page_analysis
                                        save_page_analysis(search_result_id, analysis_data)
                                        logger.info(f"Saved page analysis to database for URL: {url}")
                                    except (ImportError, NameError):
                                        logger.warning("Database modules not available for saving page analysis")
                                    except Exception as e:
                                        logger.error(f"Error saving page analysis: {str(e)}")
                            except Exception as e:
                                logger.error(f"Error in database operations: {str(e)}")
                        
                        return analysis_data
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout on attempt {attempt+1}/{max_retries} for {url}")
                    if attempt == max_retries - 1:  # If this was the last attempt
                        return {"url": url, "title": "", "description": "", "error": "Timeout after multiple attempts", "seo_details": {}}
                    # Otherwise continue to the next retry attempt
                    continue
                except Exception as e:
                    logger.error(f"Error on attempt {attempt+1}/{max_retries} for {url}: {str(e)}")
                    if attempt == max_retries - 1:  # If this was the last attempt
                        return {"url": url, "title": "", "description": "", "error": str(e), "seo_details": {}}
                    # Otherwise continue to the next retry attempt
                    continue
        
            # This should only be reached if all retries failed but didn't raise exceptions
            return {"url": url, "title": "", "description": "", "error": "All retry attempts failed", "seo_details": {}}
        finally:
            # Close the session if we created it
            if session_created and _session:
                await _session.close()

    async def analyze_serp_for_api(self, query, num_results=10):
        """
        Perform SERP analysis for the API: search, analyze pages, save, and return results.
        """
        logger.info(f"Starting API SERP analysis for query: '{query}' with {num_results} results")
        raw_search_results = await self.search_google(query, num_results)

        analyzed_pages = []
        if not raw_search_results:
            logger.warning(f"No search results returned from search_google for query: {query}")
        else:
            # Use aiohttp.ClientSession for concurrent page fetching in analyze_page
            async with aiohttp.ClientSession() as http_session:
                tasks = []
                for result in raw_search_results:
                    if result.get('url'):
                        tasks.append(self.analyze_page(result['url'], http_session))
                
                # Gather results from all analyze_page tasks
                # Use return_exceptions=True to prevent one failed task from stopping others
                page_analysis_results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, analyzed_data in enumerate(page_analysis_results):
                    original_result = raw_search_results[i] # Assuming order is maintained
                    if isinstance(analyzed_data, Exception):
                        logger.error(f"Exception during page analysis for {original_result.get('url')}: {analyzed_data}")
                        analyzed_pages.append({
                            "url": original_result.get('url'),
                            "title": original_result.get('title', 'N/A'),
                            "description": original_result.get('snippet', 'Failed to analyze page details.'),
                            "error_detail": str(analyzed_data)
                        })
                    elif analyzed_data:
                        # Merge raw search result data (like original snippet if analysis fails for description)
                        # with detailed analyzed data. Analyzed data takes precedence for common fields.
                        merged_data = {**original_result, **analyzed_data} 
                        analyzed_pages.append(merged_data)
                    else:
                        # Fallback if analyze_page somehow returns None but not an exception
                         analyzed_pages.append({
                            "url": original_result.get('url'),
                            "title": original_result.get('title', 'N/A'),
                            "description": original_result.get('snippet', 'Page analysis returned no data.'),
                        })

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_query = re.sub(r'\W+', '_', query) # Sanitize query for filename
        base_filename = f"{filename_query}_{timestamp}"
        json_filename = f"{base_filename}.json"
        
        # Prepare final results structure for API response
        output_data = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "num_requested": num_results,
            "num_returned_search": len(raw_search_results if raw_search_results else []),
            "num_analyzed_pages": len(analyzed_pages),
            "results": analyzed_pages,
            "files": {
                "json": json_filename,
                # "csv": f"{base_filename}.csv" # Placeholder for CSV
            }
        }

        # Save to JSON file
        json_filepath = os.path.join("results", json_filename)
        try:
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully saved results to {json_filepath}")
        except Exception as e:
            logger.error(f"Error saving results to JSON {json_filepath}: {e}")
            # Still return data even if save fails

        return output_data
    
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
            
            # Construct the search URL
            params = {
                "q": query,
                "count": num_results * 2,  # Request more results than needed
                "setlang": "en-US"
            }
            
            search_url = f"https://www.bing.com/search?{urlencode(params)}"
            
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
    
    async def _search_with_playwright(self, query, num_results=6):
        """
        Search Google using Playwright browser automation.
        This method provides a more reliable way to extract search results
        by using a real browser instance.
        """
        try:
            logger.info(f"Starting Playwright Google search for: {query}")
            
            # Respect rate limits
            self._respect_rate_limits()
            
            async with async_playwright() as p:
                # Prepare Playwright proxy configuration
                proxy_config_playwright = None
                raw_proxy_url = None # Store the raw URL for logging purposes
                try:
                    raw_proxy_url = proxy_manager.get_proxy()
                    if raw_proxy_url:
                        parsed_url = urlparse(raw_proxy_url)
                        proxy_config_playwright = {"server": f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"}
                        if parsed_url.username:
                            proxy_config_playwright["username"] = parsed_url.username
                        if parsed_url.password:
                            proxy_config_playwright["password"] = parsed_url.password
                        logger.info(f"Playwright will use proxy server: {proxy_config_playwright['server']}")
                    else:
                        logger.info("No proxy returned by proxy_manager for Playwright search.")
                except NameError:
                    logger.warning("proxy_manager not available for Playwright search")
                except Exception as e:
                    logger.error(f"Error configuring proxy for Playwright: {str(e)}")

                # Launch browser with stealth mode and proxy if configured
                browser = await p.chromium.launch(
                    headless=self.headless,
                    proxy=proxy_config_playwright
                )
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent=self._get_random_user_agent(),
                    locale="en-US"
                )
                
                # Add stealth mode
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [{name: 'Chrome PDF Plugin'}, {name: 'Chrome PDF Viewer'}, {name: 'Native Client'}] });
                    window.chrome = { runtime: {} };
                """)
                
                # Create a new page
                page = await context.new_page()
                
                # Construct the search URL
                params = {
                    "q": query,
                    "num": num_results * 2,  # Request more results than needed
                    "hl": "en",
                    "gl": "us",
                    "pws": "0"  # Disable personalized results
                }
                
                # Build the query string
                query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                search_url = f"https://www.google.com/search?{query_string}"
                
                logger.info(f"Navigating to: {search_url}")
                
                # Navigate to the search URL with a longer timeout
                try:
                    await page.goto(search_url, wait_until="load", timeout=30000)
                except Exception as e:
                    logger.warning(f"Page navigation timeout: {str(e)}")
                    # Continue anyway as the page might have partially loaded
                
                # Wait a moment for any JavaScript to execute
                await asyncio.sleep(2)
                
                # Try multiple selectors that are likely to exist in any Google response
                selectors_to_try = ["#search", "#main", "#center_col", "body", "#rcnt"]
                found_selector = None
                
                for selector in selectors_to_try:
                    try:
                        # Use a shorter timeout for each individual selector
                        await page.wait_for_selector(selector, timeout=5000)
                        found_selector = selector
                        logger.info(f"Found selector: {selector}")
                        break
                    except Exception:
                        continue
                
                if not found_selector:
                    logger.warning("Could not find any expected selectors on the page")
                
                # Save screenshot for debugging
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"debug/google_screenshot_{timestamp}.png"
                await page.screenshot(path=screenshot_path)
                logger.info(f"Saved screenshot to {screenshot_path}")
                
                # Save HTML for debugging
                html_content = await page.content()
                debug_file = f"debug/google_playwright_{timestamp}.html"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"Saved HTML to {debug_file} for debugging")
                
                # Check for CAPTCHA or other anti-bot measures
                captcha_indicators = [
                    "#captcha-form", 
                    "form[action*='captcha']", 
                    "img[src*='captcha']",
                    "div.g-recaptcha",
                    "#recaptcha"
                ]
                
                captcha_detected = False
                captcha_element = None
                
                for indicator in captcha_indicators:
                    captcha_element = await page.query_selector(indicator)
                    if captcha_element:
                        logger.warning(f"CAPTCHA detected on Google search page via selector: {indicator}")
                        captcha_detected = True
                        break
                
                # Also check content for common CAPTCHA phrases
                if not captcha_detected:
                    captcha_phrases = ["captcha", "unusual traffic", "automated queries", "verify you're a human"]
                    for phrase in captcha_phrases:
                        if phrase in html_content.lower():
                            logger.warning(f"CAPTCHA detected on Google search page via phrase: {phrase}")
                            captcha_detected = True
                            break
                
                # If CAPTCHA is detected, try to solve it
                if captcha_detected:
                    self.captcha_detected = True
                    self.block_count += 1
                    
                    # Try to solve the CAPTCHA
                    try:
                        solved = await self._solve_captcha(page)
                        if solved:
                            logger.info("Successfully solved CAPTCHA!")
                            # Wait for page to load after CAPTCHA solution
                            await asyncio.sleep(3)
                            # Get updated HTML content
                            html_content = await page.content()
                            debug_file = f"debug/google_after_captcha_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                            with open(debug_file, "w", encoding="utf-8") as f:
                                f.write(html_content)
                            logger.info(f"Saved post-CAPTCHA HTML to {debug_file}")
                        else:
                            logger.warning("Failed to solve CAPTCHA")
                            await browser.close()
                            return []
                    except Exception as e:
                        logger.error(f"Error solving CAPTCHA: {str(e)}")
                        await browser.close()
                        return []
                
                # Extract search results
                results = []
                
                # Try multiple selectors for search result containers
                # First, try a more general approach to find all search results
                try:
                    # This JavaScript will find all likely search result containers
                    general_results = await page.evaluate("""
                        function() {
                            const results = [];
                            
                            // Find all elements that look like search results
                            // Look for elements with titles (h3) and links
                            const h3Elements = Array.from(document.querySelectorAll('h3'));
                            
                            h3Elements.forEach(function(h3, index) {
                                // Find the closest anchor tag
                                const linkElement = h3.closest('a') || h3.querySelector('a') || h3.parentElement.querySelector('a');
                                if (!linkElement) return;
                                
                                const url = linkElement.href;
                                if (!url || !url.startsWith('http') || url.includes('google.com/search')) return;
                                
                                const title = h3.textContent.trim();
                                if (!title) return;
                                
                                // Try to find a description near this title
                                // Look for nearby paragraphs or divs with text
                                let description = "";
                                let container = h3.parentElement;
                                for (let i = 0; i < 3; i++) { // Go up to 3 levels up to find a container
                                    if (!container) break;
                                    
                                    // Look for text nodes or paragraphs in this container
                                    const textElements = Array.from(container.querySelectorAll('p, div, span')).filter(function(el) {
                                        // Filter out elements that are part of the title
                                        return !el.contains(h3) && 
                                               el.textContent.trim().length > 20 && // Must have some substantial text
                                               !el.querySelector('h3'); // Shouldn't contain other titles
                                    });
                                    
                                    if (textElements.length > 0) {
                                        description = textElements[0].textContent.trim();
                                        break;
                                    }
                                    
                                    container = container.parentElement;
                                }
                                
                                results.push({
                                    title: title,
                                    url: url,
                                    description: description,
                                    position: index + 1
                                });
                            });
                            
                            return results.filter(function(r) { return r.url && r.title; }); // Ensure we have at least URL and title
                        }
                    """)
                    
                    if general_results and len(general_results) > 0:
                        logger.info(f"Found {len(general_results)} results using general approach")
                        for item in general_results:
                            # Add query to each result
                            item["query"] = query
                            results.append(item)
                        
                        # If we found enough results, return them
                        if len(results) >= num_results:
                            results = results[:num_results]  # Limit to requested number
                            await browser.close()
                            return results
                except Exception as e:
                    logger.error(f"Error with general search results extraction: {str(e)}")
                
                # If general approach didn't work, try specific selectors
                selectors = [
                    "div.g", "div.kvH3mc", "div.Ww4FFb", "div.Gx5Zad", "div.MjjYud",
                    "div.tF2Cxc", "div.yuRUbf", "div.rc", 
                    "div[data-header-feature]", "div[jscontroller][data-hveid]",
                    "div[data-hveid]", "div.v7W49e", "div.ULSxyf", "div.hlcw0c",
                    "div.MjjYud", "div.g.Ww4FFb.vt6azd.tF2Cxc", "div.jtfYYd"
                ]
                
                for selector in selectors:
                    # Use JavaScript to extract results
                    result_data = await page.evaluate(f"""
                        (selector) => {{
                            const containers = document.querySelectorAll(selector);
                            const results = [];
                            
                            containers.forEach((container, index) => {{
                                // Extract title
                                const titleElement = container.querySelector('h3');
                                if (!titleElement) return;
                                
                                const title = titleElement.textContent.trim();
                                
                                // Extract URL
                                const linkElement = container.querySelector('a');
                                if (!linkElement) return;
                                
                                const url = linkElement.href;
                                if (!url.startsWith('http')) return;
                                
                                // Extract description
                                let description = "";
                                const descSelectors = [
                                    'div.VwiC3b', 'div.Z26q7c.UK95Uc', 'span.MUxGbd.yDYNvb.lyLwlc',
                                    'div[data-sncf~="1"]', 'span.st', 'div.s'
                                ];
                                
                                for (const descSelector of descSelectors) {{
                                    const descElement = container.querySelector(descSelector);
                                    if (descElement) {{
                                        description = descElement.textContent.trim();
                                        break;
                                    }}
                                }}
                                
                                results.push({{
                                    title,
                                    url,
                                    description,
                                    position: index + 1
                                }});
                            }});
                            
                            return results;
                        }}
                    """, selector)
                    
                    logger.info(f"Selector '{selector}' found {len(result_data)} elements")
                    
                    if result_data and len(result_data) > 0:
                        for item in result_data:
                            # Add query to each result
                            item["query"] = query
                            results.append(item)
                        
                        # Stop once we have enough results
                        if len(results) >= num_results:
                            results = results[:num_results]  # Limit to requested number
                            break
                
                # Close browser
                await browser.close()
                
                logger.info(f"Extracted {len(results)} results using Playwright")
                return results
                
        except Exception as e:
            logger.error(f"Error in Playwright Google search: {str(e)}")
            traceback.print_exc()
            return []
    
    async def _solve_captcha(self, page):
        """
        Attempt to solve Google CAPTCHA using OCR and image processing.
        
        Args:
            page: Playwright page object with CAPTCHA loaded
            
        Returns:
            bool: True if CAPTCHA was solved, False otherwise
        """
        try:
            logger.info("Attempting to solve CAPTCHA using OCR")
            
            # First, try to find the image CAPTCHA
            captcha_img = await page.query_selector("img[src*='captcha']")
            if not captcha_img:
                # Try other potential selectors
                captcha_img = await page.query_selector("#captcha")
            
            if not captcha_img:
                logger.warning("Could not find CAPTCHA image element")
                return False
            
            # Take a screenshot of the CAPTCHA
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            captcha_screenshot = f"debug/captcha_{timestamp}.png"
            await captcha_img.screenshot(path=captcha_screenshot)
            logger.info(f"Saved CAPTCHA image to {captcha_screenshot}")
            
            # Process the CAPTCHA image to improve OCR accuracy
            captcha_text = self._process_captcha_image(captcha_screenshot)
            
            if not captcha_text or len(captcha_text) < 4:
                logger.warning(f"OCR failed to extract valid text from CAPTCHA: '{captcha_text}'")
                return False
            
            logger.info(f"Extracted CAPTCHA text: '{captcha_text}'")
            
            # Find the input field for the CAPTCHA
            input_field = await page.query_selector("input[name='captcha']")
            if not input_field:
                # Try other potential input field selectors
                input_field = await page.query_selector("input[id*='captcha']")
            
            if not input_field:
                logger.warning("Could not find CAPTCHA input field")
                return False
            
            # Enter the CAPTCHA text
            await input_field.fill(captcha_text)
            
            # Find and click the submit button
            submit_button = await page.query_selector("input[type='submit']")
            if not submit_button:
                # Try other potential submit button selectors
                submit_button = await page.query_selector("button[type='submit']")
            
            if not submit_button:
                logger.warning("Could not find submit button")
                return False
            
            # Click the submit button
            await submit_button.click()
            
            # Wait for navigation to complete
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                logger.warning(f"Navigation timeout after CAPTCHA submission: {str(e)}")
            
            # Check if we're still on a CAPTCHA page
            current_url = page.url
            if "captcha" in current_url.lower():
                logger.warning("Still on CAPTCHA page after submission, solution failed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error solving CAPTCHA: {str(e)}")
            traceback.print_exc()
            return False
    
    def _process_captcha_image(self, image_path):
        """
        Process CAPTCHA image to improve OCR accuracy.
        
        Args:
            image_path: Path to the CAPTCHA image
            
        Returns:
            str: Extracted text from the CAPTCHA
        """
        try:
            # Read the image
            img = cv2.imread(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold to get black and white image
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
            
            # Noise removal
            kernel = np.ones((2, 2), np.uint8)
            opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            
            # Save the processed image for debugging
            processed_path = image_path.replace('.png', '_processed.png')
            cv2.imwrite(processed_path, opening)
            
            # Use pytesseract to extract text
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
            text = pytesseract.image_to_string(opening, config=custom_config)
            
            # Clean up the text
            text = text.strip().replace(' ', '').replace('\n', '')
            
            return text
            
        except Exception as e:
            logger.error(f"Error processing CAPTCHA image: {str(e)}")
            traceback.print_exc()
            return ""
    
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
            
            async with aiohttp.ClientSession(headers=headers) as session:
                proxy_url_http = None
                try:
                    proxy_url_http = proxy_manager.get_proxy() # Get string URL directly
                    if proxy_url_http:
                        logger.info(f"Using proxy for direct HTTP search: {proxy_url_http}")
                    else:
                        logger.info("No proxy returned by proxy_manager for direct HTTP search.")
                except NameError:
                    logger.warning("proxy_manager not available for direct HTTP search")
                except Exception as e:
                    logger.error(f"Error getting proxy for direct HTTP: {str(e)}")

                # Make the request
                async with session.get(search_url, timeout=15, proxy=proxy_url_http) as response:
                    logger.info(f"Direct HTTP request status code: {response.status}")
                    
                    # Check if the request was successful
                    if response.status != 200:
                        logger.error(f"Direct HTTP request failed with status code {response.status}")
                        # Removed: if proxy_url_http: proxy_manager.report_failure(proxy_url_http, is_block=(response.status == 403 or response.status == 429))
                        return []
                    
                    # Removed: if proxy_url_http: proxy_manager.report_success(proxy_url_http)

                    # Get the HTML content
                    html_content = await response.text()
                    
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
                        'div.g', 'div.kvH3mc', 'div.Ww4FFb', 'div.Gx5Zad', 'div.MjjYud',
                        'div.tF2Cxc', 'div.yuRUbf', 'div.rc', 
                        'div[data-header-feature]', 'div[jscontroller][data-hveid]'
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
                            desc_selectors = [
                                'div.VwiC3b', 'div.Z26q7c.UK95Uc', 'span.MUxGbd.yDYNvb.lyLwlc',
                                'div[data-sncf~="1"]', 'span.st', 'div.s'
                            ]
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
