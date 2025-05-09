import asyncio
import json
import os
import sys
import traceback
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote_plus

# Add the current directory to the path so we can import the SerpAnalyzer class
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from serp_analyzer import SerpAnalyzer

async def test_search_with_debugging():
    """
    Test the SERP analyzer with enhanced debugging to identify and fix issues.
    """
    print("\n" + "="*80)
    print(" DEBUG SERP ANALYZER TEST ".center(80, "="))
    print("="*80 + "\n")
    
    # Initialize the analyzer
    analyzer = SerpAnalyzer(headless=True)
    
    # Test query
    query = "python tutorial"
    
    print(f"Testing query: '{query}'")
    
    # Add detailed debugging to the search process
    try:
        # 1. First try direct HTTP request to see what Google returns
        print("\nStep 1: Testing direct HTTP request to Google...")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.google.com/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=10&gl=us&hl=en"
            response = requests.get(search_url, headers=headers, timeout=10)
            
            print(f"Direct HTTP request status code: {response.status_code}")
            print(f"Response length: {len(response.text)} characters")
            
            # Check for CAPTCHA or block
            if "captcha" in response.text.lower() or "unusual traffic" in response.text.lower():
                print("CAPTCHA or block detected in direct HTTP response")
            else:
                print("No CAPTCHA detected in direct HTTP response")
                
                # Save the HTML for analysis
                with open("direct_http_response.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                print("Saved direct HTTP response to direct_http_response.html")
                
                # Try to extract some links
                soup = BeautifulSoup(response.text, "html.parser")
                links = soup.find_all("a")
                print(f"Found {len(links)} links in direct HTTP response")
                
                # Print a few links that look like search results
                result_links = []
                for link in links:
                    href = link.get("href", "")
                    if href.startswith("http") and "google" not in href.lower():
                        result_links.append(href)
                
                print(f"Found {len(result_links)} potential result links")
                for i, link in enumerate(result_links[:5]):
                    print(f"  {i+1}. {link}")
        
        except Exception as e:
            print(f"Error in direct HTTP request: {str(e)}")
            traceback.print_exc()
        
        # 2. Test the search_google method with detailed logging
        print("\nStep 2: Testing search_google method...")
        
        # Patch the SerpAnalyzer class to add more debugging
        original_direct_search = analyzer._direct_search_google
        original_process_html = analyzer._process_google_html
        
        # Override the _direct_search_google method to add more debugging
        async def debug_direct_search(self, query, search_url, num_results=6):
            print(f"DEBUG: Entering _direct_search_google with query: {query}")
            print(f"DEBUG: Search URL: {search_url}")
            
            try:
                results = await original_direct_search(query, search_url, num_results)
                print(f"DEBUG: _direct_search_google returned: {results}")
                print(f"DEBUG: Results type: {type(results)}")
                print(f"DEBUG: Results count: {len(results) if results else 0}")
                return results
            except Exception as e:
                print(f"DEBUG: Exception in _direct_search_google: {str(e)}")
                traceback.print_exc()
                return []
        
        # Override the _process_google_html method to add more debugging
        async def debug_process_html(self, html, query, num_results=6):
            print(f"DEBUG: Entering _process_google_html")
            print(f"DEBUG: HTML length: {len(html) if html else 0}")
            
            if html:
                # Save the HTML for analysis
                with open("debug_html_content.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print("DEBUG: Saved HTML to debug_html_content.html")
                
                # Check for CAPTCHA or block
                if "captcha" in html.lower() or "unusual traffic" in html.lower():
                    print("DEBUG: CAPTCHA or block detected in HTML")
                else:
                    print("DEBUG: No CAPTCHA detected in HTML")
            
            try:
                results = await original_process_html(html, query, num_results)
                print(f"DEBUG: _process_google_html returned: {results}")
                print(f"DEBUG: Results type: {type(results)}")
                print(f"DEBUG: Results count: {len(results) if results else 0}")
                return results
            except Exception as e:
                print(f"DEBUG: Exception in _process_google_html: {str(e)}")
                traceback.print_exc()
                return []
        
        # Apply the patches
        analyzer._direct_search_google = debug_direct_search.__get__(analyzer, SerpAnalyzer)
        analyzer._process_google_html = debug_process_html.__get__(analyzer, SerpAnalyzer)
        
        # Now run the search
        results = await analyzer.search_google(query)
        
        # Print results summary
        print("\n" + "="*80)
        print(f" FOUND {len(results) if results else 0} RESULTS ".center(80, "="))
        print("="*80 + "\n")
        
        if results and len(results) > 0:
            # Print each result with clear separation
            for i, result in enumerate(results):
                print(f"RESULT #{i+1}:")
                print(f"TITLE: {result.get('title', 'No title')}")
                print(f"URL: {result.get('url', 'No URL')}")
                print(f"DESCRIPTION: {result.get('description', 'No description')[:150]}")
                print("-"*80)
            
            # Save results to a JSON file with clear formatting
            output_file = "debug_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\nSaved complete results to {output_file}")
        else:
            print("NO RESULTS FOUND.")
            print("Please check the logs for any errors.")
        
        # 3. Try an alternative approach using a simple parser
        print("\nStep 3: Testing alternative HTML parsing approach...")
        
        # Load the saved HTML if it exists
        html_file = "debug_html_content.html"
        if os.path.exists(html_file):
            try:
                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()
                
                print(f"Loaded HTML from {html_file}, length: {len(html_content)} characters")
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(html_content, "html.parser")
                
                # Try to extract search results
                print("Attempting to extract search results with alternative method...")
                
                # Method 1: Look for all links
                links = soup.find_all("a")
                print(f"Found {len(links)} links in HTML")
                
                # Filter links that look like search results
                result_links = []
                for link in links:
                    href = link.get("href", "")
                    if href.startswith("http") and "google" not in href.lower():
                        title = link.get_text().strip()
                        result_links.append({
                            "url": href,
                            "title": title if title else "No title"
                        })
                
                print(f"Found {len(result_links)} potential result links")
                
                # Print the first 5 result links
                for i, result in enumerate(result_links[:5]):
                    print(f"  {i+1}. {result['title'][:50]}... -> {result['url']}")
                
                # Save the results
                with open("alternative_results.json", "w", encoding="utf-8") as f:
                    json.dump(result_links, f, indent=2, ensure_ascii=False)
                print("Saved alternative results to alternative_results.json")
                
            except Exception as e:
                print(f"Error in alternative parsing: {str(e)}")
                traceback.print_exc()
        else:
            print(f"HTML file {html_file} not found, skipping alternative parsing")
    
    except Exception as e:
        print(f"Overall error in test: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search_with_debugging())
