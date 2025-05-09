import asyncio
import argparse
import sys
import json
import os
import logging
from datetime import datetime
from bypass_serp import BypassSerpAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reliable_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ReliableSearch")

async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Reliable SERP Analyzer - Extract search results without CAPTCHA")
    parser.add_argument("query", nargs="?", help="The search query to analyze")
    parser.add_argument("--results", "-r", type=int, default=6, help="Number of results to return (default: 6)")
    parser.add_argument("--format", "-f", choices=["json", "csv", "text"], default="text", 
                        help="Output format (default: text)")
    parser.add_argument("--output", "-o", help="Output file (default: print to console)")
    
    args = parser.parse_args()
    
    # If no query provided, prompt the user
    if not args.query:
        args.query = input("Enter your search query: ")
    
    # Print banner
    print("\n" + "="*80)
    print(" RELIABLE SERP ANALYZER ".center(80, "="))
    print("="*80 + "\n")
    
    print(f"Searching for: {args.query}")
    print(f"Number of results: {args.results}")
    print(f"Output format: {args.format}")
    print(f"Output destination: {'File: ' + args.output if args.output else 'Console'}")
    print("\nPlease wait, this may take a moment...\n")
    
    try:
        # Initialize the analyzer
        analyzer = BypassSerpAnalyzer()
        
        # Perform the search
        results = await analyzer.analyze_serp(args.query, args.results)
        
        # Check if we got any results
        if not results['results'] or len(results['results']) == 0:
            print("\nNo results found. Trying alternative search methods...")
            
            # Try alternative search methods
            results = await alternative_search(args.query, args.results)
        
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
        
        # Save results to standard location
        save_results(results)
        
        print("\n" + "="*80)
        print(f" SEARCH COMPLETE - FOUND {len(results['results'])} RESULTS ".center(80, "="))
        print("="*80 + "\n")
        
    except KeyboardInterrupt:
        print("\nSearch cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during search: {str(e)}", exc_info=True)
        print(f"\nError during search: {str(e)}")
        print("Please check the log file for more details.")
        sys.exit(1)

async def alternative_search(query, num_results):
    """Try alternative search methods when the primary method fails."""
    logger.info(f"Trying alternative search methods for query: {query}")
    
    # Import alternative search methods if available
    try:
        from improved_serp_analyzer import ImprovedSerpAnalyzer
        logger.info("Using ImprovedSerpAnalyzer as alternative")
        analyzer = ImprovedSerpAnalyzer()
        results = await analyzer.analyze_serp(query, num_results)
        if results['results'] and len(results['results']) > 0:
            logger.info(f"ImprovedSerpAnalyzer found {len(results['results'])} results")
            return results
    except ImportError:
        logger.warning("ImprovedSerpAnalyzer not available")
    
    # Try direct DuckDuckGo search as a last resort
    try:
        logger.info("Using direct DuckDuckGo search as last resort")
        results = await direct_duckduckgo_search(query, num_results)
        return results
    except Exception as e:
        logger.error(f"Error in direct DuckDuckGo search: {str(e)}", exc_info=True)
    
    # Return empty results if all methods fail
    return {"query": query, "results": [], "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

async def direct_duckduckgo_search(query, num_results):
    """Perform a direct search using DuckDuckGo."""
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urlencode
    
    logger.info(f"Performing direct DuckDuckGo search for: {query}")
    
    # Construct the search URL
    params = {
        "q": query,
        "kl": "us-en",  # US English results
        "kp": "-2",     # No safe search
        "kaf": "1"      # Show full content
    }
    
    search_url = f"https://html.duckduckgo.com/html/?{urlencode(params)}"
    
    # Set up headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    # Make the request
    response = requests.get(search_url, headers=headers, timeout=15)
    
    logger.info(f"DuckDuckGo request status code: {response.status_code}")
    
    # Check if the request was successful
    if response.status_code != 200:
        logger.error(f"DuckDuckGo request failed with status code {response.status_code}")
        return {"query": query, "results": []}
    
    # Parse the HTML
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract search results
    results = []
    result_elements = soup.select(".result")
    
    for i, result in enumerate(result_elements):
        if i >= num_results:
            break
        
        # Extract title and URL
        title_element = result.select_one(".result__title")
        if not title_element:
            continue
        
        title = title_element.get_text().strip()
        
        # Extract URL
        url_element = result.select_one(".result__url")
        if not url_element:
            link_element = title_element.select_one("a")
            if not link_element:
                continue
            url = link_element.get("href", "")
        else:
            url = "https://" + url_element.get_text().strip()
        
        # Extract description
        description_element = result.select_one(".result__snippet")
        description = description_element.get_text().strip() if description_element else ""
        
        # Add to results
        results.append({
            "title": title,
            "url": url,
            "description": description,
            "position": i + 1,
            "query": query
        })
    
    # Return the results
    return {
        "query": query,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": results
    }

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

def save_results(results):
    """Save results to standard location."""
    try:
        # Create results directory if it doesn't exist
        os.makedirs("results", exist_ok=True)
        
        # Generate timestamp and safe query string
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query = results["query"]
        safe_query = query.replace(' ', '_')
        
        # Save JSON results
        json_file = f"results/serp_{safe_query}_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved JSON results to {json_file}")
        
        # Save CSV results
        csv_file = f"results/serp_{safe_query}_{timestamp}.csv"
        with open(csv_file, "w", encoding="utf-8") as f:
            # Write header
            f.write("position,title,url,description,query\n")
            
            # Write data
            for result in results["results"]:
                position = result.get("position", "")
                title = result.get("title", "").replace('"', '""')
                url = result.get("url", "")
                description = result.get("description", "").replace('"', '""')
                result_query = result.get("query", "").replace('"', '""')
                
                f.write(f'"{position}","{title}","{url}","{description}","{result_query}"\n')
        
        logger.info(f"Saved CSV results to {csv_file}")
        
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
