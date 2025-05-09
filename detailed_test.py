import asyncio
import json
from serp_analyzer import SerpAnalyzer

async def test_serp_analyzer():
    print("=== SERP Analyzer Test with Enhanced Anti-Bot Detection ===\n")
    
    # Initialize the analyzer with headless mode
    analyzer = SerpAnalyzer(headless=True)
    
    # Test queries
    test_queries = [
        "python programming tutorial",
        "machine learning basics",
        "web development frameworks"
    ]
    
    # Run tests for each query
    for query in test_queries:
        print(f"\n\n=== Testing query: '{query}' ===\n")
        
        # Search for the query
        results = await analyzer.search_google(query)
        
        # Print results summary
        print(f"\nFound {len(results)} results for '{query}'")
        
        if results:
            # Print the first 3 results (or all if less than 3)
            for i, result in enumerate(results[:3]):
                print(f"\n{i+1}. {result['title']}")
                print(f"   URL: {result['url']}")
                print(f"   Description: {result['description'][:100]}..." if len(result.get('description', '')) > 100 else f"   Description: {result.get('description', '')}")
            
            # Save results to a JSON file
            output_file = f"results_{query.replace(' ', '_')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\nSaved complete results to {output_file}")
        else:
            print("No results found.")

if __name__ == "__main__":
    asyncio.run(test_serp_analyzer())
