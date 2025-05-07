import asyncio
import subprocess
import sys
import os

async def test_crawl4ai():
    """
    Simple test to verify Crawl4AI installation works correctly.
    """
    try:
        from crawl4ai import AsyncWebCrawler
        
        print("✅ Crawl4AI imported successfully")
        
        async with AsyncWebCrawler() as crawler:
            print("Testing basic crawl on example.com...")
            result = await crawler.arun("https://example.com")
            
            if result.success:
                print("✅ Basic crawl test successful")
                print("\nSample of extracted content (first 300 chars):")
                print("-" * 50)
                print(result.markdown[:300])
                print("-" * 50)
                return True
            else:
                print(f"❌ Crawl test failed: {result.error_message}")
                return False
    except ImportError:
        print("❌ Crawl4AI not installed properly")
        return False
    except Exception as e:
        print(f"❌ Error testing Crawl4AI: {str(e)}")
        return False

def install_crawl4ai():
    """
    Install Crawl4AI and run setup.
    """
    try:
        print("Installing Crawl4AI...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "crawl4ai"])
        
        print("\nRunning Crawl4AI setup...")
        subprocess.check_call(["crawl4ai-setup"])
        
        print("\nRunning Crawl4AI diagnostic tool...")
        subprocess.check_call(["crawl4ai-doctor"])
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during installation: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

async def main():
    print("=" * 60)
    print("Crawl4AI Setup and Test")
    print("=" * 60)
    
    # Check if Crawl4AI is already installed
    try:
        import crawl4ai
        print(f"✅ Crawl4AI is already installed (version: {crawl4ai.__version__})")
    except ImportError:
        print("Crawl4AI not found. Installing...")
        if not install_crawl4ai():
            print("Failed to install Crawl4AI. Please try manually:")
            print("pip install crawl4ai")
            print("crawl4ai-setup")
            return
    
    # Test Crawl4AI
    print("\nTesting Crawl4AI installation...")
    test_success = await test_crawl4ai()
    
    if test_success:
        print("\n✅ Crawl4AI is working correctly!")
        print("\nYou can now run the SERP analyzer with:")
        print("python serp_analyzer.py")
    else:
        print("\n❌ Crawl4AI test failed. Please check the errors above.")
    
    print("\nFor more information, see the README.md file.")

if __name__ == "__main__":
    asyncio.run(main())
