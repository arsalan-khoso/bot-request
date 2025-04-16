# scrapers/mygrant_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import re
import logging
import os
from dotenv import load_dotenv

# Setup logger
logger = logging.getLogger(__name__)

def MyGrantScraper(partNo, driver=None, logger=logger):
    """
    Scrape part information from MyGrant website using requests
    
    Args:
        partNo: The part number to search
        driver: Not used in requests implementation, kept for compatibility
        logger: Logger instance
        
    Returns:
        List of parts in the format [part_number, availability, price, location]
    """
    # Load environment variables
    load_dotenv()
    username = os.getenv('MYGRANT_USER')
    password = os.getenv('MYGRANT_PASS')
    
    if not username or not password:
        logger.error("Missing Mygrant credentials in environment variables")
        return []
    
    start_time = time.time()
    max_retries = 2
    retry_count = 0
    base_url = "https://www.mygrantglass.com"
    login_url = f"{base_url}/pages/login.aspx"
    search_url = f"{base_url}/pages/search.aspx"
    
    # Headers for requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://www.mygrantglass.com/"
    }
    
    # Create session to maintain cookies
    session = requests.Session()
    
    while retry_count < max_retries:
        try:
            logger.info(f"[Mygrant] Searching for part number: {partNo}")
            
            # Step 1: Login
            logger.info("Logging in to MyGrant")
            
            # Get the login page to extract form tokens
            response = session.get(login_url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to get login page. Status code: {response.status_code}")
                retry_count += 1
                continue
                
            # Parse the login page
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form')
            
            if not form:
                logger.error("Could not find login form on page")
                retry_count += 1
                continue
                
            # Extract form fields
            form_data = {}
            
            # Add hidden fields
            for hidden_input in form.find_all('input', type='hidden'):
                if hidden_input.get('name') and hidden_input.get('value'):
                    form_data[hidden_input.get('name')] = hidden_input.get('value')
            
            # Find username field (using direct field names from your working code)
            username_field = "clogin:TxtUsername"
            password_field = "clogin:TxtPassword"
            submit_button = "clogin:ButtonLogin"
            
            # Add credentials to form data
            form_data[username_field] = username
            form_data[password_field] = password
            form_data[submit_button] = "Login"
            
            # Set headers for login POST
            post_headers = headers.copy()
            post_headers["Content-Type"] = "application/x-www-form-urlencoded"
            post_headers["Referer"] = login_url
            
            # Submit login form
            login_response = session.post(
                login_url,
                data=form_data,
                headers=post_headers,
                allow_redirects=True
            )
            
            # Check if login was successful
            if login_response.url == login_url:
                # Check for error messages
                error_soup = BeautifulSoup(login_response.text, 'html.parser')
                error_elements = error_soup.find_all(class_=lambda x: x and ('error' in x or 'alert' in x))
                
                if error_elements:
                    error_msg = error_elements[0].get_text().strip()
                    logger.error(f"Login failed: {error_msg}")
                    retry_count += 1
                    continue
            
            login_time = time.time() - start_time
            logger.info(f"[Mygrant] Login successful in {login_time:.2f} seconds!")
            
            # Step 2: Search for part - use direct GET query like your working code
            search_url_with_query = f"{search_url}?q={partNo}&do=Search"
            
            # Submit search request
            search_response = session.get(
                search_url_with_query,
                headers=headers,
                allow_redirects=True
            )
            
            # Check for HTTP errors
            if search_response.status_code != 200:
                logger.error(f"Search request failed. Status code: {search_response.status_code}")
                retry_count += 1
                continue
            
            # Parse search results
            soup = BeautifulSoup(search_response.text, 'html.parser')
            parts = []
            
            # Look for partnumber cells - using your working code approach
            partnumber_cells = soup.find_all(class_='partnumber')
            
            if partnumber_cells:
                logger.info(f"Found {len(partnumber_cells)} part cells")
                
                for cell in partnumber_cells:
                    # Find parent row
                    parent_row = cell.find_parent('tr')
                    if parent_row:
                        cells = parent_row.find_all('td')
                        
                        if len(cells) >= 3:
                            # Part number from the partnumber cell
                            part_link = cell.find('a')
                            part_num = part_link.get_text().strip() if part_link else cell.get_text().strip()
                            
                            # Stock status (cell 1)
                            stock_span = cells[1].find('span', class_=lambda x: x and 'stock_' in x)
                            stock = stock_span.get_text().strip() if stock_span else cells[1].get_text().strip()
                            
                            # Price (cell 3)
                            price = cells[3].get_text().strip() if len(cells) > 3 else "Unknown"
                            
                            # Add to parts list
                            parts.append([
                                part_num,
                                stock,
                                price,
                                "Unknown"  # Location placeholder
                            ])
                            logger.info(f"Extracted part: {part_num}")
            
            # If no parts found but part number is in page
            if not parts and partNo.lower() in search_response.text.lower():
                logger.info(f"Part {partNo} found in page but could not extract structured data, using fallback")
                parts.append([
                    partNo,
                    "Available - Check Store",
                    "Contact for Price",
                    "Unknown"
                ])
            
            # Return results
            elapsed = time.time() - start_time
            logger.info(f"[Mygrant] Search completed in {elapsed:.2f}s, found {len(parts)} results")
            return parts
            
        except requests.RequestException as e:
            logger.error(f"Connection error: {e}")
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Retrying... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(1)
            else:
                logger.error(f"Failed after {max_retries} attempts")
                return []
                
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Retrying... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(1)
            else:
                logger.error(f"Failed after {max_retries} attempts")
                return []
    
    # Should never reach here, but return empty list just in case
    return []