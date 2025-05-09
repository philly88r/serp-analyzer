import os
import sys
import json
import asyncio
import re
import markdown
from datetime import datetime
from threading import Thread
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, send_from_directory
import generate_seo_blog
# Import serp_analyzer directly instead of serp_analyzer_working
# import serp_analyzer_working
import seo_analyzer
import md_to_html
import glob
import io
import logging

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
        print("Bypass SERP analyzer loaded successfully - using alternative search engines to avoid CAPTCHA")
    except ImportError:
        try:
            from improved_serp_analyzer import ImprovedSerpAnalyzer as SerpAnalyzer
            print("Improved SERP analyzer loaded successfully")
        except ImportError:
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
        
        # Configure Playwright for Heroku
        is_heroku = 'DYNO' in os.environ
        if is_heroku:
            print("Running on Heroku, configuring Playwright...")
            
            # Set environment variables for Playwright on Heroku
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/app/.playwright'
            os.environ['PLAYWRIGHT_CHROMIUM_ARGS'] = '--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage'
            print(f"Set PLAYWRIGHT_BROWSERS_PATH to {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")
            print(f"Set PLAYWRIGHT_CHROMIUM_ARGS to {os.environ.get('PLAYWRIGHT_CHROMIUM_ARGS')}")
            
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
    
    return render_template('index.html', results=results, browser_automation_available=BROWSER_AUTOMATION_AVAILABLE)

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
            serp_analysis = loop.run_until_complete(analyzer.analyze_serp(query, num_results))
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
        seo_analyzer.main([serp_file])
        
        flash(f'Successfully created SEO analysis for "{query}"', 'success')
        return redirect(url_for('index'))
    
    except Exception as e:
        flash(f'Error during analysis: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/generate_blog/<query>')
