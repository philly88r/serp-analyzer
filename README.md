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

## Requirements

- Python 3.8 or higher
- Crawl4AI 0.6.0 or higher
- Pandas for data processing
- Internet connection

## Notes

- The tool may be affected by Google's anti-scraping measures. Using random user agents helps mitigate this.
- For best results, avoid making too many requests in a short period.
- The tool is for educational and research purposes only.
