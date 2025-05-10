import json
import requests
import argparse
import os
from datetime import datetime
from api_config import GEMINI_API_KEY, GEMINI_API_URL
from fact_extractor import extract_facts_from_serp_data

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
        
        # Analyze internal links
        internal_link_analysis = ""
        if seo_data['internal_links']:
            internal_link_analysis = "\n\nInternal Links (sample):\n"
            for i, link in enumerate(seo_data['internal_links'][:10]):
                internal_link_analysis += f"\n{i+1}. URL: {link.get('url', '')}\n   Text: {link.get('text', '')}\n   NoFollow: {link.get('nofollow', False)}"
        
        # Analyze external links
        external_link_analysis = ""
        if seo_data['external_links']:
            external_link_analysis = "\n\nExternal Links (sample):\n"
            for i, link in enumerate(seo_data['external_links'][:10]):
                external_link_analysis += f"\n{i+1}. URL: {link.get('url', '')}\n   Text: {link.get('text', '')}\n   NoFollow: {link.get('nofollow', False)}"
        
        # Schema analysis
        schema_analysis = ""
        if seo_data['schema_data']:
            schema_analysis = "\n\nSchema Markup (sample):\n"
            for i, schema in enumerate(seo_data['schema_data'][:3]):
                schema_analysis += f"\n{i+1}. Type: {schema.get('type', 'Unknown')}"
                if schema.get('properties'):
                    schema_analysis += "\n   Properties:"
                    for prop, value in schema.get('properties', {}).items():
                        if isinstance(value, str) and len(value) < 100:
                            schema_analysis += f"\n     - {prop}: {value}"
        
        # Prepare the prompt for Gemini
        prompt = f"""
You are an expert SEO analyst. Analyze the following webpage data and provide a detailed SEO analysis with actionable recommendations.

Page Information:
- Title: {seo_data['title']}
- URL: {seo_data['url']}
- Meta Description: {seo_data['meta_description']}
- Meta Keywords: {seo_data['meta_keywords']}
- Word Count: {seo_data['word_count']}
- Internal Links: {seo_data['internal_links_count']}
- External Links: {seo_data['external_links_count']}
- Images: {seo_data['images_count']}
- Images with Alt Text: {seo_data.get('images_with_alt_count', 0)}

Header Structure:
- H1 Tags ({len(seo_data['h1_tags'])}): {', '.join(seo_data['h1_tags'][:5]) if seo_data['h1_tags'] else 'None'}
- H2 Tags ({len(seo_data['h2_tags'])}): {', '.join(seo_data['h2_tags'][:5]) if seo_data['h2_tags'] else 'None'}
- H3 Tags ({len(seo_data['h3_tags'])}): {', '.join(seo_data['h3_tags'][:5]) if seo_data['h3_tags'] else 'None'}
{internal_link_analysis}
{external_link_analysis}
{schema_analysis}

Provide a comprehensive SEO analysis of this page covering:
1. Title Tag Analysis
2. Meta Description Analysis
3. URL Structure Analysis
4. Content Quality and Length Analysis
5. Heading Structure Analysis
6. Internal Linking Analysis
7. External Linking Analysis
8. Image Optimization
9. Schema Markup Analysis (if present)
10. Overall SEO Score (out of 100)
11. Top 3 Strengths
12. Top 3 Areas for Improvement
13. Specific Actionable Recommendations

Format your response in Markdown with clear headings and bullet points.
"""

        # Prepare the request payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        # Make the API request
        try:
            response = requests.post(API_URL, json=payload)
            response_json = response.json()
            
            if 'candidates' in response_json and len(response_json['candidates']) > 0:
                seo_analysis = response_json['candidates'][0]['content']['parts'][0]['text']
                result['seo_analysis'] = seo_analysis
                print(f"SEO analysis completed for result {i+1}")
            else:
                print(f"Error in API response for result {i+1}: {response_json}")
                result['seo_analysis'] = "Error generating SEO analysis."
        except Exception as e:
            print(f"Error calling Gemini API for result {i+1}: {str(e)}")
            result['seo_analysis'] = f"Error generating SEO analysis: {str(e)}"
    
    return serp_data

