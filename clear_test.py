import asyncio
import json
from serp_analyzer import SerpAnalyzer

async def test_with_clear_output():
    print("\n" + "="*80)
    print("SERP ANALYZER TEST WITH CLEAR OUTPUT")
    print("="*80 + "\n")
    
    # Initialize the analyzer with headless mode
    analyzer = SerpAnalyzer(headless=True)
    
    # Test query
    query = "python web scraping tutorial"
    
    print(f"SEARCHING FOR: '{query}'\n")
    
    # Search for the query
    results = await analyzer.search_google(query)
    
    # Print results count
    print("\n" + "="*80)
    print(f"FOUND {len(results)} RESULTS")
    print("="*80 + "\n")
    
    if results:
        # Print each result with clear separation
        for i, result in enumerate(results):
            print(f"RESULT #{i+1}:")
            print(f"TITLE: {result.get('title', 'No title')}")
            print(f"URL: {result.get('url', 'No URL')}")
            print(f"DESCRIPTION: {result.get('description', 'No description')[:200]}")
            print("-"*80)
        
        # Save results to a JSON file with clear formatting
        output_file = "clear_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved complete results to {output_file}")
    else:
        print("NO RESULTS FOUND.")
        print("Please check the logs for any errors.")

if __name__ == "__main__":
    asyncio.run(test_with_clear_output())
