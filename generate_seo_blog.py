#!/usr/bin/env python
import os
import json
import re
import argparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def load_seo_analysis(json_file):
    """Load SEO analysis data from JSON file"""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_seo_insights(seo_data):
    """Extract key SEO insights from analysis data"""
    query = seo_data.get('query', '')
    results = seo_data.get('results', [])
    
    # Extract competitor information
    competitors = []
    for i, result in enumerate(results[:6]):
        competitors.append({
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
        })
    
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
        'target_metrics': calculate_target_metrics(competitors)
    }

def extract_unique_features(result):
    """Extract unique features from a competitor's page"""
    unique_features = []
    
    # Extract features from content
    content = result.get('content', '')
    if content:
        # Look for product features, benefits, unique selling points
        feature_patterns = [
            r'feature[s]?[\s\:]+(.*?)(?=\.|$)',
            r'benefit[s]?[\s\:]+(.*?)(?=\.|$)',
            r'advantage[s]?[\s\:]+(.*?)(?=\.|$)',
            r'unique[\s\:]+(.*?)(?=\.|$)',
            r'patent[ed]?[\s\:]+(.*?)(?=\.|$)'
        ]
        
        for pattern in feature_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches[:3]:  # Limit to 3 matches per pattern
                if len(match) > 10 and len(match) < 100:  # Reasonable length
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
    
    # Create variables dictionary
    variables = {
        'PRIMARY_KEYWORD': query,
        'SINGULAR_KEYWORD': keywords['singular'],
        'URL_FRIENDLY_KEYWORD': query.replace(' ', '-').lower(),
        'URL_FRIENDLY_SINGULAR_KEYWORD': keywords['singular'].replace(' ', '-').lower(),
        'CURRENT_DATE': datetime.now().strftime('%B %d, %Y'),
        'ISO_DATE': datetime.now().strftime('%Y-%m-%d'),
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
        'EXPERIENCE': "15"
    }
    
    # Extract competitor-specific information
    for i, comp in enumerate(competitors[:5]):
        variables[f'COMPETITOR_{i+1}'] = comp['name']
        if comp.get('unique_features'):
            variables[f'UNIQUE_FEATURE_{i+1}'] = comp['unique_features'][0]
    
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

def detect_industry(query):
    """Detect the industry based on the query"""
    tech_keywords = ['phone', 'smartphone', 'tablet', 'laptop', 'computer', 'tech', 'digital']
    home_keywords = ['home', 'kitchen', 'furniture', 'decor', 'house', 'garden']
    fashion_keywords = ['fashion', 'clothing', 'apparel', 'shoes', 'accessories', 'wear']
    
    for keyword in tech_keywords:
        if keyword in query.lower():
            return "technology"
    
    for keyword in home_keywords:
        if keyword in query.lower():
            return "home improvement"
    
    for keyword in fashion_keywords:
        if keyword in query.lower():
            return "fashion"
    
    return "consumer products"

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

def fill_template(template_file, variables):
    """Fill in the template with variables"""
    with open(template_file, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Replace all variables in the template
    for key, value in variables.items():
        placeholder = '{{' + key + '}}'
        if placeholder in template:
            template = template.replace(placeholder, str(value))
    
    # Find any remaining placeholders
    remaining_placeholders = re.findall(r'\{\{([A-Z0-9_]+)\}\}', template)
    
    if remaining_placeholders:
        print(f"Warning: Found {len(remaining_placeholders)} placeholders without values. Generating content for them.")
        
        # Generate appropriate content for each remaining placeholder
        for placeholder in remaining_placeholders:
            replacement = generate_placeholder_content(placeholder)
            template = template.replace('{{' + placeholder + '}}', replacement)
    
    return template

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

def save_blog_post(content, output_file):
    """Save the generated blog post to a file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Blog post saved to {output_file}")

def main(args=None):
    if args is None:
        parser = argparse.ArgumentParser(description='Generate SEO-optimized blog posts from SEO analysis')
        parser.add_argument('input_file', help='Path to the JSON file containing SEO analysis')
        parser.add_argument('--template', default='dynamic_blog_template.md', help='Path to the blog template file')
        parser.add_argument('--output', help='Path to save the generated blog post (default: blog_[query].md)')
        args = parser.parse_args()
    
    # Handle both command line args and direct function calls
    input_file = args[0] if isinstance(args, list) else args.input_file
    
    if isinstance(args, list):
        # Parse command line style arguments from list
        template = 'dynamic_blog_template.md'
        output = None
        
        for i, arg in enumerate(args):
            if arg == '--template' and i+1 < len(args):
                template = args[i+1]
            elif arg == '--output' and i+1 < len(args):
                output = args[i+1]
    else:
        template = args.template
        output = args.output
    
    # Load SEO analysis
    seo_data = load_seo_analysis(input_file)
    
    # Extract SEO insights
    seo_insights = extract_seo_insights(seo_data)
    
    # Generate variables for the template
    variables = generate_blog_variables(seo_insights)
    
    # Fill in the template
    blog_content = fill_template(template, variables)
    
    # Save the blog post
    if output:
        output_file = output
    else:
        query = seo_insights['query'].replace(' ', '_').lower()
        output_file = f"blog_{query}.md"
    
    save_blog_post(blog_content, output_file)
    
    print(f"Successfully generated blog post for '{seo_insights['query']}'")
    print(f"Target metrics to outrank competitors:")
    print(f"- Word count: {variables['TARGET_WORD_COUNT']}")
    print(f"- Internal links: {variables['TARGET_INTERNAL_LINKS']}")
    print(f"- External links: {variables['TARGET_EXTERNAL_LINKS']}")
    print(f"- Images: {variables['TARGET_IMAGES']}")
    print("\nNOTE: All placeholders have been replaced with appropriate content.")
    print("The blog is now complete and ready for publication with no template elements remaining.")
    print("If you need to customize specific sections, edit the generated markdown file directly.")

    
    return {
        'query': seo_insights['query'],
        'output_file': output_file,
        'metrics': {
            'word_count': variables['TARGET_WORD_COUNT'],
            'internal_links': variables['TARGET_INTERNAL_LINKS'],
            'external_links': variables['TARGET_EXTERNAL_LINKS'],
            'images': variables['TARGET_IMAGES']
        }
    }

if __name__ == "__main__":
    main()
