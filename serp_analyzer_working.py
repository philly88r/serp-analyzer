import asyncio
import os
import json
import pandas as pd
import re
import requests
import glob
from urllib.parse import quote_plus, urlparse
from datetime import datetime
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

def is_us_domain(url):
    """
    Check if a URL is likely from a US domain.
    
    Args:
        url (str): URL to check
        
    Returns:
        bool: True if the URL is likely from a US domain, False otherwise
    """
    # Parse the URL to get the domain
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    
    # List of common US top-level domains
    us_tlds = ['.com', '.org', '.net', '.edu', '.gov', '.us']
    
    # Check if the domain ends with a US TLD
    if any(domain.endswith(tld) for tld in us_tlds):
        return True
    
    # Check for known non-US country code TLDs
    non_us_tlds = ['.uk', '.ca', '.au', '.de', '.fr', '.es', '.it', '.nl', '.ru', '.cn', '.jp', '.br', '.in']
    if any(domain.endswith(tld) for tld in non_us_tlds):
        return False
    
    # Check for US-specific keywords in the domain
    us_keywords = ['usa', 'america', 'us-', '-us', 'united-states']
    if any(keyword in domain for keyword in us_keywords):
        return True
    
    # Default to True for domains we're not sure about
    return True

def clean_results_directory(query=None):
    """
    Clean up old SERP results files to prevent accumulation.
    If query is provided, only files matching that query will be removed.
    If query is None, all files in the results directory will be removed.
    
    Args:
        query (str, optional): The search query to match in filenames. Defaults to None.
    """
    if not os.path.exists("results"):
        print("Results directory does not exist. Creating it.")
        os.makedirs("results", exist_ok=True)
        return
    
    print("\n===== CLEANING RESULTS DIRECTORY =====")
    print(f"Before cleaning, results directory contains {len(os.listdir('results'))} files")
    
    # If query is None, remove all files in the results directory
    if query is None:
        for file in os.listdir("results"):
            file_path = os.path.join("results", file)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"Removed file: {file_path}")
                except Exception as e:
                    print(f"Could not remove {file_path}: {e}")
    else:
        # Remove only files matching the query
        sanitized_query = query.replace(' ', '_')
        for file in os.listdir("results"):
            file_path = os.path.join("results", file)
            if os.path.isfile(file_path) and (f"serp_{sanitized_query}" in file):
                try:
                    os.remove(file_path)
                    print(f"Removed file: {file_path}")
                except Exception as e:
                    print(f"Could not remove {file_path}: {e}")
    
    print(f"After cleaning, results directory contains {len(os.listdir('results'))} files")
    print("===== CLEANING COMPLETE =====")

