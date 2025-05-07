import os
import sys
import markdown
import glob
from datetime import datetime

def convert_md_to_html(md_file, output_dir="html_reports"):
    """
    Convert a markdown file to HTML with a nice design.
    
    Args:
        md_file (str): Path to the markdown file
        output_dir (str): Directory to save the HTML file
    
    Returns:
        str: Path to the HTML file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert markdown to HTML
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    # Get the base filename without extension
    base_name = os.path.basename(md_file)
    file_name = os.path.splitext(base_name)[0]
    
    # Create HTML file with nice design
    html_file = os.path.join(output_dir, f"{file_name}.html")
    
    # HTML template with enhanced design and better table styling
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SEO Analysis Report</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary-color: #2563eb;
            --primary-light: #dbeafe;
            --primary-dark: #1e40af;
            --secondary-color: #0f172a;
            --text-color: #334155;
            --light-text: #64748b;
            --background: #f8fafc;
            --card-bg: #ffffff;
            --border-color: #e2e8f0;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --info: #3b82f6;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--background);
            padding: 0;
            margin: 0;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .card {{
            background-color: var(--card-bg);
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            padding: 2rem;
            margin-bottom: 2rem;
        }}
        
        header {{
            background-color: var(--card-bg);
            padding: 1.5rem 2rem;
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}
        
        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .logo {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-color);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .logo svg {{
            width: 1.75rem;
            height: 1.75rem;
        }}
        
        .date {{
            color: var(--light-text);
            font-size: 0.875rem;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            color: var(--secondary-color);
            margin: 1.5rem 0 1rem 0;
            line-height: 1.3;
        }}
        
        h1 {{
            font-size: 1.875rem;
            font-weight: 700;
            margin-top: 0.5rem;
            margin-bottom: 1.5rem;
            position: relative;
            padding-bottom: 0.75rem;
        }}
        
        h1::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 4rem;
            height: 0.25rem;
            background-color: var(--primary-color);
            border-radius: 0.125rem;
        }}
        
        h2 {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-top: 2rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border-color);
        }}
        
        h3 {{
            font-size: 1.25rem;
            font-weight: 600;
        }}
        
        p {{
            margin-bottom: 1rem;
        }}
        
        /* Enhanced table styling */
        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin: 1.5rem 0;
            font-size: 0.875rem;
            overflow: hidden;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}
        
        thead {{
            background-color: var(--primary-light);
        }}
        
        th {{
            text-align: left;
            padding: 1rem;
            font-weight: 600;
            color: var(--primary-dark);
            border-bottom: 2px solid var(--primary-color);
            position: sticky;
            top: 0;
            background-color: var(--primary-light);
            z-index: 10;
        }}
        
        td {{
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        tbody tr {{
            transition: background-color 0.2s ease;
        }}
        
        tbody tr:nth-child(even) {{
            background-color: rgba(0, 0, 0, 0.02);
        }}
        
        tbody tr:hover {{
            background-color: rgba(37, 99, 235, 0.05);
        }}
        
        /* Make tables responsive */
        @media (max-width: 768px) {{
            table {{
                display: block;
                overflow-x: auto;
                white-space: nowrap;
            }}
        }}
        
        /* Styling for code elements */
        code {{
            font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
            font-size: 0.875rem;
            background-color: #f1f5f9;
            padding: 0.2rem 0.4rem;
            border-radius: 0.25rem;
            color: #ef4444;
        }}
        
        pre {{
            background-color: #1e293b;
            color: #e2e8f0;
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
            margin: 1.5rem 0;
        }}
        
        pre code {{
            background-color: transparent;
            color: inherit;
            padding: 0;
            font-size: 0.875rem;
        }}
        
        /* Blockquotes */
        blockquote {{
            border-left: 4px solid var(--primary-color);
            padding: 0.5rem 0 0.5rem 1rem;
            margin: 1.5rem 0;
            color: var(--light-text);
            background-color: #f8fafc;
            border-radius: 0 0.25rem 0.25rem 0;
        }}
        
        /* Links */
        a {{
            color: var(--primary-color);
            text-decoration: none;
            transition: color 0.2s ease;
        }}
        
        a:hover {{
            color: var(--primary-dark);
            text-decoration: underline;
        }}
        
        /* Lists */
        ul, ol {{
            padding-left: 1.5rem;
            margin: 1rem 0;
        }}
        
        li {{
            margin-bottom: 0.5rem;
        }}
        
        /* Special sections */
        .recommendations {{
            background-color: #ecfdf5;
            border-left: 4px solid var(--success);
            padding: 1.5rem;
            border-radius: 0 0.5rem 0.5rem 0;
            margin: 1.5rem 0;
        }}
        
        .warning {{
            background-color: #fff7ed;
            border-left: 4px solid var(--warning);
            padding: 1.5rem;
            border-radius: 0 0.5rem 0.5rem 0;
            margin: 1.5rem 0;
        }}
        
        .highlight {{
            background-color: rgba(245, 158, 11, 0.1);
            padding: 0.125rem 0.25rem;
            border-radius: 0.25rem;
        }}
        
        /* Footer */
        footer {{
            text-align: center;
            padding: 2rem 0;
            color: var(--light-text);
            font-size: 0.875rem;
            border-top: 1px solid var(--border-color);
            margin-top: 3rem;
        }}
        
        /* Print styles */
        @media print {{
            body {{
                background-color: white;
            }}
            
            .container {{
                max-width: 100%;
                padding: 0;
            }}
            
            .card {{
                box-shadow: none;
                padding: 0;
            }}
            
            header {{
                position: static;
                box-shadow: none;
                padding: 1rem 0;
            }}
            
            table {{
                box-shadow: none;
            }}
            
            a {{
                color: var(--text-color);
                text-decoration: none;
            }}
            
            @page {{
                margin: 2cm;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <div class="logo">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.375 2.25c-1.035 0-1.875.84-1.875 1.875v15.75c0 1.035.84 1.875 1.875 1.875h.75c1.035 0 1.875-.84 1.875-1.875V4.125c0-1.036-.84-1.875-1.875-1.875h-.75zM9.75 8.625c0-1.036.84-1.875 1.875-1.875h.75c1.036 0 1.875.84 1.875 1.875v11.25c0 1.035-.84 1.875-1.875 1.875h-.75a1.875 1.875 0 01-1.875-1.875V8.625zM3 13.125c0-1.036.84-1.875 1.875-1.875h.75c1.036 0 1.875.84 1.875 1.875v6.75c0 1.035-.84 1.875-1.875 1.875h-.75A1.875 1.875 0 013 19.875v-6.75z" />
                </svg>
                SEO Analysis Report
            </div>
            <div class="date">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
    </header>
    
    <div class="container">
        <div class="card">
            {html_content}
        </div>
        
        <footer>
            <p>Generated by SERP Analyzer | &copy; {datetime.now().year}</p>
        </footer>
    </div>
</body>
</html>
"""

    # Write HTML file
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"Converted {md_file} to {html_file}")
    return html_file

