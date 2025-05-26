import os
import sys
import json
import asyncio
import re
import markdown
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, send_from_directory
import generate_seo_blog
# Import serp_analyzer directly instead of serp_analyzer_working
# import serp_analyzer_working
import seo_analyzer
import md_to_html
import glob
import io
import logging
from logging.handlers import RotatingFileHandler

# Configure logging to show DEBUG level messages
log_file = os.path.join(os.path.dirname(__file__), 'serp_analyzer.log')
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
log_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024 * 5, backupCount=2) # 5MB per file, 2 backups
log_handler.setFormatter(log_formatter)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        log_handler
    ]
)
# Ensure third-party loggers don't overwhelm our logs
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('playwright').setLevel(logging.INFO)

# Create a logger for this module
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'seo_analyzer_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['ANALYSIS_FOLDER'] = 'analysis'
app.config['BLOG_FOLDER'] = 'blogs'
app.config['HTML_REPORTS_FOLDER'] = os.path.join(app.root_path, 'html_reports')

# Import and register test routes
try:
    from test_routes import register_test_routes
    app = register_test_routes(app)
    print("Test routes registered successfully in app.py")
except ImportError as e:
    print(f"Warning: Could not import test_routes: {e}")
except Exception as e:
    print(f"Error registering test routes: {e}")


# Create necessary folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
os.makedirs(app.config['ANALYSIS_FOLDER'], exist_ok=True)
os.makedirs(app.config['BLOG_FOLDER'], exist_ok=True)
os.makedirs(app.config['HTML_REPORTS_FOLDER'], exist_ok=True)

# Import SerpAnalyzer conditionally to handle case when browser automation is not available
try:
    # Try to import analyzers in order of preference
    try:
        from bypass_serp import BypassSerpAnalyzer as SerpAnalyzer
        logger.info("Bypass SERP analyzer loaded successfully - using alternative search engines to avoid CAPTCHA")
    except ImportError as e:
        logger.error(f"Could not import BypassSerpAnalyzer: {str(e)}")
        try:
            from improved_serp_analyzer import ImprovedSerpAnalyzer as SerpAnalyzer
            logger.info("Improved SERP analyzer loaded successfully")
        except ImportError as e:
            logger.error(f"Could not import ImprovedSerpAnalyzer: {str(e)}")
            # Fall back to the original analyzer if others are not available
            from serp_analyzer import SerpAnalyzer
            print("Original SERP analyzer loaded as fallback")
    
    import generate_seo_blog
    BROWSER_AUTOMATION_AVAILABLE = True
    print("Browser automation dependencies loaded successfully")
except Exception as e:
    BROWSER_AUTOMATION_AVAILABLE = False
    print(f"Browser automation dependencies not available: {str(e)}. Running in limited mode.")
    
# Try to initialize Playwright if it's available
if BROWSER_AUTOMATION_AVAILABLE:
    try:
        import os
        import subprocess
        from playwright.sync_api import sync_playwright
        
        # Configure Playwright for different environments
        is_heroku = 'DYNO' in os.environ
        is_render = 'RENDER' in os.environ
        
        if is_heroku:
            logger.info("Running on Heroku, configuring Playwright...")
            
            # Set environment variables for Playwright on Heroku
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/app/.playwright'
            os.environ['PLAYWRIGHT_CHROMIUM_ARGS'] = '--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage'
            logger.info(f"Set PLAYWRIGHT_BROWSERS_PATH to {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")
            logger.info(f"Set PLAYWRIGHT_CHROMIUM_ARGS to {os.environ.get('PLAYWRIGHT_CHROMIUM_ARGS')}")
        
        elif is_render:
            logger.info("Running on Render, configuring Playwright...")
            
            # Set environment variables for Playwright on Render
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/opt/render/.playwright'
            os.environ['PLAYWRIGHT_CHROMIUM_ARGS'] = '--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage'
            logger.info(f"Set PLAYWRIGHT_BROWSERS_PATH to {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")
            logger.info(f"Set PLAYWRIGHT_CHROMIUM_ARGS to {os.environ.get('PLAYWRIGHT_CHROMIUM_ARGS')}")
            
            # Log all environment variables related to Playwright for debugging
            logger.info("Environment variables related to Playwright on Render:")
            for key, value in os.environ.items():
                if any(term in key.upper() for term in ['PLAYWRIGHT', 'CHROME', 'BROWSER', 'PROXY']):
                    # Mask sensitive values
                    if any(sensitive in key.lower() for sensitive in ['key', 'secret', 'password', 'token']):
                        value = value[:5] + '...' if value and len(value) > 5 else value
                    logger.info(f"  {key}: {value}")
            
            # Log all environment variables related to Playwright for debugging
            print("Environment variables related to Playwright:")
            for key, value in os.environ.items():
                if "PLAYWRIGHT" in key or "CHROME" in key or "BROWSER" in key:
                    print(f"  {key}: {value}")
            
            try:
                # Try to access the browser without installing
                print("Checking for Playwright browsers...")
                try:
                    with sync_playwright() as p:
                        browser_args = {
                            "chromium_sandbox": False,
                            "executable_path": None,  # Let Playwright find the executable
                            "args": [
                                "--no-sandbox",
                                "--disable-setuid-sandbox",
                                "--disable-dev-shm-usage",
                                "--disable-gpu",
                                "--single-process"
                            ],
                            "ignore_default_args": ["--disable-extensions"],
                            "timeout": 30000  # Increase timeout to 30 seconds
                        }
                        print(f"Launching browser with args: {browser_args}")
                        browser = p.chromium.launch(**browser_args)
                        page = browser.new_page()
                        page.goto("https://example.com")
                        title = page.title()
                        print(f"Successfully loaded page with title: {title}")
                        browser.close()
                        print("Playwright is working correctly!")
                except Exception as browser_error:
                    print(f"Browser test failed, trying to install: {str(browser_error)}")
                    # Try to install Playwright browsers
                    print("Installing Playwright browsers...")
                    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"], check=False)
                    
                    # Test again after installation
                    try:
                        with sync_playwright() as p:
                            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
                            page = browser.new_page()
                            page.goto("https://example.com")
                            title = page.title()
                            print(f"Successfully loaded page with title: {title}")
                            browser.close()
                            print("Playwright is working correctly after installation!")
                    except Exception as retry_error:
                        print(f"Browser still not working after installation: {str(retry_error)}")
                        # Continue anyway with limited functionality
                        print("Continuing with limited functionality")
            except Exception as e:
                print(f"Error setting up Playwright on Heroku: {str(e)}")
                print("Continuing with limited browser automation functionality")
                # Don't set BROWSER_AUTOMATION_AVAILABLE to False here
                # Let the app try to use it and handle failures gracefully
    except Exception as e:
        print(f"Error initializing Playwright: {str(e)}")
        print("Continuing with limited browser automation functionality")
        # Don't set BROWSER_AUTOMATION_AVAILABLE to False here
        # Let the app try to use it and handle failures gracefully

