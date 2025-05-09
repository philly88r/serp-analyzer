import asyncio
import json
import os
import random
import time
import re
from urllib.parse import quote_plus, urlparse
from datetime import datetime
import logging
from bs4 import BeautifulSoup

# Attempt to use crawl4ai if available, otherwise a basic fallback
try:
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    print("Warning: crawl4ai library not found. Page analysis will be limited.")
    # Define dummy classes if crawl4ai is not available to avoid runtime errors
    class AsyncWebCrawler:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
        async def arun(self, url, headless, config, user_agent):
            # Basic fallback using requests if crawl4ai is not present
            # This won't execute JavaScript or handle complex sites well
            import requests
            print(f"Fallback: Fetching {url} with requests")
            try:
                response = requests.get(url, headers={'User-Agent': user_agent}, timeout=10)
                response.raise_for_status()
                return type('obj', (object,), {'html': response.text, 'markdown': 'Markdown not available (crawl4ai missing)'})
            except requests.RequestException as e:
                print(f"Fallback request failed: {e}")
                return type('obj', (object,), {'html': f'<html><body>Error fetching page: {e}</body></html>', 'markdown': ''})

    class CrawlerRunConfig:
        def __init__(self, **kwargs):
            pass


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stealth_serp_analyzer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("StealthSerpAnalyzer")

