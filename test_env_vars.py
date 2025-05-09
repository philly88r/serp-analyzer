import os
import sys

# Try to import from oxylabs_config first
try:
    from oxylabs_config import (
        OXYLABS_USERNAME, 
        OXYLABS_PASSWORD, 
        PROXY_URL, 
        SERP_API_URL,
        PROXY_TYPE,
        COUNTRY
    )
    print("Successfully imported from oxylabs_config.py")
    print(f"OXYLABS_USERNAME: {OXYLABS_USERNAME}")
    print(f"PROXY_URL: {PROXY_URL}")
    print(f"PROXY_TYPE: {PROXY_TYPE}")
    print(f"COUNTRY: {COUNTRY}")
    print("Oxylabs configuration from file is available")
except (ImportError, AttributeError):
    # Try to get configuration from environment variables
    print("Failed to import from oxylabs_config.py, trying environment variables")
    OXYLABS_USERNAME = os.environ.get('OXYLABS_USERNAME')
    OXYLABS_PASSWORD = os.environ.get('OXYLABS_PASSWORD')
    PROXY_URL = os.environ.get('PROXY_URL')
    SERP_API_URL = os.environ.get('SERP_API_URL')
    PROXY_TYPE = os.environ.get('PROXY_TYPE')
    COUNTRY = os.environ.get('COUNTRY')
    
    print(f"OXYLABS_USERNAME from env: {OXYLABS_USERNAME}")
    print(f"PROXY_URL from env: {PROXY_URL}")
    print(f"PROXY_TYPE from env: {PROXY_TYPE}")
    print(f"COUNTRY from env: {COUNTRY}")
    
    # Check if all required variables are set
    if all([OXYLABS_USERNAME, OXYLABS_PASSWORD, PROXY_URL, SERP_API_URL, PROXY_TYPE, COUNTRY]):
        print("All Oxylabs environment variables are set correctly")
    else:
        print("Some Oxylabs environment variables are missing:")
        if not OXYLABS_USERNAME: print("- OXYLABS_USERNAME is missing")
        if not OXYLABS_PASSWORD: print("- OXYLABS_PASSWORD is missing")
        if not PROXY_URL: print("- PROXY_URL is missing")
        if not SERP_API_URL: print("- SERP_API_URL is missing")
        if not PROXY_TYPE: print("- PROXY_TYPE is missing")
        if not COUNTRY: print("- COUNTRY is missing")

print("\nAll environment variables related to Oxylabs or Playwright:")
for key, value in os.environ.items():
    if "OXYLABS" in key or "PROXY" in key or "PLAYWRIGHT" in key or "RENDER" in key:
        if "PASSWORD" in key:
            print(f"{key}: [REDACTED]")
        else:
            print(f"{key}: {value}")
