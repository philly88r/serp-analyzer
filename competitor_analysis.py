import logging
import asyncio
from urllib.parse import urlparse
from collections import Counter
import re
import json
from database import save_competitor_analysis
from ai_recommendations import generate_competitor_gap_analysis

# Set up logging
logger = logging.getLogger(__name__)

class CompetitorAnalyzer:
    """Analyzes competitors in search results and compares against target URL."""
    
    def __init__(self, serp_analyzer):
        """Initialize with a reference to the main SERP analyzer."""
        self.serp_analyzer = serp_analyzer
    
    async def identify_competitors(self, query, target_url, search_results=None):
        """Identify competitors for a given query and target URL."""
        try:
            # If search results not provided, get them
            if not search_results:
                search_results = await self.serp_analyzer.search_google(query)
            
            # Parse target domain
            target_domain = self._extract_domain(target_url)
            
            # Filter out the target domain and identify competitors
            competitors = []
            for result in search_results:
                result_url = result.get('url', '')
                result_domain = self._extract_domain(result_url)
                
                # Skip if this is the target domain
                if result_domain == target_domain:
                    continue
                
                # Add to competitors list
                competitors.append({
                    'position': result.get('position', 0),
                    'title': result.get('title', ''),
                    'url': result_url,
                    'domain': result_domain,
                    'description': result.get('description', '')
                })
            
            logger.info(f"Identified {len(competitors)} competitors for query: {query}")
            return competitors
        
        except Exception as e:
            logger.error(f"Error identifying competitors: {str(e)}")
            return []
    
    async def analyze_competitor(self, competitor_url):
        """Analyze a competitor's page."""
        try:
            # Use the main analyzer to get page data
            competitor_data = await self.serp_analyzer.analyze_page(competitor_url, None)
            return competitor_data
        except Exception as e:
            logger.error(f"Error analyzing competitor {competitor_url}: {str(e)}")
            return None
    
    async def compare_with_competitors(self, query, target_url, target_data=None, top_n=3):
        """Compare target URL with top competitors."""
        try:
            # Get search results
            search_results = await self.serp_analyzer.search_google(query)
            
            # Identify competitors
            competitors = await self.identify_competitors(query, target_url, search_results)
            
            # Limit to top N competitors
            top_competitors = competitors[:top_n]
            
            # If target data not provided, analyze target URL
            if not target_data:
                target_data = await self.serp_analyzer.analyze_page(target_url, None)
            
            # Analyze each competitor
            comparison_results = []
            for competitor in top_competitors:
                competitor_url = competitor['url']
                competitor_data = await self.analyze_competitor(competitor_url)
                
                if competitor_data:
                    # Generate gap analysis
                    gap_analysis = generate_competitor_gap_analysis(target_data, competitor_data)
                    
                    if gap_analysis:
                        # Save to database
                        query_id = getattr(self.serp_analyzer, 'current_query_id', None)
                        save_competitor_analysis(
                            query_id=query_id,
                            target_url=target_url,
                            competitor_url=competitor_url,
                            analysis_data=gap_analysis
                        )
                        
                        # Add to results
                        comparison_results.append({
                            'competitor': competitor,
                            'gap_analysis': gap_analysis
                        })
            
            logger.info(f"Completed comparison with {len(comparison_results)} competitors")
            return comparison_results
        
        except Exception as e:
            logger.error(f"Error comparing with competitors: {str(e)}")
            return []
    
    def _extract_domain(self, url):
        """Extract domain from URL."""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Remove www. if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain
        except Exception:
            return url
    
    def _extract_keywords(self, text, min_length=4, max_length=30):
        """Extract keywords from text."""
        if not text:
            return []
        
        # Remove special characters and convert to lowercase
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into words
        words = text.split()
        
        # Filter out short words and common stop words
        stop_words = {
            'the', 'and', 'is', 'in', 'to', 'of', 'for', 'on', 'with', 'as',
            'at', 'by', 'an', 'be', 'this', 'that', 'it', 'or', 'are', 'from',
            'was', 'were', 'will', 'would', 'could', 'should', 'have', 'has',
            'had', 'not', 'what', 'when', 'where', 'who', 'how', 'why', 'which'
        }
        
        keywords = [word for word in words if len(word) >= min_length and word not in stop_words]
        
        # Count keyword frequency
        keyword_counts = Counter(keywords)
        
        # Return most common keywords
        return keyword_counts.most_common(max_length)
    
    async def analyze_serp_features(self, query):
        """Analyze SERP features for a query."""
        try:
            # Get search results
            search_results = await self.serp_analyzer.search_google(query)
            
            # Extract domains
            domains = [self._extract_domain(result.get('url', '')) for result in search_results]
            domain_counts = Counter(domains)
            
            # Count domain frequency
            domain_distribution = {
                domain: count for domain, count in domain_counts.items() if count > 0
            }
            
            # Extract keywords from titles and descriptions
            all_titles = ' '.join([result.get('title', '') for result in search_results])
            all_descriptions = ' '.join([result.get('description', '') for result in search_results])
            
            title_keywords = self._extract_keywords(all_titles)
            description_keywords = self._extract_keywords(all_descriptions)
            
            return {
                'query': query,
                'results_count': len(search_results),
                'domain_distribution': domain_distribution,
                'title_keywords': title_keywords,
                'description_keywords': description_keywords
            }
        
        except Exception as e:
            logger.error(f"Error analyzing SERP features: {str(e)}")
            return None
    
    async def bulk_competitor_analysis(self, queries, target_url):
        """Perform competitor analysis for multiple queries."""
        results = []
        for query in queries:
            try:
                logger.info(f"Analyzing competitors for query: {query}")
                comparison = await self.compare_with_competitors(query, target_url)
                results.append({
                    'query': query,
                    'comparisons': comparison
                })
            except Exception as e:
                logger.error(f"Error in bulk competitor analysis for query '{query}': {str(e)}")
        
        return results