def get_html_report_dir():
    return os.path.join(app.root_path, 'html_reports')

def get_results_dir():
    return os.path.join(app.root_path, 'results')

def get_analysis_dir():
    return os.path.join(app.root_path, 'analysis')

def get_blog_dir():
    return os.path.join(app.root_path, 'blogs')

@app.route('/reports/<path:filename>')
def serve_html_report(filename):
    """Serves the static HTML report files."""
    report_dir = get_html_report_dir()
    # Basic security check to prevent directory traversal
    safe_path = os.path.join(report_dir, filename)
    if not os.path.abspath(safe_path).startswith(os.path.abspath(report_dir)):
        return "Forbidden", 403
    if not os.path.exists(safe_path):
        return "File not found", 404
        
    return send_from_directory(report_dir, filename)

@app.route('/')
def index():
    # Get list of available results
    results = []
    if os.path.exists(app.config['RESULTS_FOLDER']):
        for file in os.listdir(app.config['RESULTS_FOLDER']):
            if file.startswith('serp_') and file.endswith('.json'):
                query = file[5:-5].replace('_', ' ')
                file_path = os.path.join(app.config['RESULTS_FOLDER'], file)
                timestamp = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # Check if analysis exists
                analysis_exists = False
                for analysis_file in os.listdir(app.config['ANALYSIS_FOLDER']):
                    if query.replace(' ', '_') in analysis_file and analysis_file.endswith('.md'):
                        analysis_exists = True
                        break
                
                # Check if blog exists
                blog_exists = False
                blog_file = os.path.join(app.config['BLOG_FOLDER'], f"blog_{query.replace(' ', '_')}.md")
                if os.path.exists(blog_file):
                    blog_exists = True
                
                results.append({
                    'query': query,
                    'file': file,
                    'timestamp': timestamp,
                    'analysis_exists': analysis_exists,
                    'blog_exists': blog_exists
                })
    
    # Sort results by timestamp (newest first)
    results.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('index.html', results=results, browser_automation_available=BROWSER_AUTOMATION_AVAILABLE, current_time=f"App Reloaded: {datetime.now().isoformat()}")

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    num_results = int(request.form.get('num_results', 6))
    
    if not query:
        flash('Please enter a search query', 'danger')
        return redirect(url_for('index'))
    
    try:
        if not BROWSER_AUTOMATION_AVAILABLE:
            flash('Browser automation is not available in this deployment. Some features may be limited.', 'warning')
            # Instead of redirecting, we could potentially use a fallback method or mock data
            # For now, we'll just inform the user and redirect
            return redirect(url_for('index'))
            
        # Create necessary directories
        os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
        
        # Clean up old results for this query
        try:
            # Remove old result files for this query
            query_prefix = f"serp_{query.replace(' ', '_')}"
            for file in glob.glob(os.path.join(app.config['RESULTS_FOLDER'], f"{query_prefix}*.json")):
                try:
                    os.remove(file)
                except Exception as e:
                    print(f"Could not remove file {file}: {str(e)}")
            for file in glob.glob(os.path.join(app.config['RESULTS_FOLDER'], f"{query_prefix}*.csv")):
                try:
                    os.remove(file)
                except Exception as e:
                    print(f"Could not remove file {file}: {str(e)}")
        except Exception as cleanup_error:
            print(f"Warning: Could not clean up old results: {str(cleanup_error)}")
        
        # Create SERP analyzer with Heroku-specific configuration
        try:
            # Check if we're running on Heroku
            is_heroku = 'DYNO' in os.environ
            
            # Configure analyzer with appropriate options for the environment
            analyzer = SerpAnalyzer(headless=True)
            
            # Run search asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                serp_analysis = loop.run_until_complete(analyzer.analyze_serp(query, num_results))
                
                # Validate that we got valid results and not an HTML error page
                if isinstance(serp_analysis, dict) and "results" in serp_analysis:
                    if not serp_analysis["results"] or len(serp_analysis["results"]) == 0:
                        print(f"Warning: No search results found for query: {query}")
                else:
                    raise Exception("Invalid search results format returned")
            except json.JSONDecodeError as json_err:
                print(f"JSON decode error: {str(json_err)}")
                raise Exception(f"Received invalid response format. This might be due to a CAPTCHA or block page.")
            finally:
                loop.close()
            
            # Save results
            analyzer.save_results(serp_analysis, "json")
            analyzer.save_results(serp_analysis, "csv")
            
            flash(f'Successfully analyzed {len(serp_analysis["results"])} search results for "{query}"', 'success')
            return redirect(url_for('view_results', query=query))
        except Exception as browser_error:
            # Log the specific browser error
            print(f"Browser automation error: {str(browser_error)}")
            raise Exception(f"Browser automation error: {str(browser_error)}")
    
    except Exception as e:
        error_message = str(e)
        if "executable doesn't exist" in error_message.lower():
            flash('Browser executable not found. This is a common issue on Heroku. Please check the Playwright configuration.', 'danger')
        else:
            flash(f'Error during search: {error_message}', 'danger')
        return redirect(url_for('index'))