def convert_all_md_files(directory="analysis", output_dir="html_reports"):
    """
    Convert all markdown files in a directory to HTML.
    
    Args:
        directory (str): Directory containing markdown files
        output_dir (str): Directory to save HTML files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all markdown files
    md_files = glob.glob(os.path.join(directory, "*.md"))
    
    if not md_files:
        print(f"No markdown files found in {directory}")
        return
    
    print(f"Found {len(md_files)} markdown files to convert")
    
    # Convert each file
    html_files = []
    for md_file in md_files:
        html_file = convert_md_to_html(md_file, output_dir)
        html_files.append(html_file)
    
    # Create index.html
    create_index_html(html_files, output_dir)
    
    print(f"\nAll files converted successfully. Open {os.path.join(output_dir, 'index.html')} to view the reports.")

def create_index_html(html_files, output_dir):
    """
    Create an index.html file with links to all HTML reports.
    
    Args:
        html_files (list): List of HTML file paths
        output_dir (str): Directory to save the index.html file
    """
    # Sort files by modification time (newest first)
    html_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    # Create links to HTML files
    links = ""
    for html_file in html_files:
        file_name = os.path.basename(html_file)
        # Make the filename more readable
        readable_name = os.path.splitext(file_name)[0]
        readable_name = readable_name.replace('_', ' ').title()
        
        # Get file modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(html_file)).strftime('%Y-%m-%d %H:%M:%S')
        
        links += f'<li><a href="{file_name}">{readable_name}</a> <span class="date">({mod_time})</span></li>\n'
    
    # HTML template for index.html
    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SEO Analysis Reports</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: #fff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        h1 {{
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
            color: #2980b9;
        }}
        ul {{
            list-style-type: none;
            padding: 0;
        }}
        li {{
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        li:last-child {{
            border-bottom: none;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
            font-weight: bold;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .date {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-left: 10px;
        }}
        .footer {{
            margin-top: 50px;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
            color: #2980b9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">SEO Analysis Reports</div>
        </div>
        
        <h1>Available Reports</h1>
        
        <ul>
            {links}
        </ul>
        
        <div class="footer">
            <p>Generated by SERP Analyzer | &copy; {datetime.now().year}</p>
        </div>
    </div>
</body>
</html>
"""

    # Write index.html
    index_file = os.path.join(output_dir, "index.html")
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    print(f"Created index file: {index_file}")

def main():
    # Check if a specific file is provided
    if len(sys.argv) > 1:
        md_file = sys.argv[1]
        if os.path.exists(md_file) and md_file.endswith('.md'):
            convert_md_to_html(md_file)
        else:
            print(f"File not found or not a markdown file: {md_file}")
    else:
        # Convert all markdown files in the analysis directory
        convert_all_md_files()

if __name__ == "__main__":
    main()
