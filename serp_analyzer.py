import asyncio
import os
import json
import pandas as pd
from urllib.parse import quote_plus
from datetime import datetime
from crawl4ai import AsyncWebCrawler

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
        
        search_url = f"https://www.google.com/search?q={quote_plus(query)}"
        print(f"Searching Google for: {query}")
        
        # Configure browser options
        browser_options = {
            "headless": self.headless,
            # Remove verbose from here as it's likely included in the config
            "cache_mode": "bypass",
            "wait_until": "networkidle",
            "page_timeout": 60000,  # Increased timeout for slower connections
            "delay_before_return_html": 1.0,  # Increased delay for better rendering
            "word_count_threshold": 100,
            "scan_full_page": True,
            "scroll_delay": 0.5,
            "process_iframes": False,
            "remove_overlay_elements": True,
            "magic": True
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
        except Exception as e:
            print(f"Error during search: {str(e)}")
            return search_results
        
        # Extract search results using CSS selectors
        # Google search results are typically in divs with class 'g'
        search_results = []
        
        try:
            # Use Crawl4AI's HTML parser to extract search results
            soup = result.soup
            
            # Find all search result containers
            result_elements = soup.select("div.g")[:num_results]
            
            for element in result_elements:
                try:
                    # Extract title, URL, and snippet
                    title_element = element.select_one("h3")
                    link_element = element.select_one("a")
                    snippet_element = element.select_one("div[data-sncf='1']") or element.select_one("div.VwiC3b")
                    
                    if title_element and link_element and "href" in link_element.attrs:
                        title = title_element.get_text().strip()
                        url = link_element["href"]
                        snippet = snippet_element.get_text().strip() if snippet_element else ""
                        
                        # Only include results with valid URLs (skip Google's internal links)
                        if url.startswith("http") and "google.com" not in url:
                            search_results.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet
                            })
                except Exception as extract_error:
                    print(f"Error extracting search result: {str(extract_error)}")
                    continue
            
            print(f"Found {len(search_results)} search results")
            return search_results
        except Exception as e:
            print(f"Error parsing search results: {str(e)}")
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
        
        # Configure browser options
        browser_options = {
            "url": url,
            "headless": self.headless,
            # Remove verbose from here as it's likely included in the config
            "cache_mode": "bypass",
            "wait_until": "networkidle",
            "page_timeout": 60000,  # Increased timeout for slower connections
            "delay_before_return_html": 1.0,
            "word_count_threshold": 100,
            "scan_full_page": True,
            "scroll_delay": 0.5,
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
        except Exception as e:
            print(f"Error analyzing page {url}: {str(e)}")
            return {
                "url": url,
                "success": False,
                "error": str(e)
            }
            
            if not result.success:
                print(f"Error analyzing page: {result.error_message}")
                return {
                    "url": url,
                    "success": False,
                    "error": result.error_message
                }
            
            # Extract SEO data
            soup = result.soup
            
            # Basic SEO data
            title = soup.title.get_text() if soup.title else "" 
            meta_description = ""
            meta_keywords = ""
            
            # Extract meta tags
            for meta in soup.find_all("meta"):
                if meta.get("name", "").lower() == "description":
                    meta_description = meta.get("content", "")
                elif meta.get("name", "").lower() == "keywords":
                    meta_keywords = meta.get("content", "")
            
            # Extract headings
            h1_tags = [h1.get_text().strip() for h1 in soup.find_all("h1")]
            h2_tags = [h2.get_text().strip() for h2 in soup.find_all("h2")]
            h3_tags = [h3.get_text().strip() for h3 in soup.find_all("h3")]
            
            # Extract links
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
            
            # Extract images
            images = []
            for img in soup.find_all("img", src=True):
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
            
            # Page content analysis
            content_text = result.text
            word_count = len(content_text.split())
            
            # Get clean markdown content
            markdown_content = result.markdown
            
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
        search_results = await self.search_google(query, num_results)
        
        if not search_results:
            print("No search results found")
            return {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "No search results found",
                "results": []
            }
        
        # Analyze each result page
        analyzed_results = []
        for result in search_results:
            analysis = await self.analyze_page(result["url"])
            
            # Combine search result data with page analysis
            full_result = {
                **result,
                **analysis
            }
            
            analyzed_results.append(full_result)
        
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
