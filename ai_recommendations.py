import os
import json
import logging
import requests
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def get_gemini_api_key():
    """Get the Gemini API key from environment variable or config file."""
    if GEMINI_API_KEY:
        return GEMINI_API_KEY
    
    # Try to read from config file if not in environment
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get('gemini_api_key')
    except Exception as e:
        logger.error(f"Error reading config file: {str(e)}")
    
    return None

def generate_content_with_gemini(prompt, api_key=None):
    """Generate content using the Gemini API."""
    if not api_key:
        api_key = get_gemini_api_key()
    
    if not api_key:
        logger.error("No Gemini API key found")
        return None
    
    try:
        url = f"{GEMINI_API_URL}?key={api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
                "stopSequences": []
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract the generated text from the response
        if "candidates" in result and len(result["candidates"]) > 0:
            candidate = result["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    return parts[0]["text"]
        
        logger.error(f"Unexpected response format: {result}")
        return None
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error processing Gemini API response: {str(e)}")
        return None

def generate_seo_recommendations(page_data, competitor_data=None):
    """Generate SEO recommendations based on page analysis and competitor data."""
    prompt = f"""
    As an SEO expert, analyze this webpage data and provide actionable recommendations:
    
    PAGE DATA:
    {json.dumps(page_data, indent=2)}
    
    {"COMPETITOR DATA:" + json.dumps(competitor_data, indent=2) if competitor_data else ""}
    
    Please provide recommendations in the following JSON format:
    {{
      "recommendations": [
        {{
          "type": "content", // can be content, technical, keyword, etc.
          "recommendation": "Detailed recommendation text",
          "impact_score": 8.5, // 0-10 score of estimated impact
          "difficulty": "medium" // easy, medium, or hard
        }},
        // more recommendations...
      ]
    }}
    
    Focus on the most impactful recommendations first. Provide specific, actionable advice.
    """
    
    response = generate_content_with_gemini(prompt)
    
    if not response:
        logger.error("Failed to generate SEO recommendations")
        return None
    
    # Extract JSON from response
    try:
        # Find JSON in the response (it might be surrounded by markdown code blocks)
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            recommendations = json.loads(json_str)
            return recommendations
        else:
            logger.error("No valid JSON found in response")
            return None
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON from response: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error processing recommendations: {str(e)}")
        return None

def generate_competitor_gap_analysis(target_data, competitor_data):
    """Generate gap analysis between target page and competitor page."""
    prompt = f"""
    As an SEO expert, perform a gap analysis between the target page and competitor page:
    
    TARGET PAGE DATA:
    {json.dumps(target_data, indent=2)}
    
    COMPETITOR PAGE DATA:
    {json.dumps(competitor_data, indent=2)}
    
    Please provide a gap analysis in the following JSON format:
    {{
      "gap_score": 7.2, // 0-10 score of overall gap (higher means bigger gap)
      "content_gap": {{
        "score": 6.8,
        "missing_topics": ["topic1", "topic2"],
        "word_count_difference": 450,
        "recommendations": ["recommendation1", "recommendation2"]
      }},
      "keyword_gap": {{
        "score": 7.5,
        "missing_keywords": ["keyword1", "keyword2"],
        "keyword_density_issues": ["issue1", "issue2"],
        "recommendations": ["recommendation1", "recommendation2"]
      }},
      "technical_gap": {{
        "score": 5.4,
        "missing_elements": ["element1", "element2"],
        "performance_issues": ["issue1", "issue2"],
        "recommendations": ["recommendation1", "recommendation2"]
      }}
    }}
    
    Provide specific, actionable insights based on the data.
    """
    
    response = generate_content_with_gemini(prompt)
    
    if not response:
        logger.error("Failed to generate competitor gap analysis")
        return None
    
    # Extract JSON from response
    try:
        # Find JSON in the response (it might be surrounded by markdown code blocks)
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            gap_analysis = json.loads(json_str)
            return gap_analysis
        else:
            logger.error("No valid JSON found in response")
            return None
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON from response: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error processing gap analysis: {str(e)}")
        return None

def prioritize_recommendations(recommendations):
    """Prioritize recommendations based on impact score and difficulty."""
    if not recommendations or "recommendations" not in recommendations:
        return []
    
    # Sort by impact score (descending) and then by difficulty (easy first)
    difficulty_weights = {"easy": 1, "medium": 2, "hard": 3}
    
    sorted_recommendations = sorted(
        recommendations["recommendations"],
        key=lambda x: (-x["impact_score"], difficulty_weights.get(x["difficulty"].lower(), 2))
    )
    
    return sorted_recommendations
