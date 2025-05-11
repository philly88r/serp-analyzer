#!/usr/bin/env python
import os
import json
import re
import argparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import csv
import random
import markdown
from api_config import GEMINI_API_KEY, GEMINI_FLASH_API_URL

def load_seo_analysis(json_file):
    """Load SEO analysis data from JSON file"""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_seo_insights(seo_data, html_dir=None):
    """Extract key SEO insights from analysis data"""
    query = seo_data.get('query', '')
    results = seo_data.get('results', [])
    
    # Extract competitor information
    competitors = []
    all_unique_facts = []
    
    for i, result in enumerate(results[:6]):
        # Initialize competitor data
        competitor_data = {
            'position': i + 1,
            'name': result.get('title', '').split(' - ')[0].strip(),
            'url': result.get('url', ''),
            'title': result.get('title', ''),
            'meta_description': result.get('meta_description', ''),
            'word_count': result.get('word_count', 0),
            'h1_count': result.get('h1_count', 0),
            'h2_count': result.get('h2_count', 0),
            'h3_count': result.get('h3_count', 0),
            'internal_links_count': result.get('internal_links_count', 0),
            'external_links_count': result.get('external_links_count', 0),
            'images_count': result.get('images_count', 0),
            'schema_count': result.get('schema_count', 0),
            'keyword_density': result.get('keyword_density', 0),
            'unique_features': extract_unique_features(result)
        }
        
        # Try to extract facts from HTML content if available
        if html_dir and os.path.exists(html_dir):
            html_file = os.path.join(html_dir, f'page_{i+1}.json')
            if os.path.exists(html_file):
                try:
                    with open(html_file, 'r', encoding='utf-8') as f:
                        page_data = json.load(f)
                    
                    # Extract facts from page content
                    facts = extract_facts_from_page(page_data, query)
                    competitor_data['unique_facts'] = facts
                    all_unique_facts.extend(facts)
                    print(f"Extracted {len(facts)} facts from {result.get('url')}")
                except Exception as e:
                    print(f"Error extracting facts from {html_file}: {str(e)}")
        
        competitors.append(competitor_data)
    
    # Extract keyword information
    keywords = {
        'primary': query,
        'singular': query.rstrip('s'),
        'related': extract_related_keywords(seo_data)
    }
    
    return {
        'query': query,
        'competitors': competitors,
        'keywords': keywords,
        'target_metrics': calculate_target_metrics(competitors),
        'all_unique_facts': all_unique_facts
    }