def create_seo_comparative_analysis(serp_data):
    """
    Create a detailed comparative SEO analysis of all results and recommendations for outranking them.
    
    Args:
        serp_data (dict): The SERP analysis data with SEO analysis
        
    Returns:
        str: Detailed comparative SEO analysis markdown
    """
    # Using API key from api_config
    API_URL = GEMINI_API_URL
    
    query = serp_data.get('query', '')
    results = serp_data.get('results', [])
    
    print(f"Creating comparative SEO analysis for query: {query}")
    
    # Extract keywords from the query for analysis
    query_keywords = [kw.strip().lower() for kw in query.split()]
    
    # Create a summary of all results with keyword metrics
    results_summary = []
    for i, result in enumerate(results[:10]):
        # Calculate keyword usage metrics
        title_text = result.get('title', '').lower()
        description_text = result.get('description', '').lower()
        main_content = result.get('main_content', '').lower()
        
        # Count keyword occurrences
        keyword_counts = {}
        keyword_density = {}
        
        for keyword in query_keywords:
            # Count in title
            title_count = title_text.count(keyword)
            
            # Count in description
            description_count = description_text.count(keyword)
            
            # Count in main content
            content_count = main_content.count(keyword) if main_content else 0
            
            # Total count
            total_count = title_count + description_count + content_count
            
            # Calculate density (percentage of total words)
            word_count = result.get('word_count', 0)
            density = (total_count / word_count * 100) if word_count > 0 else 0
            
            keyword_counts[keyword] = {
                'title': title_count,
                'description': description_count,
                'content': content_count,
                'total': total_count
            }
            
            keyword_density[keyword] = round(density, 2)
        
        result_summary = {
            "position": i + 1,
            "title": result.get('title', ''),
            "url": result.get('url', ''),
            "word_count": result.get('word_count', 0),
            "internal_links_count": result.get('internal_links_count', 0),
            "external_links_count": result.get('external_links_count', 0),
            "images_count": result.get('images_count', 0),
            "h1_count": result.get('h1_count', 0),
            "h2_count": result.get('h2_count', 0),
            "h3_count": result.get('h3_count', 0),
            "schema_count": result.get('schema_count', 0),
            "keyword_counts": keyword_counts,
            "keyword_density": keyword_density,
            "unique_facts_count": len(result.get('unique_facts', []))
        }
        results_summary.append(result_summary)
    
    # Prepare the prompt for Gemini
    prompt = f"""
You are an expert SEO analyst. Analyze the following search results and provide a detailed comparative analysis with actionable recommendations for outranking these competitors.

{json.dumps(results_summary, indent=2)}

Provide a comprehensive comparative SEO analysis covering:

1. Overview of the Top Results
   - Common patterns in titles, meta descriptions, and content length
   - Typical header structure patterns
   - Link and image usage patterns

2. Detailed Comparison
   - Title tag strategies across results
   - Meta description effectiveness
   - Content length and depth comparison
   - Header structure comparison
   - Internal and external linking strategies
   - Image usage comparison

3. Content Gap Analysis
   - Topics covered by multiple top results
   - Unique topics covered by individual results
   - Important topics that might be missing from some results

4. Ranking Factor Analysis
   - Key factors likely influencing the ranking order
   - Correlation between specific SEO elements and ranking position

5. Comprehensive Strategy to Outrank Competitors
   - Content recommendations (topics, length, depth)
   - On-page SEO recommendations
   - Technical SEO considerations
   - Link building strategy
   - User experience improvements

Format your response in Markdown with clear headings, bullet points, and where appropriate, tables for comparison.
"""

    # Prepare the request payload
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    # Make the API request
    try:
        response = requests.post(API_URL, json=payload)
        response_json = response.json()
        
        if 'candidates' in response_json and len(response_json['candidates']) > 0:
            comparative_analysis = response_json['candidates'][0]['content']['parts'][0]['text']
            serp_data['comparative_seo_analysis'] = comparative_analysis
            print("Comparative SEO analysis completed")
            return comparative_analysis
        else:
            print(f"Error in API response: {response_json}")
            serp_data['comparative_seo_analysis'] = "Error generating comparative SEO analysis."
            return "Error generating comparative SEO analysis."
    except Exception as e:
        print(f"Error calling Gemini API: {str(e)}")
        serp_data['comparative_seo_analysis'] = f"Error generating comparative SEO analysis: {str(e)}"
        return f"Error generating comparative SEO analysis: {str(e)}"

