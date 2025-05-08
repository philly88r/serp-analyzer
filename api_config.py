import os

# Gemini API Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# Function to check if API keys are configured
def check_api_keys():
    """Check if all required API keys are configured."""
    missing_keys = []
    
    if not GEMINI_API_KEY:
        missing_keys.append("GEMINI_API_KEY")
    
    if missing_keys:
        print(f"Warning: The following API keys are missing: {', '.join(missing_keys)}")
        print("Some functionality may be limited.")
        return False
    
    return True

# Check API keys on import
api_keys_configured = check_api_keys()
