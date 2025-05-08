import asyncio
import os
import json
from serp_analyzer import SerpAnalyzer

async def simulate_frontend_request(query="marketing ai", num_results=3):
    """
    Simulate a frontend request to the SERP analyzer.
    This mimics how the frontend would call the backend API.
    """
    print("\n" + "="*80)
    print(f"SIMULATING FRONTEND REQUEST FOR: '{query}'")
    print("="*80)
    
    # Initialize the SERP analyzer
    print("Initializing SerpAnalyzer...")
    analyzer = SerpAnalyzer(headless=True)
    
    try:
        # This is what the frontend would call
        print(f"\nPerforming SERP analysis for query: '{query}'")
        serp_analysis = await analyzer.analyze_serp(query, num_results)
        
        # Format the results nicely
        print("\nRESULTS SUMMARY:")
        print(f"Query: {serp_analysis.get('query')}")
        print(f"Success: {serp_analysis.get('success')}")
        print(f"Results count: {len(serp_analysis.get('results', []))}")
        
        # Show details of the first result if available
        if serp_analysis.get('results') and len(serp_analysis.get('results')) > 0:
            first_result = serp_analysis['results'][0]
            print("\nFIRST RESULT DETAILS:")
            print(f"Title: {first_result.get('title', 'N/A')}")
            print(f"URL: {first_result.get('url', 'N/A')}")
            print(f"Success: {first_result.get('success', False)}")
            print(f"Word count: {first_result.get('word_count', 0)}")
            print(f"Internal links: {first_result.get('internal_links_count', 0)}")
            print(f"External links: {first_result.get('external_links_count', 0)}")
            
            # Save the results to a file (as the frontend would)
            output_file = f"results/test_frontend_{query.replace(' ', '_')}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(serp_analysis, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to {output_file}")
        else:
            print("\nNo results found in the analysis.")
    
    except Exception as e:
        print(f"\nERROR: {str(e)}")
    
    print("\nSimulation completed.")

if __name__ == "__main__":
    # Make sure the results directory exists
    os.makedirs("results", exist_ok=True)
    
    # Run the simulation
    asyncio.run(simulate_frontend_request())
