import asyncio
from crawl4ai import AsyncWebCrawler

async def debug_crawl4ai():
    print("Testing Crawl4AI directly...")
    
    # Create a simple crawler
    browser_options = {
        "url": "https://www.google.com/search?q=coffee&gl=us&hl=en",
        "headless": True,
        "cache_mode": "bypass",
        "wait_for_elements": True,
        "magic": True
    }
    
    try:
        async with AsyncWebCrawler() as crawler:
            print("Running crawler...")
            result = await crawler.arun(**browser_options)
            
            # Print all available attributes and methods
            print("\nResult object attributes:")
            for attr in dir(result):
                if not attr.startswith('_'):
                    print(f"- {attr}")
                    
            # Try to access common attributes
            print("\nTrying to access common attributes:")
            if hasattr(result, 'html'):
                print(f"HTML content length: {len(result.html)}")
            else:
                print("No 'html' attribute found")
                
            if hasattr(result, 'text'):
                print(f"Text content length: {len(result.text)}")
            else:
                print("No 'text' attribute found")
                
            if hasattr(result, 'success'):
                print(f"Success: {result.success}")
            else:
                print("No 'success' attribute found")
                
            # Try to parse HTML with BeautifulSoup
            from bs4 import BeautifulSoup
            if hasattr(result, 'html'):
                soup = BeautifulSoup(result.html, 'html.parser')
                print(f"\nParsed HTML with BeautifulSoup")
                
                # Try to find search results
                result_elements = soup.select("div.g")
                print(f"Found {len(result_elements)} search result elements with div.g selector")
                
                # Try alternative selectors if the standard one doesn't work
                if len(result_elements) == 0:
                    print("Trying alternative selectors...")
                    selectors = [
                        "div.tF2Cxc", 
                        "div.yuRUbf", 
                        "div[data-sokoban-container]",
                        "div.rc",
                        "div.g div.rc",
                        "div.g h3"
                    ]
                    
                    for selector in selectors:
                        elements = soup.select(selector)
                        print(f"Selector '{selector}': {len(elements)} elements")
                
    except Exception as e:
        print(f"Error during crawl: {str(e)}")

if __name__ == "__main__":
    asyncio.run(debug_crawl4ai())
