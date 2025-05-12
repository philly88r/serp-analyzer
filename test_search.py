import asyncio
import os
import time
from bypass_serp import BypassSerpAnalyzer

async def test_search():
    print("Initializing BypassSerpAnalyzer...")
    analyzer = BypassSerpAnalyzer(headless=True)
    
    # Create debug directory if it doesn't exist
    os.makedirs("debug", exist_ok=True)
    
    # Try a query that might trigger CAPTCHA
    query = "best coffee shops in new york"
    print(f"Searching for: {query}")
    
    # Run the search
    results = await analyzer.search_google(query, 6)
    
    if results is None:
        print("Search returned None instead of a list")
        results = []
    
    print(f"Found {len(results)} results")
    if results:
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"Title: {result.get('title', 'N/A')}")
            print(f"URL: {result.get('url', 'N/A')}")
            print(f"Snippet: {result.get('snippet', 'N/A')[:100] if result.get('snippet') else 'N/A'}...")
    else:
        print("No results found. Check the error messages above.")

if __name__ == "__main__":
    asyncio.run(test_search())
