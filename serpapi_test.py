import asyncio
import json
import os
import random
import time
from urllib.parse import quote_plus
import aiohttp
import sys

# Add the current directory to the path so we can import the SerpAnalyzer class
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from serp_analyzer import SerpAnalyzer

class SerpApiExtractor:
    """
    A class to extract search results using SerpAPI as a reliable alternative
    when Google's anti-bot measures are too aggressive.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the SerpAPI extractor with an optional API key.
        If no API key is provided, it will use a demo search.
        """
        self.api_key = api_key or "demo"
        self.base_url = "https://serpapi.com/search"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0"
        ]
    
    async def search(self, query, num_results=10):
        """
        Perform a search using SerpAPI and return the results.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to return
            
        Returns:
            list: A list of search result dictionaries
        """
        print(f"Searching for '{query}' using SerpAPI...")
        
        # Build the query parameters
        params = {
            "q": query,
            "num": num_results,
            "api_key": self.api_key,
            "engine": "google",
            "google_domain": "google.com",
            "gl": "us",  # Country to use for the search
            "hl": "en",  # Language
            "device": "desktop",
            "output": "json"
        }
        
        # Add a random user agent
        headers = {
            "User-Agent": random.choice(self.user_agents)
        }
        
        try:
            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, headers=headers) as response:
                    if response.status != 200:
                        print(f"Error: SerpAPI returned status code {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    # Save the raw response for debugging
                    with open("serpapi_response.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                    
                    # Extract organic results
                    results = []
                    
                    if "organic_results" in data:
                        for i, result in enumerate(data["organic_results"][:num_results]):
                            results.append({
                                "position": i + 1,
                                "title": result.get("title", ""),
                                "url": result.get("link", ""),
                                "description": result.get("snippet", ""),
                                "query": query
                            })
                    
                    print(f"Found {len(results)} results using SerpAPI")
                    return results
        
        except Exception as e:
            print(f"Error searching with SerpAPI: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

class EnhancedSerpAnalyzer(SerpAnalyzer):
    """
    Enhanced version of SerpAnalyzer that uses SerpAPI as a fallback
    when direct Google searches fail due to anti-bot measures.
    """
    
    def __init__(self, headless=True, api_key=None):
        """
        Initialize the enhanced SERP analyzer.
        
        Args:
            headless (bool): Whether to run the browser in headless mode
            api_key (str): Optional SerpAPI key
        """
        super().__init__(headless=headless)
        self.serpapi = SerpApiExtractor(api_key)
    
    async def search_google(self, query, num_results=6):
        """
        Search Google with enhanced fallback mechanisms.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to return
            
        Returns:
            list: A list of search result dictionaries
        """
        print(f"Enhanced search for '{query}'")
        
        # First try the standard search method
        results = await super().search_google(query, num_results)
        
        # If we got results, return them
        if results and len(results) > 0:
            print(f"Standard search returned {len(results)} results")
            return results
        
        # If standard search failed, try SerpAPI
        print("Standard search failed. Trying SerpAPI as fallback...")
        results = await self.serpapi.search(query, num_results)
        
        return results

async def test_enhanced_analyzer():
    """Test the enhanced SERP analyzer with a sample query."""
    print("\n" + "="*80)
    print(" ENHANCED SERP ANALYZER TEST ".center(80, "="))
    print("="*80 + "\n")
    
    # Initialize the enhanced analyzer
    analyzer = EnhancedSerpAnalyzer(headless=True)
    
    # Test query
    query = "python web scraping tutorial"
    
    print(f"Testing query: '{query}'")
    
    # Search for the query
    results = await analyzer.search_google(query)
    
    # Print results summary
    print("\n" + "="*80)
    print(f" FOUND {len(results)} RESULTS ".center(80, "="))
    print("="*80 + "\n")
    
    if results:
        # Print each result with clear separation
        for i, result in enumerate(results):
            print(f"RESULT #{i+1}:")
            print(f"TITLE: {result.get('title', 'No title')}")
            print(f"URL: {result.get('url', 'No URL')}")
            print(f"DESCRIPTION: {result.get('description', 'No description')[:150]}")
            print("-"*80)
        
        # Save results to a JSON file with clear formatting
        output_file = "enhanced_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved complete results to {output_file}")
    else:
        print("NO RESULTS FOUND.")
        print("Please check the logs for any errors.")

if __name__ == "__main__":
    asyncio.run(test_enhanced_analyzer())