def analyze_companies_with_gemini(serp_data):
    """
    Use Gemini API to perform a comprehensive analysis of each company in the SERP data.
    
    Args:
        serp_data (dict): The SERP analysis data
        
    Returns:
        dict: The SERP data with added company analysis
    """
    # Using API key from api_config
    API_URL = GEMINI_API_URL
    
    print(f"Performing company analysis for {len(serp_data['results'])} results...")
    
    for i, result in enumerate(serp_data['results']):
        print(f"Analyzing company {i+1}/{len(serp_data['results'])}: {result['title']}")
        
        # Extract company data to analyze
        company_data = {
            "title": result.get('title', ''),
            "url": result.get('url', ''),
            "snippet": result.get('snippet', ''),
            "meta_description": result.get('meta_description', ''),
            "content_sample": result.get('content_sample', '')[:5000] if result.get('content_sample') else ''
        }
        
        # Prepare the prompt for Gemini
        prompt = f"""
You are an expert business analyst. Analyze the following company data and provide a detailed business analysis.

Company Information:
- Company Name/Title: {company_data['title']}
- Website: {company_data['url']}
- Description: {company_data['snippet']}
- Meta Description: {company_data['meta_description']}

Content Sample:
{company_data['content_sample'][:2000] if company_data['content_sample'] else 'No content sample available.'}

Provide a comprehensive business analysis covering:
1. Company Overview
2. Products/Services Offered
3. Target Market and Audience
4. Unique Value Proposition
5. Marketing Strategy
6. Competitive Positioning
7. Strengths and Weaknesses
8. Opportunities and Threats
9. Recommendations for Improvement

Format your response in Markdown with clear headings and bullet points.
"""

        # Prepare the request payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        # Make the API request
        try:
            response = requests.post(API_URL, json=payload)
            response_json = response.json()
            
            if 'candidates' in response_json and len(response_json['candidates']) > 0:
                company_analysis = response_json['candidates'][0]['content']['parts'][0]['text']
                result['company_analysis'] = company_analysis
                print(f"Company analysis completed for result {i+1}")
            else:
                print(f"Error in API response for result {i+1}: {response_json}")
                result['company_analysis'] = "Error generating company analysis."
        except Exception as e:
            print(f"Error calling Gemini API for result {i+1}: {str(e)}")
            result['company_analysis'] = f"Error generating company analysis: {str(e)}"
    
    return serp_data