class StealthSerpAnalyzer:
    def __init__(self, headless=True):
        self.headless = headless
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"
        ]
        self.search_engine_url = "https://html.duckduckgo.com/html/" # Using DuckDuckGo HTML version for simplicity
        os.makedirs("results", exist_ok=True)
        os.makedirs("debug_pages", exist_ok=True)

    def _get_random_user_agent(self):
        return random.choice(self.user_agents)

    async def _fetch_page_html(self, url, purpose="search"):
        # Try with crawl4ai if available
        if CRAWL4AI_AVAILABLE:
            logger.info(f"Using crawl4ai to fetch {url} (purpose: {purpose})")
            user_agent = self._get_random_user_agent()
            logger.debug(f"Selected User-Agent for crawl4ai: {user_agent}")
            try:
                logger.info("Initializing AsyncWebCrawler...")
                async with AsyncWebCrawler() as crawler:
                    logger.info("AsyncWebCrawler initialized.")
                    config_params = {
                        "magic": True, 
                        "page_timeout": 20000, # 20 seconds
                        "cache_mode": "bypass", 
                        "wait_until": "domcontentloaded",
                        "remove_overlay_elements": True
                    }
                    if purpose == "analyze": # More thorough for analysis
                        config_params["wait_until"] = "networkidle"
                        config_params["page_timeout"] = 30000 # 30 seconds for analysis
                        config_params["scan_full_page"] = True
                        config_params["scroll_delay"] = 0.3

                    logger.info(f"Attempting to create CrawlerRunConfig with params: {config_params}")
                    config = CrawlerRunConfig(**config_params)
                    logger.info("CrawlerRunConfig created successfully.")
                    
                    logger.info(f"Attempting crawler.arun for url: {url}")
                    crawl_result = await crawler.arun(
                        url=url,
                        headless=self.headless,
                        config=config,
                        user_agent=user_agent
                    )
                    html_is_present = crawl_result.html is not None and len(crawl_result.html) > 0
                    logger.info(f"crawler.arun finished. HTML is {'Present' if html_is_present else 'None or Empty'}. Markdown is {'Present' if crawl_result.markdown else 'None'}.")

                # Save HTML for debugging, even if empty, to confirm file creation
                # Ensure debug_pages directory exists (it's created in __main__ and constructor)
                filename_safe_url = re.sub(r'[^a-zA-Z0-9]', '_', url)[:100]
                debug_path = os.path.join("debug_pages", f"{purpose}_{filename_safe_url}_{datetime.now().strftime('%Y%m%d%H%M%S')}.html")
                try:
                    with open(debug_path, "w", encoding="utf-8") as f:
                        f.write(crawl_result.html or "<!-- No HTML content retrieved -->")
                    logger.info(f"Saved debug HTML to {debug_path} (Length: {len(crawl_result.html or '')})")
                except Exception as e_write:
                    logger.error(f"Failed to write debug HTML to {debug_path}: {e_write}")

                return crawl_result.html, crawl_result.markdown
            except Exception as e:
                # Enhanced exception logging
                logger.error(f"Exception type caught in _fetch_page_html for {url}: {type(e)}")
                logger.error(f"Exception message in _fetch_page_html for {url}: {str(e)}")
                logger.exception(f"Full traceback for error fetching page {url} with crawl4ai:")
                return None, None

        # Fallback to httpx if crawl4ai is not available
        if not CRAWL4AI_AVAILABLE and purpose == "search":
             # Basic fallback for search if crawl4ai isn't there
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers={'User-Agent': user_agent}, follow_redirects=True, timeout=15)
                    response.raise_for_status()
                    return response.text, None # No markdown for this simple fetch
            except Exception as e:
                logger.error(f"Error fetching search page {url} with httpx: {e}")
                return None, None

        # Fallback to requests if crawl4ai is not available and purpose is analyze
        if not CRAWL4AI_AVAILABLE and purpose == "analyze":
            logger.warning("crawl4ai not available, detailed page analysis for SEO stats will be limited.")
            # Use the basic requests fallback from the dummy AsyncWebCrawler
            crawler = AsyncWebCrawler()
            result = await crawler.arun(url=url, headless=self.headless, config=None, user_agent=user_agent)
            return result.html, result.markdown

    async def search_google(self, query, num_results=10):
        logger.info(f"Attempting search for '{query}' using DuckDuckGo HTML as primary")
        # Using DuckDuckGo's HTML version is simpler and less prone to blocks
        # than trying to scrape Google directly without robust proxy/CAPTCHA infrastructure.
        params = {'q': query}
        search_url = self.search_engine_url + "?" + "&".join(f"{k}={quote_plus(v)}" for k, v in params.items())
        
        html_content, _ = await self._fetch_page_html(search_url, purpose="search")

        if not html_content:
            logger.error(f"Failed to fetch search results for '{query}'")
            return []

        soup = BeautifulSoup(html_content, 'html.parser')
        results = []
        
        # DuckDuckGo HTML parsing
        result_items = soup.select('div.results div.result')

        for i, item in enumerate(result_items):
            if i >= num_results:
                break
            
            try:
                title_tag = item.select_one('h2 a.result__a')
                snippet_tag = item.select_one('a.result__snippet') # Snippet is also a link in DDG HTML

                title = title_tag.get_text(strip=True) if title_tag else ""
                url = title_tag.get('href') if title_tag else ""
                description = snippet_tag.get_text(strip=True) if snippet_tag else ""

                if title and url:
                    # Basic cleanup for DDG redirect URLs if necessary, though html.duckduckgo.com usually gives direct links
                    if url.startswith("//duckduckgo.com/l/"):
                        try:
                            from urllib.parse import parse_qs, urlsplit # Import here to keep it local to usage
                            parsed_url = urlsplit(url)
                            url = parse_qs(parsed_url.query).get('uddg', [url])[0]
                        except Exception as e_parse_ddg_url:
                            logger.warning(f"Could not parse DDG redirect URL {url}: {e_parse_ddg_url}")
                    
                    results.append({
                        "position": i + 1,
                        "title": title,
                        "url": url,
                        "description": description,
                        "query": query
                    })
                else:
                    logger.warning(f"Skipping search result item {i+1} for query '{query}' due to missing title or URL.")
                    if not title_tag:
                        logger.debug(f"Title tag not found for item {i+1}.")
                    if not url: # Check url directly as it depends on title_tag
                        logger.debug(f"URL not found or derived for item {i+1}.")
                    logger.debug(f"Problematic item HTML (first 500 chars): {item.prettify()[:500]}")

            except Exception as e_parse_item:
                logger.error(f"Error parsing search result item {i+1} for query '{query}': {e_parse_item}")
                logger.debug(f"Problematic item HTML (full, up to 1000 chars): {item.prettify()[:1000]}")
                # Continue to the next item
        
        logger.info(f"Found {len(results)} results for '{query}' via DuckDuckGo HTML.")
        return results

    async def analyze_page(self, url):
        logger.info(f"Analyzing page: {url}")
        if not CRAWL4AI_AVAILABLE:
             logger.warning(f"crawl4ai is not available. Detailed SEO analysis for {url} will be significantly limited.")
        
        html_content, markdown_content = await self._fetch_page_html(url, purpose="analyze")

        if not html_content:
            logger.error(f"Failed to fetch HTML for page analysis: {url}")
            return {"url": url, "success": False, "error": "Failed to fetch page HTML"}

        soup = BeautifulSoup(html_content, 'html.parser')
        
        title_tag = soup.title
        title = title_tag.get_text(strip=True) if title_tag else ""
        
        meta_description = ""
        meta_keywords = ""
        for meta in soup.find_all("meta"):
            name = meta.get("name", "").lower()
            if name == "description":
                meta_description = meta.get("content", "")
            elif name == "keywords":
                meta_keywords = meta.get("content", "")

        h1_tags = [h1.get_text(strip=True) for h1 in soup.find_all("h1")]
        h2_tags = [h2.get_text(strip=True) for h2 in soup.find_all("h2")]
        h3_tags = [h3.get_text(strip=True) for h3 in soup.find_all("h3")]

        internal_links = []
        external_links = []
        
        try:
            parsed_url = urlparse(url)
            base_domain = parsed_url.netloc
        except Exception: # Handle potential malformed URLs from search
            base_domain = ""


        for link_tag in soup.find_all("a", href=True):
            href = link_tag["href"]
            if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            
            try:
                link_parsed = urlparse(href)
                if link_parsed.scheme and link_parsed.netloc: # Absolute URL
                    if link_parsed.netloc == base_domain:
                        internal_links.append(href)
                    else:
                        external_links.append(href)
                elif href.startswith("/"): # Relative to root
                     if base_domain:
                        internal_links.append(f"{parsed_url.scheme}://{base_domain}{href}")
                # Other relative URLs can be complex, skipping for brevity here
            except Exception:
                logger.warning(f"Could not parse link: {href} on page {url}")


        images = []
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src")
            alt = img_tag.get("alt", "")
            if src:
                try:
                    img_parsed = urlparse(src)
                    full_src = src
                    if not img_parsed.scheme and base_domain: # Relative URL
                        if src.startswith("//"):
                             full_src = f"{parsed_url.scheme}:{src}"
                        elif src.startswith("/"):
                             full_src = f"{parsed_url.scheme}://{base_domain}{src}"
                        else: # page-relative
                             full_src = f"{parsed_url.scheme}://{base_domain}{parsed_url.path.rsplit('/',1)[0]}/{src}"
                    images.append({"src": full_src, "alt": alt})
                except Exception:
                    logger.warning(f"Could not parse image src: {src} on page {url}")


        # Page content analysis
        content_text = soup.get_text(separator=' ', strip=True)
        word_count = len(content_text.split())

        analysis = {
            "url": url,
            "success": True,
            "title": title,
            "meta_description": meta_description,
            "meta_keywords": meta_keywords,
            "h1_tags": h1_tags[:5], # limit for brevity
            "h2_tags": h2_tags[:10],
            "h3_tags": h3_tags[:10],
            "word_count": word_count,
            "internal_links_count": len(internal_links),
            "external_links_count": len(external_links),
            "images_count": len(images),
            "content_text_snippet": content_text[:500] + "..." if word_count > 0 else "",
            "markdown_content_snippet": (markdown_content[:500] + "..." if markdown_content else "N/A"),
            "internal_links_sample": internal_links[:5],
            "external_links_sample": external_links[:5],
            "images_sample": images[:5]
        }
        return analysis

    async def analyze_serp(self, query, num_results=5):
        logger.info(f"\n===== ANALYZING SERP FOR QUERY: {query} (Max results: {num_results}) =====\n")
        
        search_results = await self.search_google(query, num_results)
        
        if not search_results:
            logger.warning(f"No search results found for query: {query}")
            return {
                "query": query, "timestamp": datetime.now().isoformat(), "success": False,
                "error": "No search results found", "results_count": 0, "results": []
            }
        
        analyzed_results = []
        for result_item in search_results:
            page_url = result_item.get("url")
            if not page_url:
                logger.warning(f"Search result item missing URL: {result_item.get('title')}")
                analyzed_results.append({**result_item, "page_analysis_success": False, "error": "Missing URL"})
                continue
            
            # Basic URL validation/cleanup
            if page_url.startswith("/url?q="): # Google redirect URL from some scrapers
                try:
                    from urllib.parse import parse_qs
                    parsed_q = parse_qs(urlparse(page_url).query)
                    page_url = parsed_q.get('q', [page_url])[0]
                except Exception:
                    pass


            logger.info(f"Analyzing page from SERP: {page_url}")
            try:
                # Add delay before analyzing each page to be less aggressive
                delay = random.uniform(1, 3) # Random delay between 1-3 seconds
                logger.info(f"Waiting {delay:.2f}s before analyzing {page_url}")
                await asyncio.sleep(delay)

                page_analysis = await self.analyze_page(page_url)
                full_result = {**result_item, **page_analysis, "page_analysis_success": page_analysis.get("success", False)}
                analyzed_results.append(full_result)
            except Exception as e:
                logger.error(f"Error analyzing page {page_url}: {e}")
                analyzed_results.append({
                    **result_item, 
                    "page_analysis_success": False,
                    "error": f"Error during page analysis: {str(e)}"
                })
        
        serp_analysis_data = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "results_count": len(analyzed_results),
            "results": analyzed_results
        }
        self.save_results(serp_analysis_data)
        return serp_analysis_data

    def save_results(self, serp_analysis, output_format="json"):
        query = serp_analysis["query"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^a-zA-Z0-9_]', '_', query)
        
        filename_base = f"results/serp_{safe_query}_{timestamp}"

        if output_format == "json" or output_format == "all":
            json_file = f"{filename_base}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(serp_analysis, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved JSON results to {json_file}")
        
        if output_format == "csv" or output_format == "all":
            csv_file = f"{filename_base}.csv"
            try:
                import pandas as pd
                # Flatten the data for CSV
                flat_results = []
                for res in serp_analysis.get("results", []):
                    # Combine SERP result and page analysis, prefixing page analysis keys
                    flat_row = {
                        'serp_position': res.get('position'),
                        'serp_title': res.get('title'),
                        'serp_url': res.get('url'),
                        'serp_description': res.get('description'),
                        'page_analysis_success': res.get('page_analysis_success'),
                        'page_title': res.get('title'), # from analyze_page
                        'page_meta_description': res.get('meta_description'),
                        'page_word_count': res.get('word_count'),
                        'page_internal_links_count': res.get('internal_links_count'),
                        'page_external_links_count': res.get('external_links_count'),
                        'page_images_count': res.get('images_count'),
                        'page_error': res.get('error')
                    }
                    flat_results.append(flat_row)
                
                if flat_results:
                    df = pd.DataFrame(flat_results)
                    df.to_csv(csv_file, index=False, encoding="utf-8")
                    logger.info(f"Saved CSV results to {csv_file}")
                else:
                    logger.info("No results to save to CSV.")
            except ImportError:
                logger.warning("Pandas library not found. Cannot save CSV results.")
            except Exception as e:
                logger.error(f"Error saving CSV: {e}")

