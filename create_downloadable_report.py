import os
import sys
import shutil
import zipfile
from datetime import datetime

def create_downloadable_report(html_file, output_dir="downloadable_reports"):
    """
    Create a downloadable version of the HTML report.
    
    Args:
        html_file (str): Path to the HTML file
        output_dir (str): Directory to save the downloadable report
    
    Returns:
        str: Path to the downloadable report
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the base filename without extension
    base_name = os.path.basename(html_file)
    file_name = os.path.splitext(base_name)[0]
    
    # Create a directory for the report
    report_dir = os.path.join(output_dir, file_name)
    os.makedirs(report_dir, exist_ok=True)
    
    # Copy the HTML file to the report directory
    shutil.copy2(html_file, os.path.join(report_dir, "index.html"))
    
    # Create a PDF version of the HTML file (requires wkhtmltopdf)
    try:
        import pdfkit
        pdf_file = os.path.join(report_dir, f"{file_name}.pdf")
        pdfkit.from_file(html_file, pdf_file)
        print(f"Created PDF version: {pdf_file}")
    except ImportError:
        print("pdfkit not installed. Skipping PDF creation.")
        print("To create PDF files, install pdfkit and wkhtmltopdf:")
        print("pip install pdfkit")
        print("Download wkhtmltopdf from https://wkhtmltopdf.org/downloads.html")
    except Exception as e:
        print(f"Error creating PDF: {e}")
    
    # Create a ZIP file of the report directory
    zip_file = os.path.join(output_dir, f"{file_name}.zip")
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(report_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, report_dir)
                zipf.write(file_path, arcname)
    
    print(f"Created downloadable report: {zip_file}")
    return zip_file

def create_standalone_html(html_file, output_dir="downloadable_reports"):
    """
    Create a standalone HTML file with all resources embedded.
    
    Args:
        html_file (str): Path to the HTML file
        output_dir (str): Directory to save the standalone HTML file
    
    Returns:
        str: Path to the standalone HTML file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the base filename without extension
    base_name = os.path.basename(html_file)
    file_name = os.path.splitext(base_name)[0]
    
    # Read the HTML file
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Create a standalone HTML file
    standalone_file = os.path.join(output_dir, f"{file_name}_standalone.html")
    with open(standalone_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Created standalone HTML file: {standalone_file}")
    return standalone_file

def main():
    # Check if a specific file is provided
    if len(sys.argv) > 1:
        html_file = sys.argv[1]
        if os.path.exists(html_file) and html_file.endswith('.html'):
            create_downloadable_report(html_file)
            create_standalone_html(html_file)
        else:
            print(f"File not found or not an HTML file: {html_file}")
    else:
        # Process all HTML files in the html_reports directory
        html_dir = "html_reports"
        if os.path.exists(html_dir):
            html_files = [os.path.join(html_dir, f) for f in os.listdir(html_dir) if f.endswith('.html')]
            if html_files:
                for html_file in html_files:
                    create_downloadable_report(html_file)
                    create_standalone_html(html_file)
            else:
                print(f"No HTML files found in {html_dir}")
        else:
            print(f"Directory not found: {html_dir}")

if __name__ == "__main__":
    main()
