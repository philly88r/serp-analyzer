# SERP Analyzer

A powerful tool for analyzing Google search results using Crawl4AI and Oxylabs integration. This tool fetches the top search results for a query, extracts SEO data, and analyzes page content while bypassing anti-bot measures.

## Features

- Search Google for any query
- Extract top search results (configurable number)
- Visit each result page and analyze:
  - Meta information (title, description, keywords)
  - Heading structure (H1, H2, H3)
  - Internal and external links
  - Images and alt text
  - Word count and content analysis
- Export results in JSON and CSV formats
- Configurable browser and crawler settings

## Installation

1. Install Crawl4AI and dependencies:

```bash
pip install -r requirements.txt
crawl4ai-setup
```

2. Verify the installation:

```bash
crawl4ai-doctor
```

## Usage

Run the SERP analyzer with:

```bash
python serp_analyzer.py
```

You'll be prompted to enter:
- Your search query
- Number of results to analyze (default: 6)

The tool will:
1. Search Google for your query
2. Extract the top results
3. Visit each result page
4. Analyze SEO data and page content
5. Save results to both JSON and CSV files in the `results` directory

## Configuration

The tool uses two configuration files:

- `browser.yml`: Browser settings (viewport, user agent, etc.)
- `crawler.yml`: Crawler settings (timeouts, content extraction, etc.)

You can modify these files to customize the behavior of the SERP analyzer.

## Advanced Usage

For more advanced features, you can modify the `serp_analyzer.py` script to:

- Change the search engine (currently Google)
- Extract additional SEO metrics
- Customize the analysis process
- Modify output formats

## Stealth SERP Analyzer (`stealth_serp_analyzer.py`)

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

Ensure all dependencies are installed by referring to the main [Installation](#installation) section (i.e., run `pip install -r requirements.txt`). The necessary packages (`beautifulsoup4`, `httpx`, `crawl4ai`) are included in `requirements.txt`.

### Usage

To run the stealth SERP analyzer:

```bash
python stealth_serp_analyzer.py
```

The script will:
1.  Iterate through a predefined list of queries (currently "best python ide" and "what is SEO" in the script).
2.  For each query, search DuckDuckGo and retrieve the top 3 results (configurable in the script).
3.  Visit each result page using `crawl4ai`.
4.  Analyze SEO data and page content.
5.  Save the analysis for each query to a separate JSON file in the `results` directory (e.g., `results/stealth_serp_analysis_best_python_ide_YYYYMMDDHHMMSS.json`).
6.  Save debug HTML files for each fetched page (both search results and analyzed pages) into the `debug_pages` directory.

You can modify the `queries` list and `num_results` parameter within the `main()` function in `stealth_serp_analyzer.py` to customize your analysis.

## Requirements

- Python 3.8 or higher
- Crawl4AI 0.6.0 or higher
- Pandas for data processing
- Internet connection

## Notes

- The tool may be affected by Google's anti-scraping measures. Using random user agents helps mitigate this.
- For best results, avoid making too many requests in a short period.
- The tool is for educational and research purposes only.
