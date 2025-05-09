#!/usr/bin/env python
import asyncio
import argparse
import json
import sys
import os
from datetime import datetime

# Import the StealthSerpAnalyzer
from stealth_serp import StealthSerpAnalyzer

async def main():
    """
    Command-line interface for the SERP analyzer.
    Run searches from the terminal without keeping a server running.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="SERP Analyzer CLI - Search Google from the command line")
    parser.add_argument("query", help="Search query")
    parser.add_argument("-n", "--num-results", type=int, default=6, help="Number of results to return (default: 6)")
    parser.add_argument("-o", "--output", choices=["json", "csv", "terminal"], default="terminal", 
                        help="Output format (default: terminal)")
    parser.add_argument("-f", "--output-file", help="Output file name (default: auto-generated)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode (default: True)")
    
    args = parser.parse_args()
    
    # Initialize the analyzer
    analyzer = StealthSerpAnalyzer(headless=args.headless)
    
    print(f"Searching for: '{args.query}'")
    print(f"Requesting {args.num_results} results")
    print("Please wait, this may take a few moments...")
    
    # Start time for performance tracking
    start_time = datetime.now()
    
    # Perform the search
    results = await analyzer.search_google(args.query, args.num_results)
    
    # Calculate elapsed time
    elapsed_time = (datetime.now() - start_time).total_seconds()
    
    # Check if we got results
    if not results or len(results) == 0:
        print(f"No results found for query: '{args.query}'")
        return 1
    
    print(f"Found {len(results)} results in {elapsed_time:.2f} seconds")
    
    # Handle output based on format
    if args.output == "terminal":
        # Print results to terminal
        for i, result in enumerate(results):
            print(f"\nRESULT #{i+1}:")
            print(f"TITLE: {result.get('title', 'No title')}")
            print(f"URL: {result.get('url', 'No URL')}")
            print(f"DESCRIPTION: {result.get('description', 'No description')[:150]}")
            print("-" * 80)
    else:
        # Generate output file name if not provided
        if not args.output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_query = args.query.replace(' ', '_')
            args.output_file = f"results/serp_{safe_query}_{timestamp}.{args.output}"
        
        # Create results directory if it doesn't exist
        os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
        
        if args.output == "json":
            # Save as JSON
            with open(args.output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Results saved to {args.output_file}")
        elif args.output == "csv":
            # Save as CSV
            with open(args.output_file, "w", encoding="utf-8") as f:
                # Write header
                f.write("position,title,url,description,query\n")
                
                # Write data
                for result in results:
                    position = result.get("position", "")
                    title = result.get("title", "").replace('"', '""')
                    url = result.get("url", "")
                    description = result.get("description", "").replace('"', '""')
                    result_query = result.get("query", "").replace('"', '""')
                    
                    f.write(f'"{position}","{title}","{url}","{description}","{result_query}"\n')
            print(f"Results saved to {args.output_file}")
    
    return 0

if __name__ == "__main__":
    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