@app.route('/analyze/<query>')
def analyze(query):
    # Replace spaces with underscores for file operations
    query_file = query.replace(' ', '_')
    
    # Check if SERP results exist
    serp_file = os.path.join(app.config['RESULTS_FOLDER'], f'serp_{query_file}.json')
    if not os.path.exists(serp_file):
        flash(f'SERP results for "{query}" not found', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Clean up old analysis files
        seo_analyzer.clean_all_directories()
        
        # Run SEO analysis
        seo_analyzer.main(['--input', serp_file])
        
        # Extract and save HTML content for blog generation
        print(f"Extracting HTML content for blog generation from {serp_file}")
        try:
            # Load SERP results
            with open(serp_file, 'r', encoding='utf-8') as f:
                serp_data = json.load(f)
            
            # Create HTML extraction directory if it doesn't exist
            html_extraction_dir = os.path.join(app.config['ANALYSIS_FOLDER'], f'html_{query_file}')
            os.makedirs(html_extraction_dir, exist_ok=True)
            
            # Extract HTML content from each result
            if 'results' in serp_data and serp_data['results']:
                for i, result in enumerate(serp_data['results']):
                    if 'url' in result:
                        try:
                            # Use the analyze_page function to extract content
                            page_data = analyze_page(result['url'])
                            
                            # Save the extracted content
                            html_file = os.path.join(html_extraction_dir, f'page_{i+1}.json')
                            with open(html_file, 'w', encoding='utf-8') as f:
                                json.dump(page_data, f, indent=2)
                            
                            print(f"Saved HTML content for {result['url']} to {html_file}")
                        except Exception as page_error:
                            print(f"Error extracting HTML from {result['url']}: {str(page_error)}")
                
                print(f"Successfully extracted HTML content from {len(serp_data['results'])} pages")
            else:
                print("No results found in SERP data for HTML extraction")
        except Exception as html_error:
            print(f"Error during HTML extraction: {str(html_error)}")
        
        flash(f'Successfully created SEO analysis for "{query}"', 'success')
        return redirect(url_for('index'))
    
    except Exception as e:
        flash(f'Error during analysis: {str(e)}', 'danger')
        return redirect(url_for('index'))
@app.route('/generate_blog/', methods=['GET'])
@app.route('/generate_blog/<query>', methods=['GET'])
def generate_blog(query=None):
    # Direct file logging to ensure we capture this
    try:
        with open('blog_debug.log', 'a') as f:
            f.write(f"\n\n[{datetime.now()}] ***** generate_blog FUNCTION ENTERED *****\n")
    except Exception as e:
        print(f"Error writing to debug log: {e}")
        
    app.logger.info("***** generate_blog FUNCTION ENTERED *****")
    app.logger.info(f"\n\n==== BLOG GENERATION REQUESTED ====\n")
    app.logger.info(f"Request method: {request.method}")
    app.logger.info(f"Request args: {request.args}")
    app.logger.info(f"Request form: {request.form}")
    app.logger.info(f"Request path: {request.path}")
    app.logger.info(f"Query parameter: {query}")
    
    # Get query from URL params or form submission
    if query is None:
        query = request.args.get('query')
        app.logger.info(f"Query from request args: {query}")
    else:
        app.logger.info(f"Query from URL param: {query}")
    
    if not query:
        flash('No query provided for blog generation.', 'warning')
        app.logger.warning("No query provided, redirecting to index.")
        return redirect(url_for('index'))
    
    query_file = query.replace(' ', '_')
    
    # Ensure all required folders exist
    for folder in [app.config['RESULTS_FOLDER'], app.config['ANALYSIS_FOLDER'], 
                  app.config['BLOG_FOLDER'], app.config['HTML_REPORTS_FOLDER']]:
        os.makedirs(folder, exist_ok=True)
        app.logger.info(f"Ensured directory exists: {folder}")
    
    # Set environment variable for HTML_REPORTS_DIR to ensure generate_seo_blog.py can find it
    os.environ['HTML_REPORTS_DIR'] = app.config['HTML_REPORTS_FOLDER']
    app.logger.info(f"Set HTML_REPORTS_DIR environment variable to: {os.environ['HTML_REPORTS_DIR']}")
    
    # Check if SERP results exist
    serp_file = os.path.join(app.config['RESULTS_FOLDER'], f'serp_{query_file}.json')
    app.logger.info(f"Looking for SERP file at: {serp_file}")
    
    if not os.path.exists(serp_file):
        flash(f'SERP results for "{query}" not found', 'danger')
        app.logger.warning(f"SERP file not found: {serp_file}. Redirecting to index.")
        return redirect(url_for('index'))
    
    try:
        # Generate blog post
        output_file = os.path.join(app.config['BLOG_FOLDER'], f'blog_{query_file}.md')
        app.logger.info(f"Attempting to generate blog for query: '{query}' using SERP file: {serp_file}")
        
        # Set up arguments for generate_seo_blog.main
        html_extraction_dir = os.path.join(app.config['ANALYSIS_FOLDER'], f'html_{query_file}')
        if os.path.exists(html_extraction_dir):
            app.logger.info(f"HTML extraction directory found: {html_extraction_dir}")
        else:
            app.logger.info(f"HTML extraction directory not found: {html_extraction_dir}")
            
        # Call the main generation script with explicit arguments
        blog_result = generate_seo_blog.main(query=query)
        
        if blog_result and 'output_file' in blog_result:
            app.logger.info(f"Blog generation successful. Output file: {blog_result['output_file']}")
            app.logger.info(f"HTML output file: {blog_result.get('html_output_file', 'None')}")
        else:
            app.logger.info("Blog generation completed but no output file information returned")
            
        # Redirect to the index page with a success message
        flash(f'Blog for "{query}" generated successfully!', 'success')
        app.logger.info(f"Redirecting to index with success message for query: '{query}'")
        
        # Use the Memory pattern: Render index with context
        return render_template('index.html',
                               results=get_existing_results_and_blogs(),
                               blog_generated_query=query)  # Pass the query
        
    except Exception as e:
        flash(f'Error generating blog: {str(e)}', 'danger')
        app.logger.error(f"Error during blog generation for query '{query}': {e}", exc_info=True)
        return redirect(url_for('index'))


@app.route('/api/proxy/status', methods=['GET'])
def api_proxy_status():
    """API endpoint to check the status of the proxy system."""
    try:
        from proxy_manager import proxy_manager
        proxy_url = proxy_manager.get_proxy()
        
        if proxy_url:
            # Get the last used timestamp if available
            last_used = None
            
            return jsonify({
                'status': 'active',
                'last_used': last_used,
                'message': 'Proxy system is active and configured.'
            })
        else:
            return jsonify({
                'status': 'inactive',
                'message': 'Proxy system is inactive or not properly configured.'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error checking proxy status: {str(e)}'
        }), 500

@app.route('/api/proxy/test', methods=['GET'])
def api_proxy_test():
    """API endpoint to test the proxy connection."""
    try:
        import requests
        from proxy_manager import proxy_manager
        
        proxy_url = proxy_manager.get_proxy()
        
        if not proxy_url:
            return jsonify({
                'success': False,
                'message': 'No proxy configured.'
            })
        
        # Test the proxy with a simple request to a test site
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # Use a test URL that returns IP information
        response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=10)
        
        if response.status_code == 200:
            ip_data = response.json()
            return jsonify({
                'success': True,
                'message': 'Proxy connection successful',
                'ip_info': ip_data
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Proxy test failed with status code: {response.status_code}'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error testing proxy connection: {str(e)}'
        }), 500