def extract_facts_from_page(page_data, query):
    """Extract factual information from page content using AI"""
    try:
        # Check if Gemini API key is available
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        if not gemini_api_key:
            print("Warning: GEMINI_API_KEY not found in environment variables. Falling back to rule-based extraction.")
            return extract_facts_rule_based(page_data, query)
        
        # Prepare content for AI processing
        content = ""
        
        # Add title and description
        if 'title' in page_data:
            content += f"Title: {page_data['title']}\n\n"
        if 'description' in page_data:
            content += f"Description: {page_data['description']}\n\n"
        
        # Add headings
        if 'headings' in page_data:
            content += "Headings:\n"
            for heading_type in ['h1', 'h2', 'h3']:
                if heading_type in page_data['headings']:
                    for heading in page_data['headings'][heading_type][:5]:  # Limit to 5 headings per type
                        content += f"{heading_type.upper()}: {heading}\n"
            content += "\n"
        
        # Add main content
        if 'content' in page_data and 'sample' in page_data['content']:
            content += f"Content Sample:\n{page_data['content']['sample']}\n\n"
        
        # Prepare the prompt for Gemini
        prompt = f"""Extract factual information from the following webpage content related to the query: '{query}'.
        
        WEBPAGE CONTENT:
        {content}
        
        INSTRUCTIONS:
        1. Extract 5-10 specific, factual statements from the content.
        2. Focus on information that would be useful for writing a blog post about '{query}'.
        3. Ignore opinions, marketing claims, or vague statements.
        4. Return only the factual statements, one per line.
        5. Do not make up or infer facts not present in the content.
        6. Format each fact as a complete sentence.
        
        FACTS:
        """
        
        # Call Gemini API
        import requests
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        headers = {
            "Content-Type": "application/json",
        }
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 1024,
            }
        }
        
        response = requests.post(
            f"{url}?key={gemini_api_key}",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                text = result['candidates'][0]['content']['parts'][0]['text']
                # Extract facts from the response
                facts = [line.strip() for line in text.split('\n') if line.strip() and not line.strip().startswith('FACT') and len(line.strip()) > 20]
                print(f"AI extracted {len(facts)} facts from content")
                return facts[:10]  # Limit to 10 facts
        
        print(f"Warning: AI fact extraction failed with status {response.status_code}. Falling back to rule-based extraction.")
        return extract_facts_rule_based(page_data, query)
    
    except Exception as e:
        print(f"Error in AI fact extraction: {str(e)}. Falling back to rule-based extraction.")
        return extract_facts_rule_based(page_data, query)


def extract_facts_rule_based(page_data, query):
    """Extract factual information from page content using rule-based approach (fallback)"""
    facts = []
    
    # Extract facts from content sample if available
    if 'content' in page_data and 'sample' in page_data['content']:
        content = page_data['content']['sample']
        
        # Split content into sentences
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        for sentence in sentences:
            # Filter for sentences that likely contain facts
            if any(fact_indicator in sentence.lower() for fact_indicator in ['is', 'are', 'was', 'were', 'has', 'have', 'can', 'will', 'should', 'percent', '%', 'study', 'research', 'according', 'survey', 'data']):
                # Clean up the sentence
                clean_sentence = sentence.strip()
                if clean_sentence and len(clean_sentence) > 20 and clean_sentence not in facts:
                    facts.append(clean_sentence)
    
    # Extract facts from headings
    if 'headings' in page_data:
        for heading_type in ['h1', 'h2', 'h3']:
            if heading_type in page_data['headings']:
                for heading in page_data['headings'][heading_type]:
                    if any(fact_indicator in heading.lower() for fact_indicator in ['how', 'why', 'what', 'when', 'where', 'top', 'best', 'guide', 'tips', 'benefits']):
                        if heading not in facts and len(heading) > 10:
                            facts.append(heading)
    
    # Limit the number of facts to avoid overwhelming
    return facts[:10]


def extract_unique_features(result):
    """Extract unique features and facts from a competitor's page"""
    unique_features = []
    
    # First, check if we have AI-extracted facts available
    if 'unique_facts' in result and result['unique_facts']:
        # Use the AI-extracted facts as features
        for fact_item in result['unique_facts']:
            if isinstance(fact_item, dict) and 'fact' in fact_item:
                unique_features.append(fact_item['fact'])
        
        # If we have enough facts, return them
        if len(unique_features) >= 3:
            return unique_features[:5]  # Return up to 5 unique facts
    
    # Fallback: Extract features from content
    content = result.get('content', {}).get('sample', '') or result.get('main_content', '') or result.get('description', '')
    if content:
        # Look for product features, benefits, unique selling points
        feature_patterns = [
            r'feature[s]?[\s\:]+(.*?)(?=\.|$)',
            r'benefit[s]?[\s\:]+(.*?)(?=\.|$)',
            r'advantage[s]?[\s\:]+(.*?)(?=\.|$)',
            r'unique[\s\:]+(.*?)(?=\.|$)',
            r'patent[ed]?[\s\:]+(.*?)(?=\.|$)',
            r'research shows[\s\:]+(.*?)(?=\.|$)',
            r'according to[\s\:]+(.*?)(?=\.|$)',
            r'study found[\s\:]+(.*?)(?=\.|$)',
            r'experts recommend[\s\:]+(.*?)(?=\.|$)'
        ]
        
        for pattern in feature_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches[:3]:  # Limit to 3 matches per pattern
                if len(match) > 10 and len(match) < 150:  # Reasonable length
                    unique_features.append(match.strip())
    
    return unique_features[:5]  # Return up to 5 unique features

def extract_related_keywords(seo_data):
    """Extract related keywords from SEO data"""
    query = seo_data.get('query', '')
    words = query.split()
    
    related = []
    
    # Generate variations
    if len(words) > 1:
        # Rearrange words
        related.append(' '.join(words[::-1]))
        
    # Add common modifiers
    modifiers = ['best', 'top', 'custom', 'professional', 'premium', 'affordable']
    for mod in modifiers:
        if mod not in query.lower():
            related.append(f"{mod} {query}")
    
    # Add purpose modifiers
    purposes = ['for business', 'for home', 'for office', 'for travel']
    for purpose in purposes:
        related.append(f"{query} {purpose}")
    
    return related[:10]  # Limit to 10 related keywords

def calculate_target_metrics(competitors):
    """Calculate target metrics to outperform competitors"""
    if not competitors:
        return {}
    
    # Calculate average and top metrics
    metrics = {
        'word_count': {'avg': 0, 'top': 0},
        'h1_count': {'avg': 0, 'top': 0},
        'h2_count': {'avg': 0, 'top': 0},
        'h3_count': {'avg': 0, 'top': 0},
        'internal_links_count': {'avg': 0, 'top': 0},
        'external_links_count': {'avg': 0, 'top': 0},
        'images_count': {'avg': 0, 'top': 0},
        'schema_count': {'avg': 0, 'top': 0},
        'keyword_density': {'avg': 0, 'top': 0}
    }
    
    for metric in metrics:
        values = [comp.get(metric, 0) for comp in competitors]
        metrics[metric]['avg'] = sum(values) / len(values) if values else 0
        metrics[metric]['top'] = max(values) if values else 0
        # Set target to beat the top competitor
        metrics[metric]['target'] = max(metrics[metric]['top'] * 1.1, metrics[metric]['avg'] * 1.5)
    
    return metrics

def generate_blog_variables(seo_insights):
    """Generate variables to fill in the blog template"""
    query = seo_insights['query']
    competitors = seo_insights['competitors']
    keywords = seo_insights['keywords']
    target_metrics = seo_insights['target_metrics']
    
    # Determine industry and context
    industry = detect_industry(query)
    current_year = datetime.now().year
    
    # Extract all unique features from competitors
    all_unique_features = []
    for comp in competitors:
        if 'unique_features' in comp and comp['unique_features']:
            all_unique_features.extend(comp['unique_features'])
    
    # Collect AI-extracted facts from competitors
    all_facts = []
    fact_by_competitor = {}
    
    # First collect facts from individual competitors
    for i, comp in enumerate(competitors):
        if 'unique_facts' in comp and comp['unique_facts']:
            comp_facts = comp['unique_facts']
            fact_by_competitor[f'COMPETITOR_{i+1}'] = comp_facts
            all_facts.extend(comp_facts)
    
    # Then collect facts from the consolidated all_unique_facts
    if 'all_unique_facts' in seo_insights and seo_insights['all_unique_facts']:
        # Handle both string facts and dict facts
        for fact in seo_insights['all_unique_facts']:
            if isinstance(fact, dict) and 'fact' in fact:
                all_facts.append(fact['fact'])
            elif isinstance(fact, str):
                all_facts.append(fact)
    
    print(f"Collected {len(all_facts)} total facts from all sources")
    
    # Deduplicate facts and features
    unique_features = []
    unique_facts = []
    
    # First deduplicate features
    for feature in all_unique_features:
        is_duplicate = False
        for unique_feature in unique_features:
            # Simple string similarity check
            if similarity_score(feature, unique_feature) > 0.7:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_features.append(feature)
    
    # Then deduplicate facts
    for fact in all_facts:
        is_duplicate = False
        for unique_fact in unique_facts:
            # Simple string similarity check
            if similarity_score(fact, unique_fact) > 0.7:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_facts.append(fact)
    
    print(f"After deduplication: {len(unique_features)} unique features and {len(unique_facts)} unique facts")
    
    # Create variables dictionary
    variables = {
        'PRIMARY_KEYWORD': query,
        'SINGULAR_KEYWORD': keywords['singular'],
        'URL_FRIENDLY_KEYWORD': query.replace(' ', '-').lower(),
        'URL_FRIENDLY_SINGULAR_KEYWORD': keywords['singular'].replace(' ', '-').lower(),
        'CURRENT_DATE': datetime.now().strftime('%B %d, %Y'),
        'ISO_DATE': datetime.now().strftime('%Y-%m-%d'),
        'CURRENT_YEAR': str(current_year),
        'INDUSTRY': industry,
        'INDUSTRY_CONTEXT': f"fast-paced {industry} world",
        'HERO_IMAGE_URL': f"https://example.com/images/{query.replace(' ', '-')}-hero.jpg",
        'PRODUCT_IMAGE_URL': f"https://example.com/images/{query.replace(' ', '-')}-collection.jpg",
        'LOGO_URL': "https://example.com/logo.png",
        'PUBLISHER': f"{industry.title()} Accessories Guide",
        'COLLECTION_URL': f"https://example.com/{query.replace(' ', '-')}",
        'DISCOUNT_CODE': "BLOG15",
        'DISCOUNT_PERCENTAGE': "15%",
        'LOW_PRICE': "9.99",
        'HIGH_PRICE': "59.99",
        'CURRENCY': "USD",
        'RATING': "4.8",
        'REVIEW_COUNT': "1247",
        'EXPERIENCE': "15",
        'DEFINITION': f"the process of optimizing {keywords['singular']} to achieve better results and performance",
        'RELATED_TERM': f"{keywords['singular']} optimization",
        'RELATED_ASPECT': "performance enhancement",
        'METRIC_1': "conversion rate",
        'METRIC_2': "engagement metrics",
        'TOOL_1': f"{industry} Analytics Pro",
        'TOOL_2': f"{keywords['singular'].title()} Optimizer",
        'TOOL_3': f"Advanced {industry} Suite",
        'TECHNOLOGY_1': "artificial intelligence",
        'TREND_1': "personalization",
        'TREND_2': "automated optimization",
        
        # Add AI-extracted facts to the variables
        'AI_FACTS_AVAILABLE': 'yes' if unique_facts else 'no',
        'AI_FACTS_COUNT': str(len(unique_facts)),
        'ALL_AI_FACTS': '\n'.join([f'- {fact}' for fact in unique_facts]) if unique_facts else 'No facts available',
    }
    
    # Extract competitor-specific information
    for i, comp in enumerate(competitors[:5]):
        variables[f'COMPETITOR_{i+1}'] = comp['name']
        if comp.get('unique_features'):
            variables[f'UNIQUE_FEATURE_{i+1}'] = comp['unique_features'][0]
        
        # Add competitor-specific facts if available
        if f'COMPETITOR_{i+1}' in fact_by_competitor and fact_by_competitor[f'COMPETITOR_{i+1}']:
            comp_facts = fact_by_competitor[f'COMPETITOR_{i+1}']
            variables[f'COMPETITOR_{i+1}_FACTS_AVAILABLE'] = 'yes'
            variables[f'COMPETITOR_{i+1}_FACTS_COUNT'] = str(len(comp_facts))
            variables[f'COMPETITOR_{i+1}_FACTS'] = '\n'.join([f'- {fact}' for fact in comp_facts[:5]])
            
            # Add individual facts
            for j, fact in enumerate(comp_facts[:3]):
                variables[f'COMPETITOR_{i+1}_FACT_{j+1}'] = fact
        else:
            variables[f'COMPETITOR_{i+1}_FACTS_AVAILABLE'] = 'no'
            variables[f'COMPETITOR_{i+1}_FACTS_COUNT'] = '0'
            variables[f'COMPETITOR_{i+1}_FACTS'] = 'No facts available'
    
    # Add individual facts to variables
    for i, fact in enumerate(unique_facts[:10]):
        variables[f'FACT_{i+1}'] = fact
    
    # Generate use cases based on the query
    use_cases = generate_use_cases(query)
    for i, use_case in enumerate(use_cases[:3]):
        variables[f'USE_CASE_{i+1}'] = use_case
    
    # Generate product types based on the query
    product_types = generate_product_types(query)
    for i, product_type in enumerate(product_types[:4]):
        variables[f'TYPE_{i+1}'] = product_type
        variables[f'TYPE_{i+1}_DESCRIPTION'] = f"These are specialized {query} designed for {use_cases[i % len(use_cases)]}"
    
    # Generate factors to consider
    factors = generate_factors(query)
    for i, factor in enumerate(factors[:4]):
        variables[f'FACTOR_{i+1}'] = factor
        variables[f'URL_FRIENDLY_FACTOR_{i+1}'] = factor.replace(' ', '-').lower()
    
    # Generate aspects to consider
    aspects = generate_aspects(query)
    for i, aspect in enumerate(aspects[:4]):
        variables[f'ASPECT_{i+1}'] = aspect
        variables[f'URL_FRIENDLY_ASPECT_{i+1}'] = aspect.replace(' ', '-').lower()
    
    # Generate usage aspects
    usage_aspects = generate_usage_aspects(query)
    for i, aspect in enumerate(usage_aspects[:2]):
        variables[f'USAGE_ASPECT_{i+1}'] = aspect
        variables[f'URL_FRIENDLY_USAGE_ASPECT_{i+1}'] = aspect.replace(' ', '-').lower()
    
    # Generate contexts
    contexts = generate_contexts(query)
    for i, context in enumerate(contexts[:3]):
        variables[f'CONTEXT_{i+1}'] = context
        variables[f'URL_FRIENDLY_CONTEXTS'] = "settings"
        variables[f'CONTEXT_{i+1}_DESCRIPTION'] = f"{context} environments"
    
    # Set target metrics
    variables['TARGET_WORD_COUNT'] = int(target_metrics['word_count']['target'])
    variables['TARGET_INTERNAL_LINKS'] = int(target_metrics['internal_links_count']['target'])
    variables['TARGET_EXTERNAL_LINKS'] = int(target_metrics['external_links_count']['target'])
    variables['TARGET_IMAGES'] = int(target_metrics['images_count']['target'])
    
    return variables

def similarity_score(str1, str2):
    """Calculate a simple similarity score between two strings"""
    # Convert to lowercase and split into words
    words1 = set(str1.lower().split())
    words2 = set(str2.lower().split())
    
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0

def detect_industry(query):
    """Detect the industry based on the query"""
    industry_keywords = {
        'tech': ['software', 'app', 'technology', 'digital', 'computer', 'laptop', 'smartphone', 'gadget'],
        'fashion': ['clothing', 'fashion', 'apparel', 'shoes', 'accessories', 'jewelry', 'watch'],
        'health': ['health', 'fitness', 'workout', 'exercise', 'diet', 'nutrition', 'wellness'],
        'home': ['home', 'furniture', 'decor', 'kitchen', 'bedroom', 'bathroom', 'garden'],
        'beauty': ['beauty', 'skincare', 'makeup', 'cosmetics', 'hair', 'fragrance'],
        'food': ['food', 'recipe', 'cooking', 'baking', 'meal', 'restaurant', 'dining'],
        'travel': ['travel', 'vacation', 'hotel', 'flight', 'destination', 'tourism', 'resort'],
        'finance': ['finance', 'money', 'investment', 'banking', 'credit', 'loan', 'insurance'],
        'education': ['education', 'learning', 'course', 'school', 'college', 'university', 'training'],
        'automotive': ['car', 'vehicle', 'automotive', 'truck', 'suv', 'motorcycle', 'auto']
    }
    
    query_terms = query.lower().split()
    
    for industry, keywords in industry_keywords.items():
        for term in query_terms:
            if term in keywords or any(term in keyword for keyword in keywords):
                return industry
    
    return "digital"  # Default industry

def generate_use_cases(query):
    """Generate use cases based on the query"""
    words = query.lower().split()
    
    # Default use cases
    use_cases = [
        "everyday use",
        "professional settings",
        "travel and outdoor activities"
    ]
    
    # Customize based on query
    if any(word in words for word in ['phone', 'smartphone', 'mobile']):
        use_cases = [
            "desk and office use",
            "car and travel",
            "hands-free viewing"
        ]
    elif any(word in words for word in ['laptop', 'computer']):
        use_cases = [
            "ergonomic positioning",
            "cooling and ventilation",
            "space-saving setups"
        ]
    
    return use_cases

def generate_product_types(query):
    """Generate product types based on the query"""
    words = query.lower().split()
    
    # Default product types
    product_types = [
        "Standard Models",
        "Premium Versions",
        "Portable Options",
        "Multi-functional Designs"
    ]
    
    # Customize based on query
    if any(word in words for word in ['phone', 'smartphone', 'mobile']):
        product_types = [
            "Desk and Tabletop Stands",
            "Car Mounts and Vehicle Holders",
            "Grip-Style Holders and PopSockets",
            "Promotional and Branded Holders"
        ]
    elif any(word in words for word in ['laptop', 'computer']):
        product_types = [
            "Adjustable Height Stands",
            "Cooling Platforms",
            "Portable Folding Stands",
            "Docking Stations"
        ]
    
    return product_types

def generate_factors(query):
    """Generate factors to consider based on the query"""
    words = query.lower().split()
    
    # Default factors
    factors = [
        "Materials",
        "Durability",
        "Design",
        "Functionality"
    ]
    
    # Customize based on query
    if any(word in words for word in ['phone', 'smartphone', 'mobile']):
        factors = [
            "Materials",
            "Durability",
            "Adjustability",
            "Compatibility"
        ]
    elif any(word in words for word in ['laptop', 'computer']):
        factors = [
            "Materials",
            "Weight Capacity",
            "Cooling Features",
            "Portability"
        ]
    
    return factors

def generate_aspects(query):
    """Generate aspects to consider based on the query"""
    words = query.lower().split()
    
    # Default aspects
    aspects = [
        "Features",
        "Benefits",
        "Customization",
        "Applications"
    ]
    
    # Customize based on query
    if 'custom' in words:
        aspects = [
            "Features",
            "Benefits",
            "Customization",
            "Branding"
        ]
    
    return aspects

def generate_usage_aspects(query):
    """Generate usage aspects based on the query"""
    words = query.lower().split()
    
    # Default usage aspects
    usage_aspects = [
        "Installation",
        "Usage",
        "Maintenance",
        "Storage"
    ]
    
    # Customize based on query
    if any(word in words for word in ['mount', 'holder', 'stand']):
        usage_aspects = [
            "Installation",
            "Positioning",
            "Adjustment",
            "Removal"
        ]
    
    return usage_aspects

def generate_contexts(query):
    """Generate contexts based on the query"""
    words = query.lower().split()
    
    # Default contexts
    contexts = [
        "Home",
        "Office",
        "Travel"
    ]
    
    # Customize based on query
    if any(word in words for word in ['phone', 'smartphone', 'mobile']):
        contexts = [
            "Office and Desk",
            "Vehicle and Travel",
            "Promotional Events"
        ]
    elif any(word in words for word in ['laptop', 'computer']):
        contexts = [
            "Home Office",
            "Corporate Environment",
            "Mobile Workstation"
        ]
    
    return contexts

def fill_placeholders_with_gemini(template_content, variables, query):
    """Use Gemini 2.5 Flash Preview to fill in any remaining placeholders in the template"""
    # Find all remaining placeholders
    remaining_placeholders = re.findall(r'\{\{([A-Z0-9_]+)\}\}', template_content)
    
    if not remaining_placeholders:
        return template_content
    
    print(f"Found {len(remaining_placeholders)} placeholders to fill with Gemini AI")
    
    # Group similar placeholders
    placeholder_groups = {}
    for placeholder in remaining_placeholders:
        # Extract the base name without numbers
        base_name = re.sub(r'_\d+$', '', placeholder)
        if base_name not in placeholder_groups:
            placeholder_groups[base_name] = []
        placeholder_groups[base_name].append(placeholder)
    
    # For each group, create a batch request to Gemini
    for base_name, placeholders in placeholder_groups.items():
        # Create a prompt for this group of placeholders
        prompt = f"""You are an expert SEO content writer creating a blog post about '{query}'.
        Generate content for the following placeholders in a blog template:
        
        {', '.join(placeholders)}
        
        Based on the naming pattern, these placeholders seem to be about: {base_name}
        
        For each placeholder, provide content that is:
        1. Specific and relevant to '{query}'
        2. Demonstrates expertise (E-E-A-T)
        3. Is factually accurate
        4. Has a natural, human-like writing style
        5. Is appropriate length for a blog section (1-3 sentences for most items)
        
        Return your response as a JSON object with the placeholder names as keys and the content as values.
        """
        
        try:
            # Call Gemini API
            headers = {
                "Content-Type": "application/json"
            }
            
            data = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 1024,
                }
            }
            
            if GEMINI_API_KEY:
                url = GEMINI_FLASH_API_URL
                if "?key=" not in url:
                    url = f"{url}?key={GEMINI_API_KEY}"
            else:
                print("No Gemini API key found, using fallback placeholder generation")
                # Use fallback for this group
                for placeholder in placeholders:
                    replacement = generate_placeholder_content(placeholder)
                    template_content = template_content.replace('{{' + placeholder + '}}', replacement)
                continue
                
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code != 200:
                print(f"Error calling Gemini API: {response.status_code} - {response.text}")
                # Use fallback for this group
                for placeholder in placeholders:
                    replacement = generate_placeholder_content(placeholder)
                    template_content = template_content.replace('{{' + placeholder + '}}', replacement)
                continue
                
            response_json = response.json()
            
            # Extract the generated text
            if 'candidates' in response_json and len(response_json['candidates']) > 0:
                generated_text = response_json['candidates'][0]['content']['parts'][0]['text']
                
                # Try to extract JSON from the response
                try:
                    # Find JSON object in the response
                    json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        placeholder_values = json.loads(json_str)
                        
                        # Replace placeholders with their values
                        for placeholder, value in placeholder_values.items():
                            template_content = template_content.replace('{{' + placeholder + '}}', str(value))
                    else:
                        print(f"Could not find JSON in Gemini response for {base_name} placeholders")
                        # Use fallback for this group
                        for placeholder in placeholders:
                            replacement = generate_placeholder_content(placeholder)
                            template_content = template_content.replace('{{' + placeholder + '}}', replacement)
                except json.JSONDecodeError:
                    print(f"Could not parse JSON from Gemini response for {base_name} placeholders")
                    # Use fallback for this group
                    for placeholder in placeholders:
                        replacement = generate_placeholder_content(placeholder)
                        template_content = template_content.replace('{{' + placeholder + '}}', replacement)
            else:
                print(f"Unexpected response format from Gemini API for {base_name} placeholders")
                # Use fallback for this group
                for placeholder in placeholders:
                    replacement = generate_placeholder_content(placeholder)
                    template_content = template_content.replace('{{' + placeholder + '}}', replacement)
        except Exception as e:
            print(f"Error generating content with Gemini: {str(e)}")
            # Use fallback for this group
            for placeholder in placeholders:
                replacement = generate_placeholder_content(placeholder)
                template_content = template_content.replace('{{' + placeholder + '}}', replacement)
    
    # Check if there are still any remaining placeholders
    remaining_placeholders = re.findall(r'\{\{([A-Z0-9_]+)\}\}', template_content)
    if remaining_placeholders:
        print(f"Still found {len(remaining_placeholders)} placeholders after Gemini processing. Using fallback.")
        # Use fallback for any that weren't filled
        for placeholder in remaining_placeholders:
            replacement = generate_placeholder_content(placeholder)
            template_content = template_content.replace('{{' + placeholder + '}}', replacement)
    
    return template_content

