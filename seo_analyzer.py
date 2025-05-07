import json
import requests
import argparse
import os
from datetime import datetime

def analyze_seo_with_gemini(serp_data):
    """
    Use Gemini API to perform a comprehensive SEO analysis of each page in the SERP data.
    
    Args:
        serp_data (dict): The SERP analysis data
        
    Returns:
        dict: The SERP data with added SEO analysis
    """
    GEMINI_API_KEY = "AIzaSyBl6LgSol_l_ELLHhd5YX90VeXEwdt3xPU"
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
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
        if seo_data['schema_count'] > 0:
            schema_analysis = f"\n\nSchema Markup: {seo_data['schema_count']} schema(s) detected"
        else:
            schema_analysis = "\n\nSchema Markup: No schema detected"
        
        # Create a detailed prompt for Gemini
        prompt = f"""
        Perform a comprehensive SEO analysis of the following webpage data:
        
        URL: {seo_data['url']}
        Title: {seo_data['title']}
        Meta Description: {seo_data['meta_description']}
        Meta Keywords: {seo_data['meta_keywords']}
        
        Heading Structure:
        H1 Tags ({seo_data['h1_count']}): {', '.join(seo_data['h1_tags']) if seo_data['h1_tags'] else 'None'}
        H2 Tags ({seo_data['h2_count']}): {', '.join(seo_data['h2_tags'][:5]) if seo_data['h2_tags'] else 'None'}{' (more...)' if len(seo_data['h2_tags']) > 5 else ''}
        H3 Tags ({seo_data['h3_count']}): {', '.join(seo_data['h3_tags'][:5]) if seo_data['h3_tags'] else 'None'}{' (more...)' if len(seo_data['h3_tags']) > 5 else ''}
        H4 Tags: {seo_data['h4_count']}
        H5 Tags: {seo_data['h5_count']}
        H6 Tags: {seo_data['h6_count']}
        
        Content Stats:
        Word Count: {seo_data['word_count']}
        Main Keyword: {seo_data['keyword']}
        Keyword Count: {seo_data['keyword_count']}
        Keyword Density: {seo_data['keyword_density']:.2f}%
        
        Link Structure:
        Internal Links: {seo_data['internal_links_count']}
        External Links: {seo_data['external_links_count']}
        {internal_link_analysis}
        {external_link_analysis}
        
        Image Optimization:
        Total Images: {seo_data['images_count']}
        Images with Alt Text: {seo_data['images_with_alt_count']}
        Alt Text Ratio: {(seo_data['images_with_alt_count'] / seo_data['images_count'] * 100) if seo_data['images_count'] > 0 else 0:.2f}%
        
        {schema_analysis}
        
        Provide a detailed SEO analysis that includes:
        1. Title tag analysis (length, keyword usage, effectiveness)
        2. Meta description analysis (length, persuasiveness, keyword usage)
        3. URL structure analysis
        4. Heading structure analysis (H1, H2, H3 usage, hierarchy)
        5. Content analysis (length, readability, keyword density, topical relevance)
        6. Internal linking analysis (count, anchor text quality, site structure)
        7. External linking analysis (authority, relevance, nofollow usage)
        8. Image optimization analysis (alt text usage, size, relevance)
        9. Schema markup analysis (if present, type and completeness)
        10. Customer intent analysis (what user needs does this page address)
        11. Overall SEO score (out of 100)
        12. Specific recommendations for improvement
        
        Format your response as a well-structured markdown document with clear sections.
        """
        
        # Call Gemini API
        payload = {
            "contents": [{
                "parts":[{"text": prompt}]
            }]
        }
        
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                api_response = response.json()
                if 'candidates' in api_response and len(api_response['candidates']) > 0:
                    seo_analysis = api_response['candidates'][0]['content']['parts'][0]['text']
                    # Add the SEO analysis to the result
                    result['seo_analysis'] = seo_analysis
                else:
                    result['seo_analysis'] = "Could not generate SEO analysis."
            else:
                result['seo_analysis'] = f"API Error: {response.status_code}"
        except Exception as e:
            result['seo_analysis'] = f"Error calling Gemini API: {str(e)}"
    
    return serp_data