async def main_test():
    print("Starting Stealth SERP Analyzer Test...")
    if not CRAWL4AI_AVAILABLE:
        print("WARNING: crawl4ai library is not installed. Functionality will be limited.")
        print("Please install it with: pip install crawl4ai")
    
    analyzer = StealthSerpAnalyzer(headless=True) # Set to False to see browser
    
    test_query = "python web scraping libraries"
    print(f"Analyzing SERP for query: '{test_query}'")
    
    analysis_results = await analyzer.analyze_serp(test_query, num_results=3) # Small number for test
    
    if analysis_results and analysis_results.get("success"):
        print(f"\nSuccessfully completed SERP analysis for '{test_query}'")
        print(f"Found {analysis_results.get('results_count')} results.")
        for i, res_data in enumerate(analysis_results.get("results", [])):
            print(f"\n--- Result #{i+1} ---")
            print(f"  SERP Title: {res_data.get('title', 'N/A')}")
            print(f"  URL: {res_data.get('url', 'N/A')}")
            if res_data.get("page_analysis_success"):
                print(f"  Page Title: {res_data.get('title', 'N/A')}") # This is the title from page_analysis
                print(f"  Page Word Count: {res_data.get('word_count', 'N/A')}")
            else:
                print(f"  Page Analysis Error: {res_data.get('error', 'Unknown error')}")
    else:
        print(f"\nSERP analysis failed for '{test_query}'.")
        print(f"Error: {analysis_results.get('error', 'Unknown error') if analysis_results else 'No results object'}")

    print("\nStealth SERP Analyzer Test Finished.")

if __name__ == "__main__":
    # To run this: python stealth_serp_analyzer.py
    # Ensure you have crawl4ai installed: pip install crawl4ai
    # Also, crawl4ai needs Playwright browsers: python -m playwright install
    asyncio.run(main_test())
