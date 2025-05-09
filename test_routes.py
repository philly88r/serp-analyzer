"""
Test routes to diagnose deployment issues on Render.
Import this file in both app.py and simple_serp_app.py.
"""

def register_test_routes(app):
    """Register test routes with the given Flask app."""
    
    @app.route('/test-html')
    def test_html():
        """Return a simple HTML page for testing."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SERP Analyzer Test Page</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .success { color: green; }
                .info { color: blue; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>SERP Analyzer Test Page</h1>
                <p class="success">✅ If you can see this page, the basic Flask routing is working!</p>
                <p>This is a static test page to verify the deployment.</p>
                <h2>API Test Links:</h2>
                <ul>
                    <li><a href="/api/test-json">/api/test-json</a> - Should return a simple JSON response</li>
                    <li><a href="/api/test-route">/api/test-route</a> - Should return the test route JSON</li>
                </ul>
                <p class="info">Check these links to verify API routing is working correctly.</p>
            </div>
        </body>
        </html>
        """
    
    @app.route('/api/test-json')
    def test_json():
        """Return a simple JSON response for testing."""
        from flask import jsonify
        return jsonify({
            "status": "success",
            "message": "API test endpoint is working!",
            "timestamp": "2025-05-08T23:42:00-04:00"
        })
    
    return app  # Return the app for chaining