def create_seo_comparative_analysis(serp_data):
    """
    Create a detailed comparative SEO analysis of all results and recommendations for outranking them.
    
    Args:
        serp_data (dict): The SERP analysis data with SEO analysis
        
    Returns:
        str: Detailed comparative SEO analysis markdown
    """
    GEMINI_API_KEY = "AIzaSyBl6LgSol_l_ELLHhd5YX90VeXEwdt3xPU"
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    print("Creating detailed comparative SEO analysis...")
    
    # Extract SEO data for comparison
    seo_comparison_data = []
    for result in serp_data['results']:
        seo_metrics = {
            "position": serp_data['results'].index(result) + 1,
            "title": result.get('title', ''),
            "url": result.get('url', ''),
            "title_length": len(result.get('title', '')),
            "meta_description": result.get('meta_description', ''),
            "meta_description_length": len(result.get('meta_description', '')),
            "word_count": result.get('word_count', 0),
            "h1_count": result.get('h1_count', 0),
            "h2_count": result.get('h2_count', 0),
            "h3_count": result.get('h3_count', 0),
            "internal_links_count": result.get('internal_links_count', 0),
            "external_links_count": result.get('external_links_count', 0),
            "images_count": result.get('images_count', 0),
            "images_with_alt_count": result.get('images_with_alt_count', 0),
            "schema_count": result.get('schema_count', 0),
            "keyword": result.get('keyword', ''),
            "keyword_density": result.get('keyword_density', 0)
        }
        seo_comparison_data.append(seo_metrics)
    
    # Create a detailed comparative SEO analysis prompt
    comparative_seo_prompt = f"""
    Perform a detailed comparative SEO analysis of the following search results:
    
    {json.dumps(seo_comparison_data, indent=2)}
    
    Provide a comprehensive comparative SEO analysis that includes:
    
    1. Executive Summary: Overall SEO landscape of these results
    
    2. Detailed Comparison by SEO Factor:
       - Title tag optimization (length, keyword usage, effectiveness)
       - Meta description optimization (length, persuasiveness, CTR potential)
       - URL structure (cleanliness, keyword usage, user-friendliness)
       - Content depth and quality (word count, comprehensiveness)
       - Heading structure (H1, H2, H3 usage and hierarchy)
       - Internal linking (quantity and likely quality)
       - External linking (quantity and likely authority)
       - Image optimization (quantity and alt text usage)
       - Schema implementation (presence and likely completeness)
       - Keyword optimization (density and likely relevance)
    
    3. Competitive Gap Analysis: Identify what the top-ranking pages are doing that lower-ranking pages are not
    
    4. Strategic Recommendations: Detailed, specific recommendations for creating a new page that would outrank ALL of these competitors, including:
       - Optimal title structure and length
       - Ideal meta description approach
       - URL structure recommendations
       - Content depth and structure (word count, sections to include)
       - Heading hierarchy recommendations
       - Internal and external linking strategy
       - Image optimization approach
       - Schema markup implementation
       - Keyword usage and density targets
       - Additional technical SEO considerations
       - Content quality and E-E-A-T signals to incorporate
    
    5. Competitive Edge Strategy: Specific tactics to differentiate from and outperform these competitors
    
    Format your response as a well-structured markdown document with clear sections, tables for comparisons where appropriate, and actionable recommendations.
    """
    
    # Call Gemini API for comparative SEO analysis
    payload = {
        "contents": [{
            "parts":[{"text": comparative_seo_prompt}]
        }]
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            api_response = response.json()
            if 'candidates' in api_response and len(api_response['candidates']) > 0:
                comparative_seo_analysis = api_response['candidates'][0]['content']['parts'][0]['text']
                return comparative_seo_analysis
            else:
                return "Could not generate comparative SEO analysis."
        else:
            return f"API Error: {response.status_code}"
    except Exception as e:
        return f"Error calling Gemini API: {str(e)}"

def analyze_companies_with_gemini(serp_data):
    """
    Use Gemini API to perform a comprehensive analysis of each company in the SERP data.
    
    Args:
        serp_data (dict): The SERP analysis data
        
    Returns:
        dict: The SERP data with added company analysis
    """
    GEMINI_API_KEY = "AIzaSyBl6LgSol_l_ELLHhd5YX90VeXEwdt3xPU"
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    print(f"Performing company analysis for {len(serp_data['results'])} results...")
    
    # First, create a comparative analysis of all companies
    companies_data = []
    for result in serp_data['results']:
        company_info = {
            "title": result.get('title', ''),
            "url": result.get('url', ''),
            "snippet": result.get('snippet', ''),
            "meta_description": result.get('meta_description', '')
        }
        companies_data.append(company_info)
    
    # Get the query from the SERP data
    query = serp_data.get('query', 'unknown')
    
    # Create a comparative analysis prompt
    comparative_prompt = f"""
    Perform a comparative analysis of the following websites related to "{query}":
    
    {json.dumps(companies_data, indent=2)}
    
    Provide a detailed comparative analysis that includes:
    1. Overview of the market based on these websites
    2. Comparison of their offerings, positioning, and unique selling points
    3. Market positioning analysis
    4. Strengths and weaknesses of each website
    5. Recommendations for a new entrant to this market
    
    Format your response as a well-structured markdown document with clear sections.
    """
    
    # Call Gemini API for comparative analysis
    payload = {
        "contents": [{
            "parts":[{"text": comparative_prompt}]
        }]
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            api_response = response.json()
            if 'candidates' in api_response and len(api_response['candidates']) > 0:
                comparative_analysis = api_response['candidates'][0]['content']['parts'][0]['text']
                # Add the comparative analysis to the SERP data
                serp_data['comparative_analysis'] = comparative_analysis
            else:
                serp_data['comparative_analysis'] = "Could not generate comparative analysis."
        else:
            serp_data['comparative_analysis'] = f"API Error: {response.status_code}"
    except Exception as e:
        serp_data['comparative_analysis'] = f"Error calling Gemini API: {str(e)}"
    
    # Now analyze each company individually
    for i, result in enumerate(serp_data['results']):
        print(f"Analyzing company {i+1}/{len(serp_data['results'])}: {result['title']}")
        
        # Extract company data to analyze
        company_data = {
            "title": result.get('title', ''),
            "url": result.get('url', ''),
            "snippet": result.get('snippet', ''),
            "meta_description": result.get('meta_description', ''),
            "content_preview": result.get('content_text', '')[:1000] if result.get('content_text') else ''
        }
        
        # Create a detailed prompt for Gemini
        prompt = f"""
        Perform a comprehensive business analysis of the following coffee fundraising company:
        
        Company: {company_data['title']}
        URL: {company_data['url']}
        Description: {company_data['snippet']}
        Meta Description: {company_data['meta_description']}
        Content Preview: {company_data['content_preview']}
        
        Provide a detailed business analysis that includes:
        1. Company overview and background
        2. Product offerings and services
        3. Target audience and market positioning
        4. Unique selling proposition (USP)
        5. Marketing strategy analysis
        6. Strengths and weaknesses
        7. Opportunities and threats
        8. Recommendations for improvement
        
        Format your response as a well-structured markdown document with clear sections.
        """
        
        # Call Gemini API
        payload = {
            "contents": [{
                "parts":[{"text": prompt}]
            }]
        }
        
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                api_response = response.json()
                if 'candidates' in api_response and len(api_response['candidates']) > 0:
                    company_analysis = api_response['candidates'][0]['content']['parts'][0]['text']
                    # Add the company analysis to the result
                    result['company_analysis'] = company_analysis
                else:
                    result['company_analysis'] = "Could not generate company analysis."
            else:
                result['company_analysis'] = f"API Error: {response.status_code}"
        except Exception as e:
            result['company_analysis'] = f"Error calling Gemini API: {str(e)}"
    
    return serp_data

def clean_all_directories():
    """
    Clean all files in the analysis directory
    """
    analysis_dir = "analysis"
    
    # Clean analysis directory
    if os.path.exists(analysis_dir):
        print("\n===== CLEANING ANALYSIS DIRECTORY =====")
        print(f"Before cleaning, analysis directory contains {len(os.listdir(analysis_dir))} files")
        for file in os.listdir(analysis_dir):
            file_path = os.path.join(analysis_dir, file)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"Removed file: {file_path}")
                except Exception as e:
                    print(f"Could not remove {file_path}: {e}")
        print(f"After cleaning, analysis directory contains {len(os.listdir(analysis_dir))} files")
    else:
        os.makedirs(analysis_dir, exist_ok=True)
        print("Created analysis directory")
    
    print("===== CLEANING COMPLETE =====")

def main():
    parser = argparse.ArgumentParser(description='Analyze SEO data from SERP results')
    parser.add_argument('input_file', help='Path to the JSON file containing SERP results')
    parser.add_argument('--output_dir', default='analysis', help='Directory to save the analysis results')
    args = parser.parse_args()
    
    try:
        # Clean ALL files in the analysis directory
        clean_all_directories()
        
        # Create output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Load the SERP data
        with open(args.input_file, 'r', encoding='utf-8') as f:
            serp_data = json.load(f)
        
        # Get the query from the SERP data
        query = serp_data.get('query', 'unknown')
        sanitized_query = query.replace(' ', '_')
        
        # Generate timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Perform SEO analysis
        print(f"\nPerforming SEO analysis for {len(serp_data['results'])} results...")
        serp_data_with_seo = analyze_seo_with_gemini(serp_data)
        
        # Save intermediate results in case of later failure
        intermediate_file = os.path.join(args.output_dir, f"seo_analysis_{sanitized_query}_{timestamp}.json")
        with open(intermediate_file, 'w', encoding='utf-8') as f:
            json.dump(serp_data_with_seo, f, indent=2, ensure_ascii=False)
        print(f"\nSEO analysis complete! Intermediate results saved to {intermediate_file}")
        
        # Perform company analysis
        print(f"\nPerforming company analysis for {len(serp_data['results'])} results...")
        serp_data_with_analysis = analyze_companies_with_gemini(serp_data_with_seo)
        
        # Create detailed comparative SEO analysis
        print("\nCreating detailed comparative SEO analysis...")
        comparative_seo_analysis = create_seo_comparative_analysis(serp_data_with_seo)
        serp_data_with_analysis['comparative_seo_analysis'] = comparative_seo_analysis
        
        # Save the final analysis results
        output_file = os.path.join(args.output_dir, f"full_analysis_{sanitized_query}_{timestamp}.json")
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
