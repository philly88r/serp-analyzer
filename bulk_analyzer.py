import os
import csv
import json
import logging
import asyncio
import time
from datetime import datetime
from database import save_search_query, save_search_results

# Set up logging
logger = logging.getLogger(__name__)

class BulkAnalyzer:
    """Handles bulk analysis of multiple queries and URLs."""
    
    def __init__(self, serp_analyzer):
        """Initialize with a reference to the main SERP analyzer."""
        self.serp_analyzer = serp_analyzer
        self.results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
        os.makedirs(self.results_dir, exist_ok=True)
    
    async def analyze_queries(self, queries, max_concurrent=3, save_to_file=True):
        """Analyze multiple search queries."""
        results = []
        start_time = time.time()
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(query):
            async with semaphore:
                logger.info(f"Analyzing query: {query}")
                try:
                    # Save query to database
                    query_id = save_search_query(query)
                    
                    # Search and analyze
                    search_results = await self.serp_analyzer.search_google(query)
                    
                    # Save results to database
                    save_search_results(query_id, search_results)
                    
                    # Add to results
                    return {
                        'query': query,
                        'query_id': query_id,
                        'results': search_results,
                        'timestamp': datetime.now().isoformat()
                    }
                except Exception as e:
                    logger.error(f"Error analyzing query '{query}': {str(e)}")
                    return {
                        'query': query,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
        
        # Create tasks for all queries
        tasks = [analyze_with_semaphore(query) for query in queries]
        
        # Wait for all tasks to complete
        for completed_task in asyncio.as_completed(tasks):
            result = await completed_task
            if result:
                results.append(result)
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"Completed bulk analysis of {len(queries)} queries in {duration:.2f} seconds")
        
        # Save results to file if requested
        if save_to_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.results_dir, f"bulk_query_results_{timestamp}.json")
            
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Saved bulk analysis results to {filename}")
        
        return results
    
    async def analyze_urls(self, urls, max_concurrent=3, save_to_file=True):
        """Analyze multiple URLs."""
        results = []
        start_time = time.time()
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(url):
            async with semaphore:
                logger.info(f"Analyzing URL: {url}")
                try:
                    # Analyze page
                    page_data = await self.serp_analyzer.analyze_page(url, None)
                    
                    # Add to results
                    return {
                        'url': url,
                        'analysis': page_data,
                        'timestamp': datetime.now().isoformat()
                    }
                except Exception as e:
                    logger.error(f"Error analyzing URL '{url}': {str(e)}")
                    return {
                        'url': url,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
        
        # Create tasks for all URLs
        tasks = [analyze_with_semaphore(url) for url in urls]
        
        # Wait for all tasks to complete
        for completed_task in asyncio.as_completed(tasks):
            result = await completed_task
            if result:
                results.append(result)
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"Completed bulk analysis of {len(urls)} URLs in {duration:.2f} seconds")
        
        # Save results to file if requested
        if save_to_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.results_dir, f"bulk_url_results_{timestamp}.json")
            
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Saved bulk analysis results to {filename}")
        
        return results
    
    def load_queries_from_csv(self, csv_file):
        """Load queries from a CSV file."""
        queries = []
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        queries.append(row[0].strip())
            
            logger.info(f"Loaded {len(queries)} queries from {csv_file}")
            return queries
        except Exception as e:
            logger.error(f"Error loading queries from CSV: {str(e)}")
            return []
    
    def load_urls_from_csv(self, csv_file):
        """Load URLs from a CSV file."""
        urls = []
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        urls.append(row[0].strip())
            
            logger.info(f"Loaded {len(urls)} URLs from {csv_file}")
            return urls
        except Exception as e:
            logger.error(f"Error loading URLs from CSV: {str(e)}")
            return []
    
    def export_results_to_csv(self, results, csv_file):
        """Export analysis results to a CSV file."""
        try:
            # Determine if these are query results or URL results
            is_query_results = 'query' in results[0] if results else False
            
            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                if is_query_results:
                    # Export query results
                    fieldnames = ['query', 'position', 'title', 'url', 'description']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for result in results:
                        query = result.get('query', '')
                        for search_result in result.get('results', []):
                            writer.writerow({
                                'query': query,
                                'position': search_result.get('position', ''),
                                'title': search_result.get('title', ''),
                                'url': search_result.get('url', ''),
                                'description': search_result.get('description', '')
                            })
                else:
                    # Export URL results
                    fieldnames = [
                        'url', 'word_count', 'title_length', 'meta_description_length',
                        'h1_count', 'h2_count', 'h3_count', 'internal_links_count',
                        'external_links_count', 'images_count', 'images_with_alt_count',
                        'page_size_kb', 'load_time_ms', 'has_schema_markup'
                    ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for result in results:
                        analysis = result.get('analysis', {})
                        writer.writerow({
                            'url': result.get('url', ''),
                            'word_count': analysis.get('content', {}).get('word_count', ''),
                            'title_length': len(analysis.get('title', '')),
                            'meta_description_length': len(analysis.get('description', '')),
                            'h1_count': len(analysis.get('headings', {}).get('h1', [])),
                            'h2_count': len(analysis.get('headings', {}).get('h2', [])),
                            'h3_count': len(analysis.get('headings', {}).get('h3', [])),
                            'internal_links_count': analysis.get('links', {}).get('internal', 0),
                            'external_links_count': analysis.get('links', {}).get('external', 0),
                            'images_count': analysis.get('images', {}).get('total', 0),
                            'images_with_alt_count': analysis.get('images', {}).get('with_alt', 0),
                            'page_size_kb': analysis.get('technical', {}).get('page_size_kb', 0),
                            'load_time_ms': analysis.get('technical', {}).get('load_time_ms', 0),
                            'has_schema_markup': analysis.get('schema_markup', {}).get('has_schema', False)
                        })
            
            logger.info(f"Exported results to {csv_file}")
            return True
        except Exception as e:
            logger.error(f"Error exporting results to CSV: {str(e)}")
            return False
