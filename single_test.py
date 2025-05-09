import asyncio
import json
from serp_analyzer import SerpAnalyzer

async def test_single_query():
    print("=== SERP Analyzer Single Query Test ===\n")
    
    # Initialize the analyzer with headless mode
    analyzer = SerpAnalyzer(headless=True)
    
    # Test query - using a more specific technical query
    query = "python async await tutorial examples"
    
    print(f"Testing query: '{query}'")
    
    # Search for the query
    results = await analyzer.search_google(query)
    
    # Print results summary
    print(f"\nFound {len(results)} results for '{query}'")
    
    if results:
        # Print all results with full details
        for i, result in enumerate(results):
            print(f"\n{i+1}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Description: {result.get('description', 'No description')[:150]}..." 
                  if len(result.get('description', '')) > 150 
                  else f"   Description: {result.get('description', 'No description')}")
        
        # Save results to a JSON file
        output_file = f"results_single_test.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved complete results to {output_file}")
    else:
        print("No results found.")

if __name__ == "__main__":
    asyncio.run(test_single_query())
