import asyncio
import os
import json
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

# Enhanced Google result extraction function
def extract_google_results(html, num_results=6):
    """
    Enhanced function to extract Google search results from HTML
    using multiple approaches for better resilience against blocks
    """
    search_results = []
    
    try:
        # First, check if we're dealing with a CAPTCHA page
        if "unusual traffic" in html.lower() or "captcha" in html.lower() or "sorry" in html.lower():
            print("DETECTED: Google CAPTCHA or block page in HTML content")
            return []
        
        # Use BeautifulSoup to parse the HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try multiple selectors for Google search results
        # Google frequently changes their HTML structure
        selectors = [
            "div.g",  # Traditional format
            "div.Gx5Zad",  # Another common format
            "div.tF2Cxc",  # Another possible format
            "div.yuRUbf",  # Another possible container
            "div[jscontroller]",  # Generic approach
            "div.rc",  # Old but sometimes still used
            "div.MjjYud",  # Newer format
            "div.v7W49e"   # Another newer format
        ]
        
        # Try each selector until we find results
        result_elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                print(f"Found {len(elements)} results using selector: {selector}")
                result_elements = elements
                break
        
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
                
                # Extract snippet
                snippet = ""
                snippet_element = element.select_one("div.VwiC3b") or element.select_one("span.st") or element.select_one("div.s")
                if snippet_element:
                    snippet = snippet_element.get_text().strip()
                
                # Add to results
                search_results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })
                
                # Stop if we have enough results
                if len(search_results) >= num_results:
                    break
                    
            except Exception as e:
                print(f"Error processing result element: {str(e)}")
                continue
        
        # If we still don't have results, try a more generic approach
        if not search_results:
            print("Using fallback method to extract search results")
            # Look for any links that might be search results
            all_links = soup.find_all("a")
            unique_urls = set()
            
            for link in all_links:
                href = link.get("href")
                if href and href.startswith("http") and "google.com" not in href and not href.startswith("https://webcache.googleusercontent.com"):
                    # Skip duplicate URLs
                    if href in unique_urls:
                        continue
                    unique_urls.add(href)
                    
                    # Try to find a title near this link
                    title_element = link.find("h3") or link.parent.find("h3") or link
                    title = title_element.get_text().strip() if title_element else ""
                    
                    # Skip if no meaningful title
                    if not title or title.lower() in ["cached", "similar", "translate this page"]:
                        continue
                        
                    url = href
                    
                    # Try to find a snippet near this link
                    snippet = ""
                    
                    # Look in parent elements for text that might be a snippet
                    parent = link.parent
                    for _ in range(3):  # Check up to 3 levels up
                        if parent:
                            # Find all text nodes that aren't in h3 tags
                            texts = [t for t in parent.find_all(text=True, recursive=True) 
                                    if t.parent.name != 'h3' and t.strip()]
                            if texts:
                                snippet = " ".join([t.strip() for t in texts])
                                break
                            parent = parent.parent
                    
                    # Add this result
                    search_results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
                    
                    # Stop if we have enough results
                    if len(search_results) >= num_results:
                        break
        
        # Try regex extraction as a last resort if we still have no results
        if not search_results:
            print("Attempting to extract results with regex patterns")
            import re
            
            # Pattern to match URLs in Google search results
            url_pattern = r'href="(https?://[^"]+)"'
            urls = re.findall(url_pattern, html)
            
            # Filter out Google URLs and duplicates
            unique_urls = set()
            filtered_urls = []
            for url in urls:
                if "google.com" not in url and url not in unique_urls:
                    unique_urls.add(url)
                    filtered_urls.append(url)
            
            print(f"Found {len(unique_urls)} unique URLs with regex")
            
            # Create basic results from the URLs
            for url in filtered_urls[:num_results]:
                # Extract a simple title from the URL
                domain = url.split("//")[1].split("/")[0]
                title = domain
                
                search_results.append({
                    "title": title,
                    "url": url,
                    "snippet": ""
                })
            
            print(f"Extracted {len(search_results)} results with regex method")
        
        return search_results
        
    except Exception as e:
        print(f"Error processing Google HTML: {str(e)}")
        return []

async def test_search_with_crawler(query="best beaches in florida", num_results=6):
    """
    Test function to search Google using crawl4ai and extract results
    """
    print(f"\n===== TESTING CRAWLER SEARCH FOR: '{query}' =====\n")
    
    # Create search URL
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&gl=us&hl=en&cr=countryUS&pws=0"
    
    # Use AsyncWebCrawler to fetch the page
    async with AsyncWebCrawler() as crawler:
        # Configure browser options
        browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-extensions',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ]
        
        # Try with Oxylabs proxy if environment variables are set
        proxy_url = None
        if os.environ.get('OXYLABS_USERNAME') and os.environ.get('OXYLABS_PASSWORD'):
            username = os.environ.get('OXYLABS_USERNAME')
            password = os.environ.get('OXYLABS_PASSWORD')
            proxy_url = f"http://{username}:{password}@pr.oxylabs.io:7777"
            print(f"Using Oxylabs proxy")
        
        # Crawl the page
        print(f"Fetching search results from: {search_url}")
        result = await crawler.arun(
            search_url,
            headless=True,
            proxy=proxy_url,
            cache_mode="bypass",
            wait_until="networkidle",
            page_timeout=30000,
            delay_before_return_html=0.5,
            word_count_threshold=100,
            scan_full_page=True,
            scroll_delay=0.3,
            remove_overlay_elements=True
        )
        
        if not result.success:
            print(f"Error fetching search results: {result.error_message}")
            return []
        
        # Save the HTML for debugging
        with open("debug_search_results.html", "w", encoding="utf-8") as f:
            f.write(result.html)
        print("Saved HTML to debug_search_results.html")
        
        # Extract search results
        search_results = extract_google_results(result.html, num_results)
        
        # Print results
        print(f"\nFound {len(search_results)} search results:")
        for i, result in enumerate(search_results):
            print(f"\n{i+1}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Snippet: {result['snippet'][:100]}..." if result['snippet'] else "   No snippet")
        
        # Save results to JSON
        with open("debug_search_results.json", "w", encoding="utf-8") as f:
            json.dump(search_results, f, indent=2, ensure_ascii=False)
        print("\nSaved results to debug_search_results.json")
        
        return search_results

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_search_with_crawler())
