import json
from bs4 import BeautifulSoup
import re

def extract_results_from_html(html_file, num_results=6):
    print("\n" + "="*80)
    print(" PARSING SAVED HTML FILE ".center(80, "="))
    print("="*80 + "\n")
    
    try:
        # Read the HTML file
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"Successfully read HTML file: {html_file}")
        print(f"HTML content length: {len(html_content)} characters\n")
        
        # Parse the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get the page title
        page_title = soup.title.text if soup.title else "No title found"
        print(f"Page title: {page_title}\n")
        
        # Check for CAPTCHA or block page
        if "captcha" in html_content.lower() or "unusual traffic" in html_content.lower():
            print("CAPTCHA or block detected in HTML content")
            return []
        
        # Direct extraction of search results
        search_results = []
        
        # Method 1: Extract all links
        links = soup.find_all('a')
        print(f"Found {len(links)} links in total")
        
        # Filter links that look like search results
        result_links = []
        for link in links:
            href = link.get('href', '')
            # Skip Google's own links and other non-result URLs
            if href.startswith('http') and 'google' not in href.lower():
                result_links.append(link)
        
        print(f"Filtered to {len(result_links)} potential result links\n")
        
        # Process each potential result link
        for i, link in enumerate(result_links):
            if i >= num_results:
                break
                
            href = link.get('href', '')
            
            # Get the title from the link text or nearby h3
            title = link.get_text().strip()
            if not title:
                # Try to find a nearby h3
                parent = link.parent
                for _ in range(3):  # Look up to 3 levels up
                    if parent and parent.find('h3'):
                        title = parent.find('h3').get_text().strip()
                        break
                    if parent:
                        parent = parent.parent
            
            # Skip if no title
            if not title:
                continue
            
            # Try to find a description
            description = ""
            parent = link.parent
            for _ in range(3):  # Look up to 3 levels up
                if parent:
                    # Find any div that might contain a description
                    for div in parent.find_all('div'):
                        text = div.get_text().strip()
                        if len(text) > 50 and text != title:  # Reasonable description length
                            description = text
                            break
                    if description:
                        break
                    parent = parent.parent
            
            # Add to results
            search_results.append({
                "title": title,
                "url": href,
                "description": description,
                "position": len(search_results) + 1
            })
            
            # Print the result
            print(f"Result #{len(search_results)}:")
            print(f"  Title: {title[:50]}..." if len(title) > 50 else f"  Title: {title}")
            print(f"  URL: {href}")
            print(f"  Description: {description[:50]}..." if len(description) > 50 else f"  Description: {description}")
            print("-" * 40)
        
        # Method 2: Try to find result containers
        if not search_results:
            print("\nTrying to find result containers...")
            
            # Try different selectors for result containers
            selectors = [
                'div.g', 'div.tF2Cxc', 'div.yuRUbf', 'div.rc', 
                'div[data-header-feature]', 'div.MjjYud', 'div.Gx5Zad'
            ]
            
            for selector in selectors:
                containers = soup.select(selector)
                print(f"Selector '{selector}' found {len(containers)} elements")
                
                if containers:
                    for i, container in enumerate(containers):
                        if i >= num_results:
                            break
                            
                        # Try to extract title and URL
                        title_elem = container.select_one('h3')
                        title = title_elem.get_text().strip() if title_elem else ""
                        
                        link_elem = container.select_one('a')
                        url = link_elem.get('href', '') if link_elem else ""
                        
                        # Skip if no valid URL
                        if not url or not url.startswith('http'):
                            continue
                            
                        # Try to extract description
                        description = ""
                        desc_elem = container.select_one('div.VwiC3b') or container.select_one('span.st') or container.select_one('div.s')
                        if desc_elem:
                            description = desc_elem.get_text().strip()
                        
                        # Add to results
                        search_results.append({
                            "title": title,
                            "url": url,
                            "description": description,
                            "position": len(search_results) + 1
                        })
                        
                        # Print the result
                        print(f"Result #{len(search_results)}:")
                        print(f"  Title: {title[:50]}..." if len(title) > 50 else f"  Title: {title}")
                        print(f"  URL: {url}")
                        print(f"  Description: {description[:50]}..." if len(description) > 50 else f"  Description: {description}")
                        print("-" * 40)
                    
                    # If we found results with this selector, stop trying others
                    if search_results:
                        break
        
        # Method 3: Try regex extraction as a last resort
        if not search_results:
            print("\nTrying regex extraction as a last resort...")
            
            # Pattern to match URLs in Google search results
            url_pattern = r'<a href="(https?://[^"]+)"[^>]*>([^<]+)</a>'
            matches = re.findall(url_pattern, html_content)
            
            for i, (url, title) in enumerate(matches):
                if i >= num_results:
                    break
                    
                # Filter out Google's own URLs and other non-result URLs
                if 'google.com' in url or 'accounts.google' in url or 'support.google' in url:
                    continue
                    
                # Clean up title
                title = title.strip()
                if not title:
                    continue
                    
                # Add to results
                search_results.append({
                    "title": title,
                    "url": url,
                    "description": "",  # No description available with regex
                    "position": len(search_results) + 1
                })
                
                # Print the result
                print(f"Result #{len(search_results)}:")
                print(f"  Title: {title[:50]}..." if len(title) > 50 else f"  Title: {title}")
                print(f"  URL: {url}")
                print(f"  Description: No description available")
                print("-" * 40)
        
        # Save the results to a JSON file
        if search_results:
            with open("parsed_results.json", "w", encoding="utf-8") as f:
                json.dump(search_results, f, indent=2, ensure_ascii=False)
            print(f"\nSaved {len(search_results)} results to parsed_results.json")
        else:
            print("\nNo results found in the HTML file")
        
        return search_results
        
    except Exception as e:
        print(f"Error parsing HTML file: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    results = extract_results_from_html("google_search_debug.html")
    print(f"\nExtracted {len(results)} results from the HTML file")