@app.route('/api/results/<query>', methods=['GET'])
def api_get_results(query):
    """API endpoint to get the latest SERP results JSON for a query."""
    query_safe = query.replace(' ', '_')
    results_dir = get_results_dir()
    potential_files = glob.glob(os.path.join(results_dir, f"serp_{query_safe}*.json"))
    
    if not potential_files:
        return jsonify({'error': f'No results found for query: {query}'}), 404
        
    latest_file = max(potential_files, key=os.path.getctime)
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        logging.error(f"Error reading results file {latest_file} for API: {e}")
        return jsonify({'error': 'Could not read results file'}), 500

@app.route('/api/analysis/<query>', methods=['GET'])
def api_get_analysis(query):
    """API endpoint to get the latest analysis Markdown content for a query."""
    query_safe = query.replace(' ', '_')
    analysis_dir = get_analysis_dir()
    potential_files = glob.glob(os.path.join(analysis_dir, f"seo_comparative_analysis_{query_safe}*.md"))
    
    if not potential_files:
        return jsonify({'error': f'No analysis found for query: {query}'}), 404
        
    latest_file = max(potential_files, key=os.path.getctime)
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'query': query, 'analysis_markdown': content})
    except Exception as e:
        logging.error(f"Error reading analysis file {latest_file} for API: {e}")
        return jsonify({'error': 'Could not read analysis file'}), 500

