## Stealth SERP Analyzer ([stealth_serp_analyzer.py](cci:7://file:///c:/Users/info/serp_analyzer/stealth_serp_analyzer.py:0:0-0:0))

This script provides an alternative SERP analysis focused on stealth and reliability by primarily using DuckDuckGo (via its HTML interface) for search queries and `crawl4ai` for fetching and analyzing page content. It's designed to be less prone to blocks and CAPTCHAs for initial search result gathering.

### Features:

-   Searches DuckDuckGo for a given query.
-   Fetches and analyzes a configurable number of top search results.
-   Extracts detailed SEO information from each page:
    -   Title, Meta Description, Meta Keywords
    -   H1, H2, H3 tags
    -   Internal and External links
    -   Image URLs and Alt texts
    -   Word count and a sample of the page content
    -   Markdown preview of the page (if `crawl4ai` successfully generates it)
-   Uses `crawl4ai` with stealth features for fetching individual pages.
-   Includes configurable delays between requests to minimize detection.
-   Saves detailed analysis results in JSON format per query.
-   Saves HTML content of fetched pages for debugging purposes in the `debug_pages` directory.

### Setup

Ensure all dependencies are installed by referring to the main [Installation](#installation) section (i.e., run `pip install -r requirements.txt`). The necessary packages (`beautifulsoup4`, `httpx`, `crawl4ai`) are included in [requirements.txt](cci:7://file:///c:/Users/info/serp_analyzer/requirements.txt:0:0-0:0).

### Usage

To run the stealth SERP analyzer:

```bash
python stealth_serp_analyzer.py