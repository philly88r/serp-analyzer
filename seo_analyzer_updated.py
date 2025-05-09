import json
import requests
import argparse
import os
from datetime import datetime
from api_config import GEMINI_API_KEY, GEMINI_API_URL

def analyze_seo_with_gemini(serp_data):
    """
    Use Gemini API to perform a comprehensive SEO analysis of each page in the SERP data.
    
    Args:
        serp_data (dict): The SERP analysis data
        
    Returns:
        dict: The SERP data with added SEO analysis
    """
    # Using API key from api_config
    API_URL = GEMINI_API_URL
    
    print(f"Performing SEO analysis for {len(serp_data['results'])} results...")
    
    for i, result in enumerate(serp_data['results']):
        print(f"Analyzing result {i+1}/{len(serp_data['results'])}: {result['title']}")
        
        # Extract SEO data to analyze
        seo_data = {
            "title": result.get('title', ''),
            "url": result.get('url', ''),
            "meta_description": result.get('meta_description', ''),
            "meta_keywords": result.get('meta_keywords', ''),
            "h1_tags": result.get('h1_tags', []),
            "h2_tags": result.get('h2_tags', []),
            "h3_tags": result.get('h3_tags', []),
            "word_count": result.get('word_count', 0),
            "internal_links_count": result.get('internal_links_count', 0),
            "external_links_count": result.get('external_links_count', 0),
            "images_count": result.get('images_count', 0)
        }
        
        # Extract more detailed SEO data to analyze
        seo_data = {
            "title": result.get('title', ''),
            "url": result.get('url', ''),
            "meta_description": result.get('meta_description', ''),
            "meta_keywords": result.get('meta_keywords', ''),
            "h1_tags": result.get('h1_tags', []),
            "h2_tags": result.get('h2_tags', []),
            "h3_tags": result.get('h3_tags', []),
            "h4_tags": result.get('h4_tags', []),
            "h5_tags": result.get('h5_tags', []),
            "h6_tags": result.get('h6_tags', []),
            "h1_count": result.get('h1_count', 0),
            "h2_count": result.get('h2_count', 0),
            "h3_count": result.get('h3_count', 0),
            "h4_count": result.get('h4_count', 0),
            "h5_count": result.get('h5_count', 0),
            "h6_count": result.get('h6_count', 0),
            "word_count": result.get('word_count', 0),
            "internal_links_count": result.get('internal_links_count', 0),
            "external_links_count": result.get('external_links_count', 0),
            "images_count": result.get('images_count', 0),
            "images_with_alt_count": result.get('images_with_alt_count', 0),
            "schema_count": result.get('schema_count', 0),
            "schema_data": result.get('schema_data', []),
            "keyword": result.get('keyword', ''),
            "keyword_count": result.get('keyword_count', 0),
            "keyword_density": result.get('keyword_density', 0),
            "internal_links": result.get('internal_links', []),
            "external_links": result.get('external_links', [])
        }
        
        # Rest of the function remains the same...
        # (continuing with the existing code)
