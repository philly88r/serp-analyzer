import asyncio
import os
from serp_analyzer import SerpAnalyzer

async def test_basic_search():
    print("=" * 60)
    print("SERP Analyzer Basic Search Test")
    print("=" * 60)
    
    # Set environment variables for testing
    os.environ["PLAYWRIGHT_SKIP_VALIDATION"] = "1"
    
    print("Initializing SerpAnalyzer...")
    analyzer = SerpAnalyzer(headless=True)
    
    # Test basic search functionality
    query = "marketing ai"
    print(f"\nSearching for: {query}")
    
    try:
        results = await analyzer.search_google(query, num_results=3)
        
        print(f"Search completed")
        if results and isinstance(results, list):
            print(f"Found {len(results)} results")
            
            # Display the first result if available
            if results and len(results) > 0:
                first_result = results[0]
                print("\nFirst result:")
                print(f"Title: {first_result.get('title', 'N/A')}")
                print(f"URL: {first_result.get('url', 'N/A')}")
        else:
            print(f"No results found or unexpected result type: {type(results)}")
    except Exception as e:
        print(f"Error during search: {str(e)}")
    
    print("\nTest completed.")

if __name__ == "__main__":
    asyncio.run(test_basic_search())
