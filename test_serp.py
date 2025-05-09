import asyncio
from serp_analyzer import SerpAnalyzer

async def test():
    print("Initializing SerpAnalyzer...")
    analyzer = SerpAnalyzer(headless=True)
    
    print("Searching for 'python programming tutorial'...")
    results = await analyzer.search_google('python programming tutorial')
    
    print(f"\nFound {len(results)} results")
    
    # Print the first 3 results (or all if less than 3)
    for i, result in enumerate(results[:3]):
        print(f"\n{i+1}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Description: {result['description'][:100]}..." if len(result.get('description', '')) > 100 else f"   Description: {result.get('description', '')}")

if __name__ == "__main__":
    asyncio.run(test())