@app.route('/view_blog/', methods=['GET'])
@app.route('/view_blog/<query>', methods=['GET'])
def view_blog(query=None):
    """View the generated blog post for a specific query."""
    # Get query from URL params if not provided in the route
    if query is None:
        query = request.args.get('query')
        
    if not query:
        flash('No query provided for blog viewing.', 'warning')
        return redirect(url_for('index'))
    
    query_safe = query.replace(' ', '_')
    blog_dir = get_blog_dir()
    
    # Look for the blog file
    potential_files = glob.glob(os.path.join(blog_dir, f"blog_{query_safe}.md"))
    
    if not potential_files:
        flash(f'No blog post found for "{query}".', 'warning')
        return redirect(url_for('index'))
    
    # Get the latest blog file
    latest_file = max(potential_files, key=os.path.getctime)
    
    try:
        # Read the blog content
        with open(latest_file, 'r', encoding='utf-8') as f:
            blog_content = f.read()
        
        # Check if there's an HTML version
        html_report_dir = get_html_report_dir()
        html_file = os.path.join(html_report_dir, f"blog_{query_safe}.html")
        html_file_url = None
        
        if os.path.exists(html_file):
            html_file_url = url_for('serve_html_report', filename=f"blog_{query_safe}.html")
        
        # Render the blog template
        return render_template('blog.html', query=query, blog_content=blog_content, html_file=html_file_url)
    
    except Exception as e:
        app.logger.error(f"Error reading blog file {latest_file}: {e}", exc_info=True)
        flash(f'Error reading blog file: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/api/blog/<query>', methods=['GET'])
def api_get_blog(query):
    """API endpoint to get the latest blog Markdown content for a query."""
    query_safe = query.replace(' ', '_')
    blog_dir = get_blog_dir()
    potential_files = glob.glob(os.path.join(blog_dir, f"blog_{query_safe}.md"))
    
    if not potential_files:
        return jsonify({'error': f'No blog post found for query: {query}'}), 404
        
    latest_file = max(potential_files, key=os.path.getctime)
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'query': query, 'blog_markdown': content})
    except Exception as e:
        logging.error(f"Error reading blog file {latest_file} for API: {e}")
        return jsonify({'error': 'Could not read blog file'}), 500