def clean_all_directories():
    """
    Clean all files in the analysis directory
    """
    try:
        analysis_dir = os.path.join(os.getcwd(), 'analysis')
        if os.path.exists(analysis_dir):
            for file in os.listdir(analysis_dir):
                file_path = os.path.join(analysis_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        print(f"Deleted {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        
        results_dir = os.path.join(os.getcwd(), 'results')
        if os.path.exists(results_dir):
            for file in os.listdir(results_dir):
                file_path = os.path.join(results_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        print(f"Deleted {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        
        print("All directories cleaned successfully!")
    except Exception as e:
        print(f"Error cleaning directories: {e}")

def main():
    parser = argparse.ArgumentParser(description='SEO Analyzer')
    parser.add_argument('--input', type=str, help='Path to SERP results JSON file')
    parser.add_argument('--output_dir', type=str, default='analysis', help='Directory to save analysis files')
    parser.add_argument('--clean', action='store_true', help='Clean all files in the analysis directory')
    parser.add_argument('--query', type=str, help='Search query to analyze')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    if args.clean:
        clean_all_directories()
        return
    
    try:
        # Load SERP data
        if args.input:
            print(f"Loading SERP data from {args.input}...")
            with open(args.input, 'r', encoding='utf-8') as f:
                serp_data = json.load(f)
        else:
            print("No input file specified. Please provide a SERP results JSON file.")
            return
        
        # Get query from arguments or SERP data
        query = args.query or serp_data.get('query', 'Unknown Query')
        
        # Sanitize query for filenames
        sanitized_query = ''.join(c if c.isalnum() or c == '_' else '_' for c in query)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract unique facts from each result's content
        print("Extracting unique facts from search results...")
        serp_data_with_facts = extract_facts_from_serp_data(serp_data)
        
        # Analyze companies if query contains company-related keywords
        is_company_query = any(keyword in query.lower() for keyword in ['company', 'business', 'corporation', 'inc', 'llc', 'enterprise'])
        
        if is_company_query:
            print("Detected company-related query. Performing company analysis...")
            serp_data_with_analysis = analyze_companies_with_gemini(serp_data_with_facts)
        else:
            # Perform SEO analysis
            print("Performing SEO analysis...")
            serp_data_with_analysis = analyze_seo_with_gemini(serp_data_with_facts)
        
        # Create comparative SEO analysis with keyword usage metrics
        print("Creating comparative SEO analysis with keyword metrics...")
        comparative_seo_analysis = create_seo_comparative_analysis(serp_data_with_analysis)
        
        # Save the complete analysis to a JSON file
        output_file = os.path.join(args.output_dir, f"analysis_{sanitized_query}_{timestamp}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serp_data_with_analysis, f, indent=2, ensure_ascii=False)
        
        print(f"\nFull analysis complete! Results saved to {output_file}")
        
        # Save a markdown file with just the comparative analysis
        try:
            comparative_md_file = os.path.join(args.output_dir, f"comparative_analysis_{sanitized_query}_{timestamp}.md")
            with open(comparative_md_file, 'w', encoding='utf-8') as f:
                industry_type = "Companies" if "company" in query.lower() else "Websites"
                f.write(f"# Comparative Analysis of {query.title()} {industry_type}\n\n")
                f.write(f"Query: {query}\n\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(serp_data_with_analysis.get('comparative_analysis', 'No comparative analysis available.'))
            
            print(f"Comparative analysis saved to {comparative_md_file}")
        except Exception as e:
            print(f"Error saving comparative analysis: {e}")
            
        # Save a markdown file with the detailed comparative SEO analysis
        try:
            comparative_seo_md_file = os.path.join(args.output_dir, f"seo_comparative_analysis_{sanitized_query}_{timestamp}.md")
            with open(comparative_seo_md_file, 'w', encoding='utf-8') as f:
                f.write(f"# Detailed SEO Comparative Analysis for '{query}'\n\n")
                f.write(f"Query: {query}\n\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(serp_data_with_analysis.get('comparative_seo_analysis', 'No comparative SEO analysis available.'))
            
            print(f"Detailed SEO comparative analysis saved to {comparative_seo_md_file}")
        except Exception as e:
            print(f"Error saving SEO comparative analysis: {e}")
        
        # Save individual analyses to separate markdown files
        for i, result in enumerate(serp_data_with_analysis['results']):
            try:
                # Create a safe filename from the title
                title = result.get('title', f'Result_{i+1}')
                safe_title = ''.join(c if c.isalnum() or c == '_' else '_' for c in title.split(' - ')[0])[:50]
                
                # Save company analysis
                if 'company_analysis' in result:
                    company_md_file = os.path.join(args.output_dir, f"company_analysis_{safe_title}_{timestamp}.md")
                    with open(company_md_file, 'w', encoding='utf-8') as f:
                        f.write(f"# Business Analysis of {title}\n\n")
                        f.write(f"URL: {result.get('url', 'No URL')}\n\n")
                        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        f.write(result.get('company_analysis', 'No company analysis available.'))
                    
                    print(f"Company analysis saved for result {i+1}: {safe_title}")
                
                # Save SEO analysis
                if 'seo_analysis' in result:
                    seo_md_file = os.path.join(args.output_dir, f"seo_analysis_{safe_title}_{timestamp}.md")
                    with open(seo_md_file, 'w', encoding='utf-8') as f:
                        f.write(f"# SEO Analysis of {title}\n\n")
                        f.write(f"URL: {result.get('url', 'No URL')}\n\n")
                        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        f.write(result.get('seo_analysis', 'No SEO analysis available.'))
                    
                    print(f"SEO analysis saved for result {i+1}: {safe_title}")
            except Exception as e:
                print(f"Error saving analysis for result {i+1}: {e}")
        
        print("\nAll analyses completed and saved successfully!")
        
    except Exception as e:
        print(f"\nError in main execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