class SerpAnalyzer:
    def __init__(self, headless=False):
        """
        Initialize the SERP Analyzer.
        
        Args:
            headless (bool): Whether to run the browser in headless mode
        """
        self.headless = headless
        
        # Create results directory if it doesn't exist
        os.makedirs("results", exist_ok=True)
    
    async def search_google(self, query, num_results=6):
        """
        Search Google for a query and extract the top results.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to extract
            
        Returns:
            list: List of dictionaries containing search results
        """
        # Add US-specific parameters to the search URL
        # gl=us: Sets Google's country to US
        # hl=en: Sets language to English
        # cr=countryUS: Restricts results to US
        # uule=w+CAIQICINVW5pdGVkIFN0YXRlcw: Geolocation encoding for United States
        # lr=lang_en: Limits to English language results
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&gl=us&hl=en&cr=countryUS&uule=w+CAIQICINVW5pdGVkIFN0YXRlcw&lr=lang_en&pws=0"
        
        print(f"Searching Google for: {query}")
        async with AsyncWebCrawler() as crawler:
            # Use parameters supported in version 0.4.247
            result = await crawler.arun(
                search_url,
                headless=self.headless,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            # Extract search results from the HTML
            search_results = []
            
            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(result.html, 'html.parser')
            
            # Try different selectors for Google search results
            selectors = [
                "div.g",  # Traditional format
                "div.Gx5Zad",  # Another common format
                "div.tF2Cxc",  # Another possible format
                "div.yuRUbf",  # Another possible container
                "div[jscontroller]",  # Generic approach
                "div.rc"  # Old but sometimes still used
            ]
            
            # Try each selector until we find results
            result_elements = []
            for selector in selectors:
                result_elements = soup.select(selector)
                if result_elements:
                    print(f"Found results using selector: {selector}")
                    break
            
            # Limit to requested number of results
            result_elements = result_elements[:num_results] if result_elements else []
            
            # If we still don't have results, try a more generic approach
            if not result_elements:
                print("Using fallback method to extract search results")
                # Look for any links that might be search results
                all_links = soup.find_all("a")
                for link in all_links:
                    if link.get("href") and link["href"].startswith("http") and "google.com" not in link["href"]:
                        # Try to find a title near this link
                        title_element = link.find("h3") or link.parent.find("h3") or link
                        title = title_element.get_text().strip() if title_element else "Unknown Title"
                        url = link["href"]
                        
                        # Try to find a snippet near this link
                        snippet = ""
                        snippet_container = link.parent.parent
                        for div in snippet_container.find_all("div"):
                            if div.get_text().strip() and div.get_text().strip() != title:
                                snippet = div.get_text().strip()
                                break
                        
                        # Only include US-based domains
                        if is_us_domain(url):
                            search_results.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet
                            })
                        else:
                            print(f"Skipping non-US domain: {url}")
                        
                        if len(search_results) >= num_results:
                            break
            else:
                # Process the results we found with the selectors
                for element in result_elements:
                    try:
                        # Try multiple approaches to extract title, URL, and snippet
                        title_element = element.select_one("h3") or element.find("h3")
                        
                        # Find the first link in this container
                        link_element = element.select_one("a") or element.find("a")
                        
                        # Try different approaches to find the snippet
                        snippet_element = (
                            element.select_one("div[data-sncf='1']") or 
                            element.select_one("div.VwiC3b") or
                            element.select_one("div.lEBKkf") or
                            element.select_one("span.aCOpRe")
                        )
                        
                        if not snippet_element:
                            # Try a more generic approach to find the snippet
                            for div in element.find_all("div"):
                                if div.get_text().strip() and (not title_element or div.get_text().strip() != title_element.get_text().strip()):
                                    snippet_element = div
                                    break
                        
                        if title_element and link_element and "href" in link_element.attrs:
                            title = title_element.get_text().strip()
                            url = link_element["href"]
                            snippet = snippet_element.get_text().strip() if snippet_element else ""
                            
                            # Only include results with valid URLs (skip Google's internal links)
                            # Also filter for US-based domains only
                            if url.startswith("http") and "google.com" not in url and is_us_domain(url):
                                search_results.append({
                                    "title": title,
                                    "url": url,
                                    "snippet": snippet
                                })
                            else:
                                print(f"Skipping non-US domain: {url}")
                    except Exception as e:
                        print(f"Error extracting search result: {e}")
            
            print(f"Found {len(search_results)} search results")
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
        
        async with AsyncWebCrawler() as crawler:
            # Use parameters supported in version 0.4.247
            result = await crawler.arun(
                url,
                headless=self.headless,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(result.html, 'html.parser')
            
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
            h4_tags = [h4.get_text().strip() for h4 in soup.find_all("h4")]
            h5_tags = [h5.get_text().strip() for h5 in soup.find_all("h5")]
            h6_tags = [h6.get_text().strip() for h6 in soup.find_all("h6")]
            
            # Count heading tags
            h1_count = len(h1_tags)
            h2_count = len(h2_tags)
            h3_count = len(h3_tags)
            h4_count = len(h4_tags)
            h5_count = len(h5_tags)
            h6_count = len(h6_tags)
            
            # Extract links with more details
            internal_links = []
            external_links = []
            base_domain = url.split("//")[-1].split("/")[0]
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("#") or not href or href == "/":
                    continue
                
                link_text = link.get_text().strip()
                
                # Normalize URL
                if href.startswith("/"):
                    full_url = f"{url.split('//')[0]}//{base_domain}{href}"
                    internal_links.append({
                        "url": full_url,
                        "text": link_text,
                        "nofollow": "nofollow" in link.get("rel", "") if link.get("rel") else False
                    })
                elif base_domain in href:
                    internal_links.append({
                        "url": href,
                        "text": link_text,
                        "nofollow": "nofollow" in link.get("rel", "") if link.get("rel") else False
                    })
                elif href.startswith("http"):
                    external_links.append({
                        "url": href,
                        "text": link_text,
                        "nofollow": "nofollow" in link.get("rel", "") if link.get("rel") else False
                    })
            
            # Extract images with more details
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
                    "alt": alt,
                    "has_alt": bool(alt.strip())
                })
            
            # Detect schema markup
            schema_data = []
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    schema_content = script.string
                    if schema_content:
                        schema_data.append(schema_content)
                except Exception as e:
                    print(f"Error parsing schema: {e}")
            
            # Page content analysis
            content_text = soup.get_text()
            word_count = len(content_text.split())
            
            # Keyword analysis
            query = url.split('?q=')[-1].split('&')[0] if '?q=' in url else ''
            query = query.replace('+', ' ')
            
            # If no query in URL, try to extract from title or meta description
            if not query and title:
                # Just use the first few words of the title as a proxy for the main topic
                query = ' '.join(title.split()[:3])
            
            keyword_count = 0
            keyword_density = 0
            
            if query:
                # Count keyword occurrences in content
                keyword_count = content_text.lower().count(query.lower())
                if word_count > 0:
                    keyword_density = (keyword_count / word_count) * 100
            
            # Get markdown content
            try:
                markdown_content = result.markdown
            except AttributeError:
                # If markdown is not available, generate a simple version from the HTML
                markdown_content = content_text[:5000]  # Limit to first 5000 chars
            
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
                "h4_tags": h4_tags,
                "h5_tags": h5_tags,
                "h6_tags": h6_tags,
                "h1_count": h1_count,
                "h2_count": h2_count,
                "h3_count": h3_count,
                "h4_count": h4_count,
                "h5_count": h5_count,
                "h6_count": h6_count,
                "word_count": word_count,
                "internal_links_count": len(internal_links),
                "external_links_count": len(external_links),
                "images_count": len(images),
                "images_with_alt_count": sum(1 for img in images if img["has_alt"]),
                "schema_count": len(schema_data),
                "schema_data": schema_data,
                "keyword": query,
                "keyword_count": keyword_count,
                "keyword_density": keyword_density,
                "content_text": content_text[:5000],  # Limit to first 5000 chars
                "markdown_content": markdown_content,
                "internal_links": internal_links[:20],  # Include more links
                "external_links": external_links[:20],  # Include more links
                "images": images[:20]  # Include more images
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
    
    def make_results_readable(self, serp_analysis):
        """
        Use Gemini API to make the results more readable.
        
        Args:
            serp_analysis (dict): SERP analysis data
            
        Returns:
            dict: SERP analysis with readable content
        """
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
        API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        
        readable_results = []
        for result in serp_analysis["results"]:
            # Extract key information for Gemini to summarize
            content_to_summarize = f"Title: {result.get('title', '')}"
            content_to_summarize += f"\nURL: {result.get('url', '')}"
            content_to_summarize += f"\nSnippet: {result.get('snippet', '')}"
            content_to_summarize += f"\nMeta Description: {result.get('meta_description', '')}"
            
            # Add some of the content text (limited to avoid overwhelming the API)
            content_text = result.get('content_text', '')[:1000] if result.get('content_text') else ''
            content_to_summarize += f"\nContent Preview: {content_text}"
            
            # Prepare the prompt for Gemini
            prompt = f"Rewrite the following webpage information in a clear, readable format. Focus on the main topic and key points. Include the title, URL, and a brief summary of the content:\n\n{content_to_summarize}"
            
            # Call Gemini API
            payload = {
                "contents": [{
                    "parts":[{"text": prompt}]
                }]
            }
            
            try:
                response = requests.post(API_URL, json=payload)
                if response.status_code == 200:
                    api_response = response.json()
                    if 'candidates' in api_response and len(api_response['candidates']) > 0:
                        readable_content = api_response['candidates'][0]['content']['parts'][0]['text']
                        # Update the result with readable content
                        result['readable_content'] = readable_content
                    else:
                        result['readable_content'] = "Could not generate readable content."
                else:
                    result['readable_content'] = f"API Error: {response.status_code}"
            except Exception as e:
                result['readable_content'] = f"Error calling Gemini API: {str(e)}"
            
            readable_results.append(result)
        
        # Update the serp_analysis with readable results
        serp_analysis["results"] = readable_results
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
        
        # Sanitize query for filename
        sanitized_query = "".join(c if c.isalnum() else "_" for c in query)
        
        # Make results more readable using Gemini API
        readable_serp_analysis = self.make_results_readable(serp_analysis)
        
        if output_format == "json":
            # Save full results to JSON (overwrite existing file)
            filename = f"results/serp_{sanitized_query}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(readable_serp_analysis, f, indent=2, ensure_ascii=False)
            
            print(f"Saved JSON results to {filename}")
            return filename
            
        elif output_format == "csv":
            # Create a flattened DataFrame for CSV export
            rows = []
            for result in readable_serp_analysis["results"]:
                row = {
                    "query": query,
                    "position": readable_serp_analysis["results"].index(result) + 1,
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "readable_content": result.get("readable_content", ""),
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
            filename = f"results/serp_{sanitized_query}.csv"
            df.to_csv(filename, index=False, encoding="utf-8")
            
            print(f"Saved CSV results to {filename}")
            return filename
        
        else:
            print(f"Unsupported output format: {output_format}")
            return None


def clean_all_directories():
    """
    Clean all files in both results and analysis directories
    """
    # Clean results directory
    if os.path.exists("results"):
        print("\n===== CLEANING RESULTS DIRECTORY =====")
        print(f"Before cleaning, results directory contains {len(os.listdir('results'))} files")
        for file in os.listdir("results"):
            file_path = os.path.join("results", file)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"Removed file: {file_path}")
                except Exception as e:
                    print(f"Could not remove {file_path}: {e}")
        print(f"After cleaning, results directory contains {len(os.listdir('results'))} files")
    else:
        os.makedirs("results", exist_ok=True)
        print("Created results directory")
    
    # Clean analysis directory
    if os.path.exists("analysis"):
        print("\n===== CLEANING ANALYSIS DIRECTORY =====")
        print(f"Before cleaning, analysis directory contains {len(os.listdir('analysis'))} files")
        for file in os.listdir("analysis"):
            file_path = os.path.join("analysis", file)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"Removed file: {file_path}")
                except Exception as e:
                    print(f"Could not remove {file_path}: {e}")
        print(f"After cleaning, analysis directory contains {len(os.listdir('analysis'))} files")
    else:
        os.makedirs("analysis", exist_ok=True)
        print("Created analysis directory")
    
    print("===== CLEANING COMPLETE =====")

async def main():
    # Initialize the SERP Analyzer
    analyzer = SerpAnalyzer(headless=False)  # Set to True for headless mode
    
    # Get search query from user
    query = input("Enter your search query: ")
    num_results = int(input("Number of results to analyze (default 6): ") or "6")
    
    # Clean ALL files in both directories
    clean_all_directories()
    
    # Perform SERP analysis
    serp_analysis = await analyzer.analyze_serp(query, num_results)
    
    # Save results
    analyzer.save_results(serp_analysis, "json")
    analyzer.save_results(serp_analysis, "csv")
    
    print("\nAnalysis complete!")
    print(f"Analyzed {len(serp_analysis['results'])} search results for query: {query}")


if __name__ == "__main__":
    asyncio.run(main())
