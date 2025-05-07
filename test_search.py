import asyncio
from serp_analyzer import SerpAnalyzer

async def test_search():
    print("Initializing SerpAnalyzer...")
    analyzer = SerpAnalyzer(headless=True)
    
    query = "coffee"
    print(f"Searching for: {query}")
    
    results = await analyzer.search_google(query, 3)
    
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