def fill_template(template_path, variables, ai_resistant=False):
    """Fill in the template with the generated variables"""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Replace all variables in the template
        for var_name, var_value in variables.items():
            placeholder = '{{' + var_name + '}}'
            template_content = template_content.replace(placeholder, str(var_value))
        
        # Use Gemini to fill in any remaining placeholders
        query = variables.get('PRIMARY_KEYWORD', '')
        template_content = fill_placeholders_with_gemini(template_content, variables, query)
        
        # If AI-resistant mode is enabled, apply techniques to make the content less detectable by AI
        if ai_resistant:
            template_content = make_ai_resistant(template_content)
        
        return template_content
    except Exception as e:
        print(f"Error filling template: {str(e)}")
        return ""

def make_ai_resistant(content):
    """Apply techniques to make content less detectable by AI detection systems"""
    import random
    import re
    
    # 1. Add slight variations in punctuation and spacing
    punctuation_variations = {
        '.': ['.', '. ', '.  '],
        ',': [',', ', ', ',  '],
        '!': ['!', '! ', '!  '],
        '?': ['?', '? ', '?  ']
    }
    
    for punct, variations in punctuation_variations.items():
        pattern = f'\\{punct}'
        matches = list(re.finditer(pattern, content))
        # Only modify a percentage of matches to maintain readability
        if matches:
            for match in random.sample(matches, min(len(matches) // 3, len(matches))):
                pos = match.start()
                replacement = random.choice(variations)
                content = content[:pos] + replacement + content[pos+1:]
    
    # 2. Introduce occasional typos and correct them with HTML
    paragraphs = content.split('\n\n')
    modified_paragraphs = []
    
    for paragraph in paragraphs:
        if len(paragraph) > 100 and random.random() < 0.2:  # 20% chance for longer paragraphs
            words = paragraph.split(' ')
            if len(words) > 10:
                # Select a random word to "typo and correct"
                idx = random.randint(5, len(words) - 5)
                word = words[idx]
                if len(word) > 4:
                    # Create a simple typo by swapping two adjacent letters
                    pos = random.randint(1, len(word) - 2)
                    typo_word = word[:pos] + word[pos+1] + word[pos] + word[pos+2:]
                    # Replace the word with the typo and correction
                    words[idx] = f"<span title='{typo_word}'>{word}</span>"
            paragraph = ' '.join(words)
        modified_paragraphs.append(paragraph)
    
    content = '\n\n'.join(modified_paragraphs)
    
    # 3. Add invisible zero-width characters at random positions
    zero_width_chars = ['\u200B', '\u200C', '\u200D']
    content_chars = list(content)
    
    # Insert zero-width characters at random positions (about 1 per 100 characters)
    for i in range(len(content) // 100):
        pos = random.randint(0, len(content_chars) - 1)
        # Avoid inserting in the middle of HTML tags or markdown formatting
        if content_chars[pos].isalnum():
            content_chars.insert(pos, random.choice(zero_width_chars))
    
    content = ''.join(content_chars)
    
    return content

def generate_placeholder_content(placeholder):
    """Generate appropriate content for a placeholder based on its name"""
    # Extract the base name without numbering
    base_name = re.sub(r'_\d+(_\d+)?$', '', placeholder)
    
    # Create content based on placeholder type
    if 'FEATURE' in placeholder:
        return f"Adjustable viewing angle"
    elif 'BENEFIT' in placeholder:
        return f"improved ergonomics and reduced strain"
    elif 'DETAIL' in placeholder:
        return f"providing optimal comfort during extended use"
    elif 'SUBTYPE' in placeholder:
        return f"Premium model"
    elif 'ADVANTAGE' in placeholder:
        return f"Enhanced durability"
    elif 'UNIQUE' in placeholder:
        return f"innovative design"
    elif 'MATERIAL' in placeholder:
        return f"aluminum alloy"
    elif 'PROBLEM' in placeholder:
        return f"device slippage"
    elif 'FACTOR' in placeholder:
        return f"stability"
    elif 'QUALITY' in placeholder:
        return f"durability"
    elif 'ASPECT' in placeholder:
        return f"versatility"
    elif 'TECHNIQUE' in placeholder:
        return f"precision molding"
    elif 'ELEMENT' in placeholder:
        return f"color scheme"
    elif 'CUSTOMIZATION' in placeholder:
        return f"logo printing"
    elif 'CONTEXT' in placeholder:
        return f"professional environment"
    elif 'TIP' in placeholder:
        return f"Secure installation"
    elif 'MAINTENANCE' in placeholder:
        return f"Regular cleaning"
    elif 'LIFESPAN' in placeholder:
        return f"2-3 years"
    elif 'PRICE' in placeholder:
        return f"$15-$25"
    elif 'REVIEWER' in placeholder:
        return f"John D."
    elif 'PROFESSION' in placeholder:
        return f"Product Designer"
    elif 'COMPONENT' in placeholder:
        return f"mounting mechanism"
    elif 'ACCESSORY' in placeholder:
        return f"protective case"
    elif 'COMPATIBILITY' in placeholder:
        return f"device dimensions"
    elif 'SPEC' in placeholder:
        return f"width and thickness"
    elif 'LOCATION' in placeholder:
        return f"California"
    elif 'USAGE' in placeholder:
        return f"hands-free viewing"
    elif 'AUDIENCE' in placeholder:
        return f"professionals"
    elif 'PRODUCT' in placeholder:
        return f"premium stand"
    else:
        # Generic replacement for any other placeholder types
        return f"high-quality option"

def convert_markdown_to_html(markdown_content):
    """Convert markdown content to HTML"""
    # Use the markdown library to convert to HTML
    html_content = markdown.markdown(markdown_content, extensions=['extra', 'codehilite'])
    
    # Wrap in a nice HTML template with styling
    html_template = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SEO Optimized Blog</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1, h2, h3, h4, h5, h6 {{
                color: #2c3e50;
                margin-top: 1.5em;
            }}
            h1 {{
                font-size: 2.2em;
                border-bottom: 1px solid #eaecef;
                padding-bottom: 0.3em;
            }}
            h2 {{
                font-size: 1.8em;
                border-bottom: 1px solid #eaecef;
                padding-bottom: 0.3em;
            }}
            p {{
                margin: 1em 0;
            }}
            a {{
                color: #3498db;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            code {{
                background-color: #f8f8f8;
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-family: Consolas, Monaco, 'Andale Mono', monospace;
                font-size: 0.9em;
            }}
            blockquote {{
                border-left: 4px solid #dfe2e5;
                padding: 0 1em;
                color: #6a737d;
                margin: 0;
            }}
            img {{
                max-width: 100%;
                height: auto;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
            }}
            table, th, td {{
                border: 1px solid #dfe2e5;
            }}
            th, td {{
                padding: 8px 16px;
                text-align: left;
            }}
            th {{
                background-color: #f6f8fa;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    '''
    
    return html_template

def save_blog_post(content, output_file, save_html=True, html_dir=None):
    """Save the generated blog post to a file"""
    # Save markdown version
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Blog post saved to {output_file}")
    
    # Also save as HTML if requested
    if save_html:
        # Get the base filename without path
        base_filename = os.path.basename(output_file)
        html_filename = os.path.splitext(base_filename)[0] + '.html'
        
        # If html_dir is specified, save HTML there, otherwise save next to markdown file
        if html_dir:
            os.makedirs(html_dir, exist_ok=True)
            html_output_file = os.path.join(html_dir, html_filename)
        else:
            html_output_file = os.path.splitext(output_file)[0] + '.html'
        
        html_content = convert_markdown_to_html(content)
        with open(html_output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML version saved to {html_output_file}")
        
        return html_output_file
    
    return None

def main(args=None):
    if args is None:
        parser = argparse.ArgumentParser(description='Generate SEO-optimized blog posts from SEO analysis')
        parser.add_argument('input_file', help='Path to the JSON file containing SEO analysis')
        parser.add_argument('--template', default='advanced_blog_template.md', help='Path to the blog template file')
        parser.add_argument('--output', help='Path to save the generated blog post (default: blog_[query].md)')
        parser.add_argument('--ai-resistant', action='store_true', help='Generate content that is resistant to AI detection')
        parser.add_argument('--html-dir', help='Directory containing extracted HTML content from competitor pages')
        args = parser.parse_args()
    
    # Handle both command line args and direct function calls
    input_file = args[0] if isinstance(args, list) else args.input_file
    
    if isinstance(args, list):
        # Parse command line style arguments from list
        template = 'advanced_blog_template.md'
        output = None
        ai_resistant = False
        html_dir = None
        
        for i, arg in enumerate(args):
            if arg == '--template' and i+1 < len(args):
                template = args[i+1]
            elif arg == '--output' and i+1 < len(args):
                output = args[i+1]
            elif arg == '--html-dir' and i+1 < len(args):
                html_dir = args[i+1]
            elif arg == '--ai-resistant':
                ai_resistant = True
    else:
        template = args.template
        output = args.output
        html_dir = args.html_dir if hasattr(args, 'html_dir') else None
        ai_resistant = args.ai_resistant if hasattr(args, 'ai_resistant') else False
        
    # Log the HTML directory for debugging
    if html_dir:
        print(f"Using HTML extraction directory: {html_dir}")
    else:
        print("No HTML extraction directory provided, will rely on SERP data only")
    
    # Load SEO analysis
    seo_data = load_seo_analysis(input_file)
    
    # Extract SEO insights with HTML content if available
    seo_insights = extract_seo_insights(seo_data, html_dir)
    
    # Generate variables for the template
    variables = generate_blog_variables(seo_insights)
    
    # Fill in the template with AI resistance if requested
    blog_content = fill_template(template, variables, ai_resistant)
    
    # Save the blog post
    if output:
        output_file = output
    else:
        query = seo_insights['query'].replace(' ', '_').lower()
        output_file = f"blog_{query}.md"
    
    # Get the HTML reports directory from environment variable or Flask app
    html_dir = None
    
    # First check environment variable (set by app.py)
    if 'HTML_REPORTS_DIR' in os.environ:
        html_dir = os.environ['HTML_REPORTS_DIR']
        print(f"Using HTML reports directory from environment: {html_dir}")
    else:
        # Try to import from app (this might not work if running standalone)
        try:
            from app import get_html_report_dir
            html_dir = get_html_report_dir()
            print(f"Using HTML reports directory from app: {html_dir}")
        except ImportError:
            print("Not running in Flask app, HTML will be saved next to markdown file")
    
    # Save both markdown and HTML versions
    html_output_file = save_blog_post(blog_content, output_file, save_html=True, html_dir=html_dir)
    
    print(f"Successfully generated blog post for '{seo_insights['query']}'")
    print(f"Target metrics to outrank competitors:")
    print(f"- Word count: {variables['TARGET_WORD_COUNT']}")
    print(f"- Internal links: {variables['TARGET_INTERNAL_LINKS']}")
    print(f"- External links: {variables['TARGET_EXTERNAL_LINKS']}")
    print(f"- Images: {variables['TARGET_IMAGES']}")
    
    if ai_resistant:
        print("\nAI-RESISTANT MODE: Content has been enhanced to resist AI detection.")
        print("- Added subtle text variations")
        print("- Incorporated zero-width characters")
        print("- Included occasional HTML-corrected 'typos'")
    
    print("\nNOTE: All placeholders have been replaced with appropriate content.")
    print("The blog is now complete and ready for publication with no template elements remaining.")
    print("The content is available in both Markdown and HTML formats.")
    print(f"- Markdown: {output_file}")
    print(f"- HTML: {html_output_file}")
    
    # Print information about the unique facts used
    if 'all_unique_facts' in seo_insights and seo_insights['all_unique_facts']:
        print(f"\nIncorporated {len(seo_insights['all_unique_facts'])} unique facts from source content for E-E-A-T signals.")
    elif any('unique_facts' in result for result in seo_insights.get('competitors', [])):
        fact_count = sum(len(result.get('unique_facts', [])) for result in seo_insights.get('competitors', []))
        print(f"\nIncorporated {fact_count} unique facts from competitor content for E-E-A-T signals.")

    
    return {
        'query': seo_insights['query'],
        'output_file': output_file,
        'html_output_file': html_output_file,
        'metrics': {
            'word_count': variables['TARGET_WORD_COUNT'],
            'internal_links': variables['TARGET_INTERNAL_LINKS'],
            'external_links': variables['TARGET_EXTERNAL_LINKS'],
            'images': variables['TARGET_IMAGES']
        }
    }

if __name__ == "__main__":
    main()
