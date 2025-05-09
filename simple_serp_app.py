from flask import Flask, render_template, request, jsonify
import asyncio
import os
import json
from datetime import datetime
import logging
from bypass_serp import BypassSerpAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simple_serp_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SimpleSerpApp")

app = Flask(__name__)

# Create necessary directories
os.makedirs("results", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Create HTML templates
def create_templates():
    # Create index.html
    index_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Simple SERP Analyzer</title>
        <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    </head>
    <body>
        <div class="container">
            <h1>Simple SERP Analyzer</h1>
            <p>Enter a search query to analyze search engine results</p>
            
            <form id="search-form" action="/search" method="post">
                <div class="form-group">
                    <input type="text" id="query" name="query" placeholder="Enter your search query" required>
                </div>
                <div class="form-group">
                    <label for="num_results">Number of results:</label>
                    <select id="num_results" name="num_results">
                        <option value="5">5</option>
                        <option value="10" selected>10</option>
                        <option value="15">15</option>
                        <option value="20">20</option>
                    </select>
                </div>
                <div class="form-group">
                    <button type="submit" id="search-button">Search</button>
                </div>
            </form>
            
            <div id="loading" style="display: none;">
                <div class="spinner"></div>
                <p>Searching... This may take a moment.</p>
            </div>
            
            <div id="results-container" style="display: none;">
                <h2>Search Results</h2>
                <div id="results-info"></div>
                <div id="results-list"></div>
                <div id="download-links">
                    <a id="download-json" href="#" class="download-button">Download JSON</a>
                    <a id="download-csv" href="#" class="download-button">Download CSV</a>
                </div>
            </div>
        </div>
        
        <script src="{{ url_for('static', filename='script.js') }}"></script>
    </body>
    </html>
    """
    
    with open("templates/index.html", "w") as f:
        f.write(index_html)
    
    # Create results.html
    results_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SERP Analysis Results</title>
        <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    </head>
    <body>
        <div class="container">
            <h1>SERP Analysis Results</h1>
            <div class="results-header">
                <h2>Query: {{ results.query }}</h2>
                <p>Timestamp: {{ results.timestamp }}</p>
                <p>Found {{ results.results|length }} results</p>
            </div>
            
            <div class="download-links">
                <a href="{{ url_for('download_results', filename=json_filename) }}" class="download-button">Download JSON</a>
                <a href="{{ url_for('download_results', filename=csv_filename) }}" class="download-button">Download CSV</a>
            </div>
            
            <div class="results-list">
                {% for result in results.results %}
                <div class="result-item">
                    <h3>{{ loop.index }}. {{ result.title }}</h3>
                    <p class="result-url"><a href="{{ result.url }}" target="_blank">{{ result.url }}</a></p>
                    <p class="result-description">{{ result.description }}</p>
                </div>
                {% endfor %}
            </div>
            
            <div class="back-link">
                <a href="{{ url_for('index') }}" class="button">Back to Search</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open("templates/results.html", "w") as f:
        f.write(results_html)

# Create CSS and JavaScript files
def create_static_files():
    # Create style.css
    css = """
    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }
    
    body {
        font-family: Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        background-color: #f5f5f5;
        padding: 20px;
    }
    
    .container {
        max-width: 800px;
        margin: 0 auto;
        background-color: #fff;
        padding: 30px;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    
    h1 {
        text-align: center;
        margin-bottom: 20px;
        color: #2c3e50;
    }
    
    h2 {
        margin-bottom: 15px;
        color: #3498db;
    }
    
    p {
        margin-bottom: 20px;
    }
    
    .form-group {
        margin-bottom: 20px;
    }
    
    input[type="text"], select {
        width: 100%;
        padding: 12px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 16px;
    }
    
    button {
        background-color: #3498db;
        color: white;
        border: none;
        padding: 12px 20px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 16px;
        width: 100%;
        transition: background-color 0.3s;
    }
    
    button:hover {
        background-color: #2980b9;
    }
    
    #loading {
        text-align: center;
        margin: 30px 0;
    }
    
    .spinner {
        border: 5px solid #f3f3f3;
        border-top: 5px solid #3498db;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        animation: spin 1s linear infinite;
        margin: 0 auto 20px;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    #results-container {
        margin-top: 30px;
    }
    
    #results-info {
        margin-bottom: 20px;
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 4px;
    }
    
    .result-item {
        margin-bottom: 25px;
        padding-bottom: 20px;
        border-bottom: 1px solid #eee;
    }
    
    .result-item h3 {
        color: #2c3e50;
        margin-bottom: 8px;
    }
    
    .result-url {
        margin-bottom: 8px;
    }
    
    .result-url a {
        color: #27ae60;
        text-decoration: none;
        word-break: break-all;
    }
    
    .result-url a:hover {
        text-decoration: underline;
    }
    
    .result-description {
        color: #555;
        line-height: 1.5;
    }
    
    .download-links {
        margin: 20px 0;
        text-align: center;
    }
    
    .download-button {
        display: inline-block;
        background-color: #2ecc71;
        color: white;
        padding: 10px 15px;
        margin: 0 10px;
        border-radius: 4px;
        text-decoration: none;
        transition: background-color 0.3s;
    }
    
    .download-button:hover {
        background-color: #27ae60;
    }
    
    .back-link {
        margin-top: 30px;
        text-align: center;
    }
    
    .button {
        display: inline-block;
        background-color: #3498db;
        color: white;
        padding: 10px 20px;
        border-radius: 4px;
        text-decoration: none;
        transition: background-color 0.3s;
    }
    
    .button:hover {
        background-color: #2980b9;
    }
    """
    
    with open("static/style.css", "w") as f:
        f.write(css)
    
    # Create script.js
    js = """
    document.addEventListener('DOMContentLoaded', function() {
        const searchForm = document.getElementById('search-form');
        const loadingDiv = document.getElementById('loading');
        const resultsContainer = document.getElementById('results-container');
        const resultsInfo = document.getElementById('results-info');
        const resultsList = document.getElementById('results-list');
        const downloadJson = document.getElementById('download-json');
        const downloadCsv = document.getElementById('download-csv');
        
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Show loading spinner
            loadingDiv.style.display = 'block';
            resultsContainer.style.display = 'none';
            
            // Get form data
            const query = document.getElementById('query').value;
            const numResults = document.getElementById('num_results').value;
            
            // Send AJAX request
            fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    num_results: numResults
                }),
            })
            .then(response => response.json())
            .then(data => {
                // Hide loading spinner
                loadingDiv.style.display = 'none';
                
                // Show results
                resultsContainer.style.display = 'block';
                
                // Update results info
                resultsInfo.innerHTML = `
                    <p><strong>Query:</strong> ${data.query}</p>
                    <p><strong>Timestamp:</strong> ${data.timestamp}</p>
                    <p><strong>Found:</strong> ${data.results.length} results</p>
                `;
                
                // Update results list
                resultsList.innerHTML = '';
                data.results.forEach((result, index) => {
                    const resultItem = document.createElement('div');
                    resultItem.className = 'result-item';
                    resultItem.innerHTML = `
                        <h3>${index + 1}. ${result.title}</h3>
                        <p class="result-url"><a href="${result.url}" target="_blank">${result.url}</a></p>
                        <p class="result-description">${result.description || 'No description available'}</p>
                    `;
                    resultsList.appendChild(resultItem);
                });
                
                // Update download links
                downloadJson.href = `/download/${data.files.json}`;
                downloadCsv.href = `/download/${data.files.csv}`;
            })
            .catch(error => {
                console.error('Error:', error);
                loadingDiv.style.display = 'none';
                alert('An error occurred while searching. Please try again.');
            });
        });
    });
    """
    
    with open("static/script.js", "w") as f:
        f.write(js)

# Create templates and static files
create_templates()
create_static_files()

# Global analyzer instance
analyzer = None

def get_analyzer():
    global analyzer
    if analyzer is None:
        analyzer = BypassSerpAnalyzer()
    return analyzer

@app.route('/')
def index():
    logger.info("Main page '/' accessed.")
    return render_template("index.html")

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query', '')
    num_results = int(request.form.get('num_results', 10))
    
    if not query:
        return render_template('index.html')
    
    # Run the search
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(get_analyzer().analyze_serp(query, num_results))
    loop.close()
    
    # Generate filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = query.replace(' ', '_')
    json_filename = f"serp_{safe_query}_{timestamp}.json"
    csv_filename = f"serp_{safe_query}_{timestamp}.csv"
    
    return render_template('results.html', 
                          results=results, 
                          json_filename=json_filename,
                          csv_filename=csv_filename)

@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.json
    query = data.get('query', '')
    num_results = int(data.get('num_results', 10))
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        # Run the search
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(get_analyzer().analyze_serp(query, num_results))
        loop.close()
        
        # Generate filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = query.replace(' ', '_')
        json_filename = f"serp_{safe_query}_{timestamp}.json"
        csv_filename = f"serp_{safe_query}_{timestamp}.csv"
        
        # Return the results
        return jsonify({
            "query": results["query"],
            "timestamp": results["timestamp"],
            "results": results["results"],
            "files": {
                "json": json_filename,
                "csv": csv_filename
            }
        })
    except Exception as e:
        logger.error(f"Error in API search: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>')
def download_results(filename):
    return send_from_directory('results', filename, as_attachment=True)

if __name__ == '__main__':
    from flask import send_from_directory
    app.run(debug=True, port=5000)