@app.route('/api/analyze/<query>', methods=['POST'])
def api_analyze_query(query):
    """API endpoint to trigger SERP scraping and SEO analysis for a query."""
    # TODO: Consider making this asynchronous in a real-world scenario (e.g., using Celery)
    query_safe = query.replace(' ', '_')
    results_dir = get_results_dir()
    analysis_dir = get_analysis_dir()
    html_report_dir = get_html_report_dir()
    
    # Define file paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_filename = f"serp_results_{query_safe}_{timestamp}.json"
    analysis_filename = f"seo_comparative_analysis_{query_safe}_{timestamp}.md"
    html_report_filename = analysis_filename.replace('.md', '.html')
    results_file_path = os.path.join(results_dir, results_filename)
    analysis_file_path = os.path.join(analysis_dir, analysis_filename)
    html_report_file_path = os.path.join(html_report_dir, html_report_filename)

    try:
        # Step 1: Run SERP Analysis
        logging.info(f"[API] Starting SERP analysis for query: {query}")
        # Create SERP analyzer instance
        analyzer = SerpAnalyzer(headless=True)
        # Run the analysis
        serp_results = asyncio.run(analyzer.analyze_serp(query))
        # Save results
        with open(results_file_path, 'w', encoding='utf-8') as f:
            json.dump(serp_results, f, indent=4)
        logging.info(f"[API] SERP results saved to {results_file_path}")

        # Step 2: Run SEO Comparative Analysis
        logging.info(f"[API] Starting SEO comparative analysis for query: {query}")
        analysis_content = seo_analyzer.run_analysis(query, results_file_path)
        with open(analysis_file_path, 'w', encoding='utf-8') as f:
            f.write(analysis_content)
        logging.info(f"[API] SEO analysis saved to {analysis_file_path}")

        # Step 3: Convert analysis MD to HTML
        logging.info(f"[API] Converting analysis Markdown to HTML")
        md_to_html.convert_md_to_html(analysis_file_path, html_report_dir)
        logging.info(f"[API] HTML report saved to {html_report_file_path}")

        return jsonify({
            'message': 'Analysis completed successfully.',
            'query': query,
            'results_file': results_file_path,
            'analysis_file': analysis_file_path,
            'html_report_file': html_report_file_path
        }), 200

    except Exception as e:
        logging.error(f"[API] Error during analysis for query '{query}': {e}", exc_info=True)
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/api/generate_blog/<query>', methods=['POST'])
def api_generate_blog(query):
    """API endpoint to trigger blog generation based on existing analysis."""
    # TODO: Consider making this asynchronous
    query_safe = query.replace(' ', '_')
    analysis_dir = get_analysis_dir()
    blog_dir = get_blog_dir()
    html_report_dir = get_html_report_dir()

    # Find the latest analysis file
    potential_analysis_files = glob.glob(os.path.join(analysis_dir, f"seo_comparative_analysis_{query_safe}*.md"))
    if not potential_analysis_files:
        return jsonify({'error': f'Analysis file for query "{query}" not found. Please run analysis first.'}), 404
    latest_analysis_file = max(potential_analysis_files, key=os.path.getctime)

    # Define blog file paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # Use new timestamp for blog
    blog_filename_md = f"blog_{query_safe}_{timestamp}.md"
    blog_filename_html = blog_filename_md.replace('.md', '.html')
    blog_file_path_md = os.path.join(blog_dir, blog_filename_md)
    blog_file_path_html = os.path.join(html_report_dir, blog_filename_html)

    try:
        logging.info(f"[API] Starting blog generation for query: {query} using {latest_analysis_file}")
        # Read analysis content
        with open(latest_analysis_file, 'r', encoding='utf-8') as f:
            analysis_content = f.read()
        
        # Generate blog post
        blog_content = generate_seo_blog.generate_blog_post(analysis_content, query)
        with open(blog_file_path_md, 'w', encoding='utf-8') as f:
            f.write(blog_content)
        logging.info(f"[API] Blog post saved to {blog_file_path_md}")

        # Convert blog MD to HTML
        logging.info(f"[API] Converting blog Markdown to HTML")
        md_to_html.convert_md_to_html(blog_file_path_md, html_report_dir)
        logging.info(f"[API] Blog HTML report saved to {blog_file_path_html}")
        
        return jsonify({
            'message': 'Blog post generated successfully.',
            'query': query,
            'analysis_used': latest_analysis_file,
            'blog_file_md': blog_file_path_md,
            'blog_file_html': blog_file_path_html
        }), 200

    except Exception as e:
        logging.error(f"[API] Error during blog generation for query '{query}': {e}", exc_info=True)
        return jsonify({'error': f'Blog generation failed: {str(e)}'}), 500


@app.route('/api/simple-search', methods=['POST'])
def simple_search():
    """Simplified API endpoint for testing search functionality.
    This is a lightweight endpoint that returns mock results without actually performing a search.
    It's useful for testing the frontend without hitting the real search functionality.
    """
    # Global try-except to ensure we always return valid JSON
    try:
        # Parse request data safely
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            query = data.get('query', '')
            try:
                num_results = int(data.get('num_results', 10))
            except (ValueError, TypeError):
                num_results = 10
                logger.warning(f"Invalid num_results value, using default: 10")
            
            if not query:
                return jsonify({"error": "Query parameter is required"}), 400
        except Exception as parse_error:
            logger.error(f"Error parsing request data: {str(parse_error)}")
            return jsonify({"error": f"Invalid request format: {str(parse_error)}"}), 400
        
        # Log the request
        logger.info(f"Simple Search API called with query: '{query}', num_results: {num_results}")
        print(f"Simple Search API called with query: '{query}', num_results: {num_results}")
        
        # Generate mock results instead of actually searching
        try:
            mock_results = [
                {
                    "url": f"https://example.com/result-{i+1}",
                    "title": f"Example Result {i+1} for '{query}'",
                    "description": f"This is a mock search result for the query '{query}'. Result number {i+1}."
                } for i in range(min(num_results, 5))  # Limit to 5 results max
            ]
            
            # Create response data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_query = re.sub(r'\W+', '_', query)
            json_filename = f"{filename_query}_{timestamp}.json"
            
            output_data = {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "results": mock_results,
                "files": {
                    "json": json_filename,
                    "csv": f"{filename_query}_{timestamp}.csv"
                }
            }
            
            # Don't actually save to file to keep it simple
            
            return jsonify(output_data)
        except Exception as results_error:
            logger.error(f"Error generating mock results: {str(results_error)}")
            return jsonify({
                "query": query,
                "error": f"Error generating results: {str(results_error)}",
                "results": []
            }), 500
    
    except Exception as e:
        # Catch-all exception handler to ensure we always return valid JSON
        import traceback
        error_msg = f"Unhandled error in simple search API: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        print(error_msg)
        traceback.print_exc()
        
        # Always return valid JSON, even in case of catastrophic failure
        return jsonify({
            "error": "Server error occurred. Please try again later.",
            "error_details": str(e),
            "results": []
        }), 500

