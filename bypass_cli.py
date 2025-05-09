import asyncio
import argparse
import sys
from bypass_serp import BypassSerpAnalyzer
import json

async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="SERP Analyzer CLI - Reliably extract search results")
    parser.add_argument("query", help="The search query to analyze")
    parser.add_argument("--results", "-r", type=int, default=6, help="Number of results to return (default: 6)")
    parser.add_argument("--format", "-f", choices=["json", "csv", "text"], default="text", 
                        help="Output format (default: text)")
    parser.add_argument("--output", "-o", help="Output file (default: print to console)")
    
    args = parser.parse_args()
    
    # Print banner
    print("\n" + "="*80)
    print(" SERP ANALYZER CLI ".center(80, "="))
    print("="*80 + "\n")
    
    print(f"Searching for: {args.query}")
    print(f"Number of results: {args.results}")
    print(f"Output format: {args.format}")
    print(f"Output destination: {'File: ' + args.output if args.output else 'Console'}")
    print("\nPlease wait, this may take a moment...\n")
    
    # Initialize the analyzer
    analyzer = BypassSerpAnalyzer()
    
    # Perform the search
    results = await analyzer.analyze_serp(args.query, args.results)
    
    # Process the results based on the format
    if args.format == "text":
        # Format as text
        output = format_results_as_text(results)
    elif args.format == "json":
        # Format as JSON
        output = json.dumps(results, indent=2)
    elif args.format == "csv":
        # Format as CSV
        output = format_results_as_csv(results)
    
    # Output the results
    if args.output:
        # Write to file
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\nResults saved to {args.output}")
    else:
        # Print to console
        print(output)
    
    print("\n" + "="*80)
    print(" SEARCH COMPLETE ".center(80, "="))
    print("="*80 + "\n")

def format_results_as_text(results):
    """Format the results as readable text."""
    output = []
    output.append(f"Search Query: {results['query']}")
    output.append(f"Timestamp: {results['timestamp']}")
    output.append(f"Total Results: {len(results['results'])}")
    output.append("")
    
    for i, result in enumerate(results['results']):
        output.append(f"Result #{i+1}:")
        output.append(f"Title: {result.get('title', 'N/A')}")
        output.append(f"URL: {result.get('url', 'N/A')}")
        output.append(f"Description: {result.get('description', 'N/A')}")
        output.append("-" * 80)
    
    return "\n".join(output)

def format_results_as_csv(results):
    """Format the results as CSV."""
    output = ["position,title,url,description,query"]
    
    for result in results['results']:
        position = result.get("position", "")
        title = result.get("title", "").replace('"', '""')
        url = result.get("url", "")
        description = result.get("description", "").replace('"', '""')
        query = result.get("query", "").replace('"', '""')
        
        output.append(f'"{position}","{title}","{url}","{description}","{query}"')
    
    return "\n".join(output)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSearch cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)
