import asyncio
from bypass_serp import BypassSerpAnalyzer

async def run_custom_search():
    # Initialize the analyzer
    analyzer = BypassSerpAnalyzer(headless=True)
    
    # Our custom query
    query = "phone mount for car"
    
    print(f"Running search for query: '{query}'")
    
    # Analyze the query
    results = await analyzer.analyze_serp(query, num_results=8)
    
    # Print results summary
    print(f"\nFound {len(results['results'])} results")
    
    # Return the results for further processing
    return results

if __name__ == "__main__":
    results = asyncio.run(run_custom_search())
    
    # Print the path to the saved results file
    print("\nResults saved to:")
    print(f"JSON: results/serp_phone_mount_for_car.json")
