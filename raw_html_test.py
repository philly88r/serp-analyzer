import asyncio
from crawl4ai import AsyncWebCrawler
import os

async def get_raw_html():
    print("=== Raw HTML Test ===")
    
    # Search query
    query = "python tutorial"
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&gl=us&hl=en&cr=countryUS&pws=0"
    
    print(f"Fetching raw HTML for: {search_url}")
    
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                search_url,
                headless=True,
                cache_mode="bypass",
                wait_until="networkidle",
                page_timeout=15000,
                delay_before_return_html=1.0,
                word_count_threshold=100,
                scan_full_page=True,
                scroll_delay=0.5,
                remove_overlay_elements=True
            )
            
            if result.success:
                html_content = result.html
                print(f"Successfully retrieved HTML content (length: {len(html_content)})")
                
                # Save the HTML to a file
                with open("raw_google_html.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"Saved raw HTML to raw_google_html.html")
                
                # Check for some common patterns in Google search results
                patterns = [
                    'div.g', 'div.tF2Cxc', 'div.yuRUbf', 'div.rc', 
                    'h3', 'a.sVXRqc', 'div.MjjYud', 'div.Gx5Zad'
                ]
                
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                print("\nChecking for common Google result patterns:")
                for pattern in patterns:
                    elements = soup.select(pattern)
                    print(f"Pattern '{pattern}': {len(elements)} elements found")
                
                # Extract all links
                all_links = soup.find_all('a')
                print(f"\nFound {len(all_links)} links in total")
                
                # Filter links that look like search results
                result_links = []
                for link in all_links:
                    href = link.get('href', '')
                    if href.startswith('http') and 'google' not in href.lower():
                        result_links.append({
                            'text': link.get_text().strip(),
                            'href': href
                        })
                
                print(f"Found {len(result_links)} potential result links")
                
                # Print the first 5 result links
                print("\nFirst 5 potential result links:")
                for i, link in enumerate(result_links[:5]):
                    print(f"{i+1}. {link['text'][:50]}... -> {link['href']}")
                
                # Save the extracted links to a file
                import json
                with open("extracted_links.json", "w", encoding="utf-8") as f:
                    json.dump(result_links, f, indent=2, ensure_ascii=False)
                print(f"Saved extracted links to extracted_links.json")
                
            else:
                print(f"Error fetching HTML: {result.error_message}")
    except Exception as e:
        print(f"Exception during crawling: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(get_raw_html())