@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for the frontend to search and analyze SERP results.
    This is a synchronous version that uses a thread to run the async operations.
    """
    # Global try-except to catch any unexpected errors
    try:
        # Parse request data safely
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            query = data.get('query', '')
            try:
                num_results = int(data.get('num_results', 10))
            except (ValueError, TypeError):
                num_results = 10
                logger.warning(f"Invalid num_results value, using default: 10")
            
            if not query:
                return jsonify({"error": "Query parameter is required"}), 400
        except Exception as parse_error:
            logger.error(f"Error parsing request data: {str(parse_error)}")
            return jsonify({"error": f"Invalid request format: {str(parse_error)}"}), 400
        
        # Log the request
        logger.info(f"API Search called with query: '{query}', num_results: {num_results}")
        print(f"API Search called with query: '{query}', num_results: {num_results}")
        
        # For simple queries, we can return mock results immediately
        # This is useful for testing and when the real search is unavailable
        if query.lower() == 'test' or query.lower() == 'example':
            mock_results = [
                {
                    "url": f"https://example.com/result-{i+1}",
                    "title": f"Example Result {i+1} for '{query}'",
                    "description": f"This is a mock search result for the query '{query}'. Result number {i+1}."
                } for i in range(min(num_results, 5))  # Limit to 5 results max
            ]
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_query = re.sub(r'\W+', '_', query)
            json_filename = f"{filename_query}_{timestamp}.json"
            
            output_data = {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "results": mock_results,
                "files": {
                    "json": json_filename,
                    "csv": f"{filename_query}_{timestamp}.csv"
                }
            }
            
            # Save to file
            json_path = os.path.join(app.config['RESULTS_FOLDER'], json_filename)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4)
            
            return jsonify(output_data)
        
        # For real queries, use the SerpAnalyzer (which is actually BypassSerpAnalyzer)
        # Initialize the analyzer
        analyzer = SerpAnalyzer()
        
        # Run the search in a synchronous way
        # This is a simplified approach - in production, you'd want to use a proper task queue
        loop = asyncio.new_event_loop()
        
        # Define the async function that will run in the event loop
        async def run_search():
            # Check if the analyzer has the analyze_serp_for_api method (added to bypass_serp.py)
            if hasattr(analyzer, 'analyze_serp_for_api') and callable(getattr(analyzer, 'analyze_serp_for_api')):
                print(f"Using analyze_serp_for_api method from BypassSerpAnalyzer for query: {query}")
                # This method does everything: search, analyze pages, and format results
                return await analyzer.analyze_serp_for_api(query, num_results)
            
            # Fallback to our implementation if analyze_serp_for_api is not available
            print(f"Fallback: Using search_google + analyze_page for query: {query}")
            # Get search results
            search_results = await analyzer.search_google(query, num_results)
            
            if not search_results:
                return {
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                    "results": [],
                    "error": "No search results found"
                }
            
            # Process results - analyze each page in detail
            analyzed_pages = []
            
            # Use aiohttp for concurrent page analysis
            async with aiohttp.ClientSession() as session:
                tasks = []
                for result in search_results:
                    if result.get('url'):
                        # Add task to analyze each page
                        tasks.append(analyze_page(result['url'], session))
                
                # Gather results from all page analysis tasks
                # Use return_exceptions=True to prevent one failed task from stopping others
                page_analysis_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, analyzed_data in enumerate(page_analysis_results):
                    original_result = search_results[i] # Assuming order is maintained
                    if isinstance(analyzed_data, Exception):
                        # Handle exceptions during page analysis
                        print(f"Exception during page analysis for {original_result.get('url')}: {analyzed_data}")
                        analyzed_pages.append({
                            "url": original_result.get('url', ''),
                            "title": original_result.get('title', 'Error'),
                            "description": original_result.get('snippet', 'Failed to analyze page details.'),
                            "error_detail": str(analyzed_data)
                        })
                    elif analyzed_data:
                        # Merge raw search result data with detailed analyzed data
                        # Analyzed data takes precedence for common fields
                        merged_data = {**original_result, **analyzed_data} 
                        analyzed_pages.append(merged_data)
                    else:
                        # Fallback if analyze_page somehow returns None but not an exception
                        analyzed_pages.append({
                            "url": original_result.get('url', ''),
                            "title": original_result.get('title', 'N/A'),
                            "description": original_result.get('snippet', 'Page analysis returned no data.'),
                        })
            
            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_query = re.sub(r'\W+', '_', query)
            json_filename = f"{filename_query}_{timestamp}.json"
            
            output_data = {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "results": analyzed_pages,
                "files": {
                    "json": json_filename,
                    "csv": f"{filename_query}_{timestamp}.csv"
                }
            }
            
            # Save to file
            json_path = os.path.join(app.config['RESULTS_FOLDER'], json_filename)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4)
            
            return output_data
        
        # Run the async function in the event loop
        try:
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(run_search())
        except Exception as e:
            logger.error(f"Error running search in event loop: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": f"Error during search execution: {str(e)}"}), 500
        finally:
            try:
                loop.close()
            except Exception as loop_close_error:
                logger.error(f"Error closing event loop: {str(loop_close_error)}")
        
        # Validate results is a dictionary
        if not isinstance(results, dict):
            logger.error(f"Unexpected results type: {type(results)}")
            return jsonify({"error": "Search returned invalid data format"}), 500
        
        try:
            # Save results to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_query = re.sub(r'\W+', '_', query)
            json_filename = f"{filename_query}_{timestamp}.json"
            
            # Ensure results directory exists
            os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
            
            # Save to file
            json_path = os.path.join(app.config['RESULTS_FOLDER'], json_filename)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4)
            
            # Add the file information
            results['files'] = {
                "json": json_filename,
                "csv": f"{filename_query}_{timestamp}.csv"
            }
            
            return jsonify(results)
        except Exception as file_error:
            logger.error(f"Error saving results to file: {str(file_error)}")
            traceback.print_exc()
            # Still return the results even if saving failed
            return jsonify({"results": results.get("results", []), 
                          "query": query,
                          "timestamp": datetime.now().isoformat(),
                          "error": f"Results generated but could not be saved: {str(file_error)}"})
    except Exception as e:
        # Catch-all exception handler to ensure we always return valid JSON
        error_msg = f"Unhandled error in API search: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        print(error_msg)
        traceback.print_exc()
        
        # Always return valid JSON, even in case of catastrophic failure
        return jsonify({
            "error": "Server error occurred. Please try again later.",
            "error_details": str(e),
            "results": [],
            "query": data.get('query', '') if 'data' in locals() and data else "unknown",
            "timestamp": datetime.now().isoformat()
        }), 500

async def analyze_page(url, session):
    """Analyze a single page for detailed SEO data."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/"
        }
        
        print(f"Analyzing page: {url}")
        async with session.get(url, headers=headers, timeout=20) as response:
            if response.status != 200:
                print(f"Failed to fetch {url}, status: {response.status}")
                return {"error": f"HTTP {response.status}"}
            
            html = await response.text()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Basic page info
            title = soup.title.string.strip() if soup.title else ""
            
            # Meta tags
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else ""
            
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            keywords = meta_keywords['content'].strip() if meta_keywords and meta_keywords.get('content') else ""
            
            # Extract headings
            h1_tags = [h1.get_text(strip=True) for h1 in soup.find_all('h1')]
            h2_tags = [h2.get_text(strip=True) for h2 in soup.find_all('h2')]
            h3_tags = [h3.get_text(strip=True) for h3 in soup.find_all('h3')]
            
            # Extract links
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    if url.endswith('/'):
                        href = url + href[1:]
                    else:
                        href = url + href
                elif not href.startswith(('http://', 'https://')):
                    if url.endswith('/'):
                        href = url + href
                    else:
                        href = url + '/' + href
                
                links.append({
                    'text': link.get_text(strip=True),
                    'url': href,
                    'is_internal': href.startswith(url) if href.startswith(('http://', 'https://')) else True
                })
            
            # Count internal and external links
            internal_links = [link for link in links if link['is_internal']]
            external_links = [link for link in links if not link['is_internal']]
            
            # Extract images
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                # Convert relative URLs to absolute
                if src.startswith('/'):
                    if url.endswith('/'):
                        src = url + src[1:]
                    else:
                        src = url + src
                elif not src.startswith(('http://', 'https://')):
                    if url.endswith('/'):
                        src = url + src
                    else:
                        src = url + '/' + src
                
                images.append({
                    'src': src,
                    'alt': img.get('alt', '')
                })
            
            # Extract text content
            body_text = soup.body.get_text(" ", strip=True) if soup.body else ""
            word_count = len(body_text.split()) if body_text else 0
            
            # Get a sample of the content (first 200 words)
            content_sample = " ".join(body_text.split()[:200]) if body_text else ""
            
            print(f"Successfully analyzed: {url}, Title: {title[:50]}...")
            return {
                "url": url,
                "title": title,
                "description": description,
                "keywords": keywords,
                "headings": {
                    "h1": h1_tags,
                    "h2": h2_tags,
                    "h3": h3_tags
                },
                "links": {
                    "total": len(links),
                    "internal": len(internal_links),
                    "external": len(external_links),
                    "sample": links[:10]  # Include first 10 links as a sample
                },
                "images": {
                    "total": len(images),
                    "with_alt": len([img for img in images if img['alt']]),
                    "sample": images[:5]  # Include first 5 images as a sample
                },
                "content": {
                    "word_count": word_count,
                    "sample": content_sample
                }
            }
    except asyncio.TimeoutError:
        print(f"Timeout analyzing page: {url}")
        return {"url": url, "error": "Timeout"}
    except Exception as e:
        print(f"Error analyzing {url}: {str(e)}")
        return {"url": url, "error": str(e)}


# ===========================
# Main Execution
# ===========================

if __name__ == '__main__':
    # Make sure the logger is configured before running the app
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    # Get port from environment variable (for Heroku compatibility) or use 5000 as default
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', debug=False, port=port)

# --- Jinja Filter for Markdown ---
def markdown_to_html(text):
    """Converts a Markdown string to HTML using the python-markdown library."""
    return markdown.markdown(text, extensions=['markdown.extensions.fenced_code', 
                                               'markdown.extensions.tables',
                                               'markdown.extensions.nl2br'])

app.jinja_env.filters['markdown'] = markdown_to_html
# --------------------------------