def generate_blog(query):
    # Replace spaces with underscores for file operations
    query_file = query.replace(' ', '_')
    
    # Check if SERP results exist
    serp_file = os.path.join(app.config['RESULTS_FOLDER'], f'serp_{query_file}.json')
    if not os.path.exists(serp_file):
        flash(f'SERP results for "{query}" not found', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Generate blog post
        output_file = os.path.join(app.config['BLOG_FOLDER'], f'blog_{query_file}.md')
        generate_seo_blog.main([serp_file, '--output', output_file])
        
        # Convert to HTML
        html_file = md_to_html.convert_md_to_html(output_file, app.config['HTML_REPORTS_FOLDER'])
        
        flash(f'Successfully generated blog post for "{query}"', 'success')
        return redirect(url_for('view_blog', query=query))
    
    except Exception as e:
        flash(f'Error generating blog: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/view_results/<query>')
def view_results(query):
    # Replace spaces with underscores for file operations
    query_file = query.replace(' ', '_')
    
    try:
        # Check if SERP results exist
        serp_file = os.path.join(app.config['RESULTS_FOLDER'], f'serp_{query_file}.json')
        
        # Make sure the results directory exists
        os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
        
        if not os.path.exists(serp_file):
            # Try to find any file that might match the query (partial match)
            potential_files = glob.glob(os.path.join(app.config['RESULTS_FOLDER'], f'serp_{query_file}*.json'))
            if potential_files:
                serp_file = potential_files[0]  # Use the first matching file
            else:
                flash(f'SERP results for "{query}" not found', 'danger')
                return redirect(url_for('index'))
        
        # Load SERP results
        with open(serp_file, 'r', encoding='utf-8') as f:
            serp_data = json.load(f)
        
        return render_template('results.html', query=query, serp_data=serp_data)
    except Exception as e:
        flash(f'Error viewing results for "{query}": {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/view_analysis/<query>')
def view_analysis(query):
    # Replace spaces with underscores for file operations
    query_file = query.replace(' ', '_')
    
    try:
        # Make sure directories exist
        os.makedirs(app.config['ANALYSIS_FOLDER'], exist_ok=True)
        os.makedirs(app.config['HTML_REPORTS_FOLDER'], exist_ok=True)
        
        # Find analysis file
        analysis_file = None
        if os.path.exists(app.config['ANALYSIS_FOLDER']):
            for file in os.listdir(app.config['ANALYSIS_FOLDER']):
                if file.startswith(f'seo_comparative_analysis_{query_file}_') and file.endswith('.md'):
                    analysis_file = os.path.join(app.config['ANALYSIS_FOLDER'], file)
                    break
        
        if not analysis_file:
            flash(f'SEO analysis for "{query}" not found', 'danger')
            return redirect(url_for('index'))
        
        # Load analysis content
        with open(analysis_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse Markdown Content into Sections
        sections = []
        parts = re.split(r'^## +(.*?) *$\n', content, flags=re.MULTILINE)
        
        current_title = "Introduction" 
        current_content = parts[0].strip()
        sections.append({'title': current_title, 'content': current_content})
        
        for i in range(1, len(parts), 2):
            title = parts[i].strip()
            markdown_content = parts[i+1].strip() if (i+1) < len(parts) else ""
            sections.append({'title': title, 'content': markdown_content})
        
        # Find HTML version if it exists
        html_file = None
        base_name = os.path.basename(analysis_file)
        html_name = os.path.splitext(base_name)[0] + '.html'
        html_path = os.path.join(app.config['HTML_REPORTS_FOLDER'], html_name)
        
        if os.path.exists(html_path):
            html_file = html_path
        else:
            # Generate HTML if it doesn't exist
            try:
                md_to_html.convert_md_to_html(analysis_file, app.config['HTML_REPORTS_FOLDER'])
                if os.path.exists(html_path):
                    html_file = html_path
            except Exception as e:
                print(f"Error generating HTML: {str(e)}")
        
        return render_template('analysis.html', query=query, sections=sections, html_file=html_file)
    except Exception as e:
        flash(f'Error viewing analysis for "{query}": {str(e)}', 'danger')
        return redirect(url_for('index'))
    

@app.route('/view_blog/<query>')
def view_blog(query):
    # Replace spaces with underscores for file operations
    query_file = query.replace(' ', '_')
    
    try:
        # Make sure directories exist
        os.makedirs(app.config['BLOG_FOLDER'], exist_ok=True)
        os.makedirs(app.config['HTML_REPORTS_FOLDER'], exist_ok=True)
        
        # Check if blog exists
        blog_file = os.path.join(app.config['BLOG_FOLDER'], f'blog_{query_file}.md')
        
        # Try to find any matching blog file if exact match not found
        if not os.path.exists(blog_file):
            potential_files = glob.glob(os.path.join(app.config['BLOG_FOLDER'], f'blog_{query_file}*.md'))
            if potential_files:
                blog_file = potential_files[0]  # Use the first matching file
            else:
                flash(f'Blog post for "{query}" not found', 'danger')
                return redirect(url_for('index'))
        
        # Load blog content
        with open(blog_file, 'r', encoding='utf-8') as f:
            blog_content = f.read()
        
        # Find HTML version if it exists
        html_file = None
        base_name = os.path.basename(blog_file)
        html_name = base_name.replace('.md', '.html')
        html_path = os.path.join(app.config['HTML_REPORTS_FOLDER'], html_name)
        
        if os.path.exists(html_path):
            html_file = html_path
        else:
            # Convert to HTML if not exists
            try:
                html_file = md_to_html.convert_md_to_html(blog_file, app.config['HTML_REPORTS_FOLDER'])
            except Exception as e:
                print(f"Error generating HTML: {str(e)}")
        
        return render_template('blog.html', query=query, blog_content=blog_content, html_file=html_file)
    except Exception as e:
        flash(f'Error viewing blog for "{query}": {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/download/<file_type>/<query>')
def download(file_type, query):
    """Handles downloading of results or analysis files."""
    query_safe = query.replace(' ', '_')
    
    if file_type == 'results':
        results_dir = get_results_dir()
        potential_files = glob.glob(os.path.join(results_dir, f"serp_{query_safe}*.json"))
        if not potential_files:
            flash(f'No results file found for query: {query}', 'danger')
            return redirect(url_for('index'))
        
        latest_file = max(potential_files, key=os.path.getctime)
        
        try:
            # Load the JSON data
            with open(latest_file, 'r', encoding='utf-8') as f:
                results_data = json.load(f)
            
            # Render the results.html template with the data
            html_content = render_template('results.html', query=query, serp_data=results_data)
            
            # Create an in-memory file
            buffer = io.BytesIO()
            buffer.write(html_content.encode('utf-8'))
            buffer.seek(0)
            
            # Send the rendered HTML as a downloadable file
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"serp_results_{query_safe}.html",
                mimetype='text/html'
            )

        except Exception as e:
            logging.error(f"Error generating HTML download for results {query}: {e}")
            flash(f'Error generating HTML download for results: {e}', 'danger')
            return redirect(url_for('view_results', query=query))
        
    elif file_type == 'analysis':
        analysis_dir = get_analysis_dir()
        # Find the latest MD analysis file for the query
        potential_files = glob.glob(os.path.join(analysis_dir, f"seo_comparative_analysis_{query_safe}*.md"))
        if not potential_files:
            flash(f'No analysis file found for query: {query}', 'danger')
            return redirect(url_for('index'))
        latest_file = max(potential_files, key=os.path.getctime)
        return send_file(latest_file, as_attachment=True)
        
    elif file_type == 'analysis_html':
        html_report_dir = get_html_report_dir()
        # Find the latest HTML analysis file for the query
        potential_files = glob.glob(os.path.join(html_report_dir, f"seo_comparative_analysis_{query_safe}*.html"))
        if not potential_files:
            flash(f'No HTML analysis report found for query: {query}', 'danger')
            # Try redirecting to the analysis page where they might generate it?
            # Or maybe just redirect to index if it should always exist?
            return redirect(url_for('view_analysis', query=query))
        latest_file = max(potential_files, key=os.path.getctime)
        return send_file(latest_file, as_attachment=True)
        
    elif file_type == 'blog':
        blog_dir = get_blog_dir()
        # Find the latest MD blog file for the query
        potential_files = glob.glob(os.path.join(blog_dir, f"blog_{query_safe}.md"))
        if not potential_files:
            flash(f'No blog post found for query: {query}', 'danger')
            return redirect(url_for('index'))
        latest_file = max(potential_files, key=os.path.getctime)
        return send_file(latest_file, as_attachment=True)
        
    elif file_type == 'html_blog':
        blog_dir = get_blog_dir()
        # Find the latest HTML blog file for the query
        potential_files = glob.glob(os.path.join(app.config['HTML_REPORTS_FOLDER'], f"blog_{query_safe}.html"))
        if not potential_files:
            flash(f'No HTML blog post found for query: {query}', 'danger')
            # Try redirecting to the blog page where they might generate it?
            # Or maybe just redirect to index if it should always exist?
            return redirect(url_for('view_blog', query=query))
        latest_file = max(potential_files, key=os.path.getctime)
        return send_file(latest_file, as_attachment=True)
    
    else:
        flash('Invalid file type', 'danger')
        return redirect(url_for('index'))

@app.route('/delete/<query>')
def delete(query):
    # Replace spaces with underscores for file operations
    query_file = query.replace(' ', '_')
    
    # Delete SERP results
    serp_file = os.path.join(app.config['RESULTS_FOLDER'], f'serp_{query_file}.json')
    if os.path.exists(serp_file):
        os.remove(serp_file)
    
    serp_csv = os.path.join(app.config['RESULTS_FOLDER'], f'serp_{query_file}.csv')
    if os.path.exists(serp_csv):
        os.remove(serp_csv)
    
    # Delete analysis files
    for file in os.listdir(app.config['ANALYSIS_FOLDER']):
        if query_file in file:
            os.remove(os.path.join(app.config['ANALYSIS_FOLDER'], file))
    
    # Delete blog files
    blog_file = os.path.join(app.config['BLOG_FOLDER'], f'blog_{query_file}.md')
    if os.path.exists(blog_file):
        os.remove(blog_file)
    
    # Delete HTML files
    for file in os.listdir(app.config['HTML_REPORTS_FOLDER']):
        if query_file in file:
            os.remove(os.path.join(app.config['HTML_REPORTS_FOLDER'], file))
    
    flash(f'Successfully deleted all files for "{query}"', 'success')
    return redirect(url_for('index'))

# ===========================
# API Endpoints
# ===========================

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

@app.route('/api/blog/<query>', methods=['GET'])
def api_get_blog(query):
    """API endpoint to get the latest blog Markdown content for a query."""
    query_safe = query.replace(' ', '_')
    blog_dir = get_blog_dir()
    potential_files = glob.glob(os.path.join(blog_dir, f"blog_{query_safe}*.md"))
    
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
    """Simplified API endpoint for testing search functionality."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        query = data.get('query', '')
        num_results = int(data.get('num_results', 10))
        
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400
        
        # Log the request
        print(f"Simple Search API called with query: '{query}', num_results: {num_results}")
        
        # Generate mock results instead of actually searching
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
    
    except Exception as e:
        import traceback
        print(f"Error in simple search API: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for the frontend to search and analyze SERP results.
    This is a synchronous version that uses a thread to run the async operations.
    It combines the bypass_serp approach with the original SEO analyzer AI analysis.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        query = data.get('query', '')
        num_results = int(data.get('num_results', 10))
        
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400
        
        # Log the request
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
        
        # Set a longer timeout for the entire operation (5 minutes)
        timeout = 300
        
        # Create a timestamp for this search operation
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_query = re.sub(r'\W+', '_', query)
        json_filename = f"{filename_query}_{timestamp}.json"
        
        # Create a status file to track progress
        status_path = os.path.join(app.config['RESULTS_FOLDER'], f"{filename_query}_{timestamp}_status.json")
        status_data = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "status": "started",
            "progress": 0,
            "message": "Starting search operation"
        }
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=4)
        
        # Initialize the analyzer
        analyzer_instance = SerpAnalyzer()
        
        # Define a function to run the search in a separate thread
        def run_search_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_search(analyzer_instance, query, num_results, status_path, status_data, json_filename, timestamp, filename_query))
            finally:
                loop.close()
        
        # Run in a separate thread to avoid blocking the Flask server
        thread = Thread(target=run_search_thread)
        thread.daemon = True
        thread.start()
        
        # Return a status URL for the client to check progress
        status_url = f"/api/status/{filename_query}_{timestamp}_status.json"
        return jsonify({
            "message": "Search started successfully",
            "status_url": status_url,
            "query": query,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        import traceback
        print(f"Error in API search: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/<status_file>', methods=['GET'])
def api_status(status_file):
    """API endpoint to check the status of a long-running operation."""
    try:
        status_path = os.path.join(app.config['RESULTS_FOLDER'], status_file)
        if not os.path.exists(status_path):
            return jsonify({"error": "Status file not found"}), 404
        
        with open(status_path, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        
        return jsonify(status_data)
    
    except Exception as e:
        import traceback
        print(f"Error in API status: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

async def run_search(analyzer, query, num_results, status_path, status_data, json_filename, timestamp, filename_query):
    """Async function to run the search and analysis."""
    try:
        # Update status
        status_data["status"] = "searching"
        status_data["message"] = "Retrieving search results"
        status_data["progress"] = 10
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=4)
        
        # Check if the analyzer has the analyze_serp_for_api method (added to bypass_serp.py)
        if hasattr(analyzer, 'analyze_serp_for_api') and callable(getattr(analyzer, 'analyze_serp_for_api')):
            print(f"Using analyze_serp_for_api method from BypassSerpAnalyzer for query: {query}")
        
            # This method does everything: search, analyze pages, and format results
            serp_data = await analyzer.analyze_serp_for_api(query, num_results)
            
            # Update status
            status_data["status"] = "analyzing"
            status_data["message"] = "Running AI analysis on search results"
            status_data["progress"] = 50
            with open(status_path, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=4)
            
            # Now pass the data to the original SEO analyzer for AI analysis
            try:
                print("Passing data to SEO analyzer for AI analysis...")
                
                # Use the original SEO analyzer to perform AI analysis
                serp_data_with_analysis = seo_analyzer.analyze_seo_with_gemini(serp_data)
                
                # Update status
                status_data["status"] = "comparing"
                status_data["message"] = "Creating comparative analysis"
                status_data["progress"] = 80
                with open(status_path, 'w', encoding='utf-8') as f:
                    json.dump(status_data, f, indent=4)
                
                # Also create a comparative analysis
                comparative_analysis = seo_analyzer.create_seo_comparative_analysis(serp_data_with_analysis)
                serp_data_with_analysis['comparative_analysis'] = comparative_analysis
                if hasattr(analyzer, 'analyze_serp_for_api') and callable(getattr(analyzer, 'analyze_serp_for_api')):
                    print(f"Using analyze_serp_for_api method from BypassSerpAnalyzer for query: {query}")
                
                    # This method does everything: search, analyze pages, and format results
                    serp_data = await analyzer.analyze_serp_for_api(query, num_results)
                    
                    # Update status
                    status_data["status"] = "analyzing"
                    status_data["message"] = "Running AI analysis on search results"
                    status_data["progress"] = 50
                    with open(status_path, 'w', encoding='utf-8') as f:
                        json.dump(status_data, f, indent=4)
                    
                    # Now pass the data to the original SEO analyzer for AI analysis
                    try:
                        print("Passing data to SEO analyzer for AI analysis...")
                        
                        # Use the original SEO analyzer to perform AI analysis
                        serp_data_with_analysis = seo_analyzer.analyze_seo_with_gemini(serp_data)
                        
                        # Update status
                        status_data["status"] = "comparing"
                        status_data["message"] = "Creating comparative analysis"
                        status_data["progress"] = 80
                        with open(status_path, 'w', encoding='utf-8') as f:
                            json.dump(status_data, f, indent=4)
                        
                        # Also create a comparative analysis
                        comparative_analysis = seo_analyzer.create_seo_comparative_analysis(serp_data_with_analysis)
                        serp_data_with_analysis['comparative_analysis'] = comparative_analysis
                        
                        print("AI SEO analysis completed successfully")
                    except Exception as e:
                        print(f"Error in AI SEO analysis: {str(e)}")
                        
                        # Continue even if AI analysis fails
                        serp_data_with_analysis = serp_data
                        serp_data_with_analysis['ai_analysis_error'] = str(e)
                    
                    # Add file information
                    serp_data_with_analysis['files'] = {
                        "json": json_filename,
                        "csv": f"{filename_query}_{timestamp}.csv"
                    }
                    
                    # Save the results
                    json_path = os.path.join(app.config['RESULTS_FOLDER'], json_filename)
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(serp_data_with_analysis, f, indent=4, ensure_ascii=False)
                    
                    # Update status to completed
                    status_data["status"] = "completed"
                    status_data["message"] = "Analysis completed successfully"
                    status_data["progress"] = 100
                    status_data["result_file"] = json_filename
                    with open(status_path, 'w', encoding='utf-8') as f:
                        json.dump(status_data, f, indent=4)
                    
                    return serp_data_with_analysis
                
            except Exception as e:
                print(f"Error in run_search: {str(e)}")
                
                # Update status to error
                status_data["status"] = "error"
                status_data["message"] = f"Error: {str(e)}"
                with open(status_path, 'w', encoding='utf-8') as f:
                    json.dump(status_data, f, indent=4)
                raise
            
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
        result = loop.run_until_complete(run_search())
        loop.close()
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        print(f"Error in API search: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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
# Status and Results Endpoints
# ===========================

@app.route('/api/status/<filename>', methods=['GET'])
def check_status(filename):
    """API endpoint to check the status of a long-running search operation."""
    try:
        status_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
        if not os.path.exists(status_path):
            return jsonify({"error": "Status file not found"}), 404
        
        with open(status_path, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        
        return jsonify(status_data)
    except Exception as e:
        print(f"Error checking status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/results/<filename>', methods=['GET'])
def get_results(filename):
    """API endpoint to get the results of a completed search operation."""
    try:
        results_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
        if not os.path.exists(results_path):
            return jsonify({"error": "Results file not found"}), 404
        
        with open(results_path, 'r', encoding='utf-8') as f:
            results_data = json.load(f)
        
        return jsonify(results_data)
    except Exception as e:
        print(f"Error getting results: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
