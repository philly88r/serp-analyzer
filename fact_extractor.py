import os
import json
import logging
import re
from api_config import GEMINI_API_KEY, GEMINI_API_URL
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_unique_facts(content, query, num_facts=6):
    """
    Extract unique, factual information from content using Gemini API.
    
    Args:
        content (str): The content to extract facts from
        query (str): The search query for context
        num_facts (int): Number of facts to extract
        
    Returns:
        list: List of extracted facts
    """
    # Truncate content if too long (Gemini has token limits)
    max_content_length = 15000
    if len(content) > max_content_length:
        # Try to truncate at sentence boundaries
        truncated_content = content[:max_content_length]
        last_period = truncated_content.rfind('.')
        if last_period > max_content_length * 0.8:  # Only truncate at sentence if we're not losing too much
            truncated_content = truncated_content[:last_period+1]
        content = truncated_content
    
    # Prepare the prompt for Gemini
    prompt = f"""
You are an expert fact extractor for SEO content creation. Extract {num_facts} unique, factual statements from the following content related to the query: "{query}".

Focus on extracting facts that:
1. Are specific, accurate, and verifiable
2. Demonstrate expertise, experience, authoritativeness, and trustworthiness (E-E-A-T)
3. Would be valuable for creating high-quality content on this topic
4. Include statistics, data points, or expert insights when available
5. Are diverse and cover different aspects of the topic

For each fact, provide:
1. The fact itself (1-2 sentences)
2. A confidence score (1-10) based on how clearly stated and reliable the fact appears to be

CONTENT:
{content}

FORMAT YOUR RESPONSE AS JSON:
[
  {{
    "fact": "The specific factual statement",
    "confidence": 8
  }},
  ...
]
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
                "temperature": 0.2,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        if GEMINI_API_KEY:
            url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        else:
            logger.error("No Gemini API key found")
            return []
            
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            logger.error(f"Error calling Gemini API: {response.status_code} - {response.text}")
            return []
            
        response_json = response.json()
        
        # Extract the generated text
        if 'candidates' in response_json and len(response_json['candidates']) > 0:
            generated_text = response_json['candidates'][0]['content']['parts'][0]['text']
            
            # Try to extract JSON from the response
            try:
                # Find JSON array in the response
                json_match = re.search(r'\[\s*\{.*\}\s*\]', generated_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    facts = json.loads(json_str)
                    
                    # Filter facts by confidence score
                    facts = [f for f in facts if f.get('confidence', 0) >= 6]
                    
                    # Limit to requested number
                    return facts[:num_facts]
                else:
                    logger.warning("Could not find JSON array in Gemini response")
                    return []
            except json.JSONDecodeError:
                logger.warning("Could not parse JSON from Gemini response")
                return []
        else:
            logger.warning("Unexpected response format from Gemini API")
            return []
            
    except Exception as e:
        logger.error(f"Error extracting facts: {str(e)}")
        return []

def extract_facts_from_serp_data(serp_data, min_facts_per_result=3, max_facts_per_result=6):
    """
    Extract facts from all results in SERP data.
    
    Args:
        serp_data (dict): The SERP analysis data
        min_facts_per_result (int): Minimum facts to extract per result
        max_facts_per_result (int): Maximum facts to extract per result
        
    Returns:
        dict: The SERP data with added facts
    """
    query = serp_data.get('query', '')
    results = serp_data.get('results', [])
    
    print(f"Extracting facts for {len(results)} results...")
    
    all_facts = []
    
    for i, result in enumerate(results):
        print(f"Extracting facts from result {i+1}/{len(results)}: {result.get('title', '')}")
        
        # Get content to analyze - prefer main_content if available
        content = result.get('main_content', '')
        if not content:
            # Fall back to description if main_content not available
            content = result.get('description', '')
            
        if not content:
            print(f"No content available for result {i+1}")
            result['unique_facts'] = []
            continue
            
        # Extract facts
        facts = extract_unique_facts(content, query, max_facts_per_result)
        
        # Store facts in result
        result['unique_facts'] = facts
        
        # Add to all facts collection
        all_facts.extend(facts)
        
        print(f"Extracted {len(facts)} facts from result {i+1}")
    
    # Deduplicate all facts by comparing similarity
    # This is a simple approach - in production, you might use embeddings for better deduplication
    unique_facts = []
    for fact in all_facts:
        is_duplicate = False
        for unique_fact in unique_facts:
            # Simple string similarity check
            if similarity_score(fact['fact'], unique_fact['fact']) > 0.7:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_facts.append(fact)
    
    # Add all unique facts to SERP data
    serp_data['all_unique_facts'] = unique_facts
    
    print(f"Total unique facts extracted: {len(unique_facts)}")
    
    return serp_data

def similarity_score(str1, str2):
    """
    Calculate a simple similarity score between two strings.
    This is a basic implementation - for production use, consider using more sophisticated
    methods like cosine similarity with embeddings.
    
    Args:
        str1 (str): First string
        str2 (str): Second string
        
    Returns:
        float: Similarity score between 0 and 1
    """
    # Convert to lowercase and split into words
    words1 = set(str1.lower().split())
    words2 = set(str2.lower().split())
    
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0

if __name__ == "__main__":
    # Test the fact extractor
    test_content = """
    Search engine optimization (SEO) is the process of improving the quality and quantity of website traffic to a website or a web page from search engines. SEO targets unpaid traffic (known as "natural" or "organic" results) rather than direct traffic or paid traffic. Unpaid traffic may originate from different kinds of searches, including image search, video search, academic search, news search, and industry-specific vertical search engines.

    As an Internet marketing strategy, SEO considers how search engines work, the computer-programmed algorithms that dictate search engine behavior, what people search for, the actual search terms or keywords typed into search engines, and which search engines are preferred by their targeted audience. SEO is performed because a website will receive more visitors from a search engine when websites rank higher on the search engine results page (SERP). These visitors can then potentially be converted into customers.
    """
    
    facts = extract_unique_facts(test_content, "SEO optimization", 3)
    print(json.dumps(facts, indent=2))
