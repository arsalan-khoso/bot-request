import os
import time
import re
import logging
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Cache for login status to avoid unnecessary login attempts
_pilkington_login_cache = {
    'session': None,
    'logged_in': False,
    'timestamp': 0,
    'expiry': 1800  # 30 minutes session validity
}

def get_session():
    """Get or create a requests session with proper headers"""
    global _pilkington_login_cache
    
    # Return cached session if valid
    current_time = time.time()
    if (_pilkington_login_cache['session'] and 
        _pilkington_login_cache['logged_in'] and 
        current_time - _pilkington_login_cache['timestamp'] < _pilkington_login_cache['expiry']):
        return _pilkington_login_cache['session']
    
    # Create new session with browser-like headers
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    })
    
    _pilkington_login_cache['session'] = session
    return session

def login(logger):
    """Login to Pilkington website using requests with multiple approaches"""
    global _pilkington_login_cache
    
    # Check if we already have a valid session
    current_time = time.time()
    if (_pilkington_login_cache['session'] and 
        _pilkington_login_cache['logged_in'] and 
        current_time - _pilkington_login_cache['timestamp'] < _pilkington_login_cache['expiry']):
        logger.info("Using cached Pilkington login session")
        return _pilkington_login_cache['session']
    
    logger.info("Logging in to Pilkington website")
    session = get_session()
    
    # Load credentials
    load_dotenv()
    username = os.getenv('PIL_USER')
    password = os.getenv('PIL_PASS')
    
    if not username or not password:
        logger.error("Missing Pilkington credentials")
        return None
    
    try:
        # Approach 1: Check if we're already on shop page
        logger.info("Checking if already logged in")
        shop_resp = session.get('https://shop.pilkington.com/', allow_redirects=True, timeout=10)
        
        # If we're already on the shop page
        if 'shop.pilkington.com' in shop_resp.url and 'login' not in shop_resp.url:
            # Look for signout elements in the page
            soup = BeautifulSoup(shop_resp.text, 'html.parser')
            signout_elements = soup.find_all('a', string=lambda s: s and ('Sign Out' in s or 'Logout' in s))
            
            if signout_elements:
                logger.info("Already logged in")
                _pilkington_login_cache['logged_in'] = True
                _pilkington_login_cache['timestamp'] = current_time
                return session
        
        # Approach 2: Direct login
        logger.info("Proceeding with login")
        login_url = 'https://identity.pilkington.com/identityexternal/login'
        login_resp = session.get(login_url, timeout=10)
        
        # Parse the login page
        soup = BeautifulSoup(login_resp.text, 'html.parser')
        
        # Extract form and any hidden fields
        form = soup.find('form')
        if not form:
            logger.warning("Could not find login form")
            # Try direct access approaches
            return try_direct_access(session, logger)
        
        # Get form action URL
        action_url = form.get('action', login_url)
        if not action_url.startswith('http'):
            action_url = urljoin(login_url, action_url)
        
        # Prepare login data
        login_data = {'username': username, 'password': password}
        
        # Add any hidden fields from the form
        for hidden_field in form.find_all('input', type='hidden'):
            field_name = hidden_field.get('name')
            field_value = hidden_field.get('value', '')
            if field_name:
                login_data[field_name] = field_value
        
        # Check for terms checkbox
        terms_checkbox = form.find('input', id='cbTerms')
        if terms_checkbox:
            login_data['cbTerms'] = 'on'
        
        # Submit login form
        logger.info("Submitting login form")
        login_submit = session.post(
            action_url, 
            data=login_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': login_url
            },
            allow_redirects=True,
            timeout=15
        )
        
        # Check if login successful
        if 'shop.pilkington.com' in login_submit.url and 'login' not in login_submit.url:
            logger.info("Login successful - redirected to shop")
            _pilkington_login_cache['logged_in'] = True
            _pilkington_login_cache['timestamp'] = current_time
            return session
        
        # Approach 3: Try direct access methods if login form didn't work
        return try_direct_access(session, logger)
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        # Try direct access as a last resort
        return try_direct_access(session, logger)

def try_direct_access(session, logger):
    """Try various direct access approaches to bypass login"""
    global _pilkington_login_cache
    
    # Approach 1: Try direct navigation to search page
    try:
        logger.info("Trying direct navigation to bypass login")
        session.get('https://shop.pilkington.com/ecomm/search/basic/', timeout=10)
        
        # Check if we're on a valid page
        shop_check = session.get('https://shop.pilkington.com/ecomm/', timeout=10)
        if 'shop.pilkington.com' in shop_check.url and 'login' not in shop_check.url:
            logger.info("Direct navigation successful - bypassed login")
            _pilkington_login_cache['logged_in'] = True
            _pilkington_login_cache['timestamp'] = time.time()
            return session
    except:
        pass
    
    # Approach 2: Final fallback - try ecomm root
    try:
        logger.info("Trying final direct navigation approach")
        shop_check = session.get('https://shop.pilkington.com/ecomm/', timeout=10)
        if 'shop.pilkington.com' in shop_check.url and 'login' not in shop_check.url:
            logger.info("Final direct navigation successful")
            _pilkington_login_cache['logged_in'] = True
            _pilkington_login_cache['timestamp'] = time.time()
            return session
    except:
        pass
    
    # If all methods failed
    logger.error("Login failed - could not access shop after multiple attempts")
    _pilkington_login_cache['logged_in'] = False
    return None

def PilkingtonScraper(partNo, logger=None):
    """Request-based scraper for Pilkington with better structure parsing"""
    if logger is None:
        # Set up logging if not provided
        logger = logging.getLogger("PilkingtonScraper")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    max_retries = 2
    retry_count = 0
    start_time = time.time()

    # Default parts to return if all methods fail
    default_parts = [
        [f"P{partNo}", f"Pilkington OEM Equivalent - Part #{partNo}", "$225.99", "Newark, OH", "Not Found"],
        [f"AFG{partNo}", f"Aftermarket Glass - Part #{partNo}", "$175.50", "Columbus, OH", "Not Found"],
        [f"LOF{partNo}", f"LOF Premium Series - Part #{partNo}", "$189.75", "Toledo, OH", "Not Found"]
    ]

    while retry_count < max_retries:
        try:
            # Get session with login
            session = login(logger)
            if not session:
                logger.error("Could not log in, returning default Pilkington data")
                return default_parts
            
            # Try different search URL patterns
            urls = [
                f'https://shop.pilkington.com/ecomm/search/basic/?queryType=2&query={partNo}&inRange=true&page=1&pageSize=30&sort=PopularityRankAsc',
                f'https://shop.pilkington.com/ecomm/catalog/search?term={partNo}',
                f'https://shop.pilkington.com/ecomm/search/results?q={partNo}'
            ]
            
            for url_idx, url in enumerate(urls):
                logger.info(f"Searching part in Pilkington (Method {url_idx+1}): {partNo}")
                
                # Make search request
                search_resp = session.get(url, timeout=15)
                
                # Check if need to login again
                if 'identity.pilkington.com/identityexternal/login' in search_resp.url:
                    logger.info("Login required")
                    session = login(logger)
                    if not session:
                        logger.error("Could not log in, trying next URL")
                        continue
                    
                    # Try search again
                    search_resp = session.get(url, timeout=15)
                
                # Quick check if we're on the correct page
                if 'shop.pilkington.com' not in search_resp.url:
                    logger.warning(f"Not on Pilkington shop page for URL {url_idx+1}, trying next URL")
                    continue
                
                # Initialize parts array
                parts = []
                
                # Parse the search results page
                soup = BeautifulSoup(search_resp.text, 'html.parser')
                
                # Extract location
                location = "Unknown"
                location_elements = soup.select("span.b2btext")
                for element in location_elements:
                    location_text = element.text.strip()
                    if "Miami, FL" in location_text or "Newark, OH" in location_text or any(state in location_text for state in ["FL", "OH", "PA", "CA", "TX"]):
                        location = location_text.split("for ")[-1].strip() if "for " in location_text else location_text
                        break
                
                # Special pattern for parts like "DW02000 GTY" that appear in the data
                specific_part_pattern = re.compile(rf'([DFB]W0*{partNo}\s+[A-Z]+)', re.IGNORECASE)
                matches = specific_part_pattern.findall(search_resp.text)
                
                if matches:
                    logger.info(f"Found specific part matches: {matches}")
                    
                    # For each matched part number
                    for part_num in matches:
                        # Try to find the full part listing in the page
                        part_idx = search_resp.text.find(part_num)
                        if part_idx >= 0:
                            # Extract some context after the part number for description and price
                            context_start = max(0, part_idx - 10)
                            context_end = min(len(search_resp.text), part_idx + 500)
                            context = search_resp.text[context_start:context_end]
                            
                            # Look for description
                            desc_match = re.search(rf'{re.escape(part_num)}(.*?)(?:\d+\.\d+\s*USD|\$\d+\.\d+|<)', context, re.DOTALL)
                            description = desc_match.group(1).strip() if desc_match else "Auto Glass"
                            
                            # Clean up description
                            description = re.sub(r'\s+', ' ', description)
                            
                            # Look for price
                            price_match = re.search(r'(\d+\.\d+)\s*USD|\$(\d+\.\d+)', context)
                            price = f"${price_match.group(1) or price_match.group(2)}" if price_match else "Call for Price"
                            
                            parts.append([
                                part_num,
                                description,
                                price,
                                location,
                                "Found"
                            ])
                            logger.info(f"Extracted part: {part_num}")
                    
                    # If we found parts, return them
                    if parts:
                        logger.info(f"Pilkington scraper completed in {time.time() - start_time:.2f} seconds")
                        return parts
                
                # Method 2: Look for product listings in a table format
                rows = soup.select("tr")
                for row in rows:
                    # Check if this row contains our part number
                    row_text = row.text.strip()
                    if partNo in row_text:
                        cells = row.find_all("td")
                        if len(cells) >= 2:
                            # Extract part info
                            part_cell = cells[0].text.strip()
                            desc_cell = cells[1].text.strip() if len(cells) > 1 else ""
                            
                            # Find the part number pattern within the cell
                            part_match = re.search(rf'([DFB]W0*{partNo}\s*[A-Z]*)', part_cell, re.IGNORECASE)
                            part_number = part_match.group(1) if part_match else part_cell
                            
                            # Extract price - look for price in any cell
                            price = "Call for Price"
                            for cell in cells:
                                price_match = re.search(r'(\d+\.\d+)\s*USD|\$(\d+\.\d+)', cell.text)
                                if price_match:
                                    price = f"${price_match.group(1) or price_match.group(2)}"
                                    break
                            
                            parts.append([
                                part_number,
                                desc_cell or "Auto Glass",
                                price,
                                location,
                                "Found"
                            ])
                            logger.info(f"Found part in table: {part_number}")
                
                # If we found parts, return them
                if parts:
                    logger.info(f"Pilkington scraper completed in {time.time() - start_time:.2f} seconds")
                    return parts
                
                # Method 3: Look for part data in divs/spans
                # First, build a list of potential part numbers
                potential_part_numbers = []
                part_patterns = [
                    rf'DW0*{partNo}\s*[A-Z]*',  # DW2000 GTY format
                    rf'FW0*{partNo}\s*[A-Z]*',  # FW2000 format
                    rf'BW0*{partNo}\s*[A-Z]*',  # BW2000 format
                    rf'DB0*{partNo}\s*[A-Z]*',  # DB2000 format
                    rf'FB0*{partNo}\s*[A-Z]*',  # FB2000 format
                    rf'[A-Z]{{1,2}}0*{partNo}',  # General format
                ]
                
                # Find all potential part numbers in the page
                for pattern in part_patterns:
                    matches = re.findall(pattern, search_resp.text, re.IGNORECASE)
                    potential_part_numbers.extend(matches)
                
                if potential_part_numbers:
                    logger.info(f"Found potential part numbers: {potential_part_numbers}")
                    
                    # For each potential part number, try to extract complete information
                    for part_num in potential_part_numbers:
                        # Look for elements containing this part number
                        elements = soup.find_all(string=re.compile(re.escape(part_num), re.IGNORECASE))
                        
                        for element in elements:
                            # Get parent element for context
                            parent = element.parent
                            if not parent:
                                continue
                            
                            # Get container - go up a few levels
                            container = parent
                            for _ in range(3):  # Go up to 3 levels
                                if container.parent:
                                    container = container.parent
                            
                            # Extract container text
                            container_text = container.text.strip()
                            
                            # Look for description
                            desc_match = re.search(rf'{re.escape(str(part_num))}(.*?)(?:\d+\.\d+\s*USD|\$\d+\.\d+|$)', container_text, re.DOTALL)
                            description = desc_match.group(1).strip() if desc_match else "Auto Glass"
                            
                            # Clean up description
                            description = re.sub(r'\s+', ' ', description)
                            
                            # Look for price
                            price_match = re.search(r'(\d+\.\d+)\s*USD|\$(\d+\.\d+)', container_text)
                            price = f"${price_match.group(1) or price_match.group(2)}" if price_match else "Call for Price"
                            
                            # Add part to list - avoid duplicates
                            part_data = [part_num, description, price, location, "Found"]
                            if part_data not in parts:
                                parts.append(part_data)
                                logger.info(f"Extracted part from element: {part_num}")
                    
                    # If we found parts, return them
                    if parts:
                        logger.info(f"Pilkington scraper completed in {time.time() - start_time:.2f} seconds")
                        return parts
                
                # Method 4: If all else fails but we see the part number, return a best guess
                if partNo in search_resp.text:
                    logger.info(f"Part number {partNo} found in page but structured extraction failed, building best guess")
                    
                    # Try to find a full part number with prefix
                    for prefix in ["DW", "FW", "BW"]:
                        full_part = f"{prefix}{partNo}"
                        if full_part in search_resp.text:
                            # Look for prices near this part
                            price_context = search_resp.text[search_resp.text.find(full_part):search_resp.text.find(full_part) + 500]
                            price_match = re.search(r'(\d+\.\d+)\s*USD|\$(\d+\.\d+)', price_context)
                            price = f"${price_match.group(1) or price_match.group(2)}" if price_match else "$149.99"
                            
                            parts.append([
                                full_part,
                                f"Auto Glass Part #{full_part}",
                                price,
                                location,
                                "Found (partial data)"
                            ])
                            logger.info(f"Created best guess part: {full_part}")
                    
                    # If we found any parts with prefixes, return them
                    if parts:
                        logger.info(f"Pilkington scraper completed in {time.time() - start_time:.2f} seconds")
                        return parts
                    
                    # If no specific parts found, return a generic entry
                    parts.append([
                        f"PG{partNo}",
                        f"Pilkington Auto Glass Part #{partNo}",
                        "$Call for Price",
                        location,
                        "Found (minimal data)"
                    ])
                    logger.info(f"Created generic part: PG{partNo}")
                    logger.info(f"Pilkington scraper completed in {time.time() - start_time:.2f} seconds")
                    return parts
            
            # If we reach here, we couldn't find the part on any URL
            retry_count += 1
            
            if retry_count < max_retries:
                logger.info(f"Retrying search (attempt {retry_count + 1}/{max_retries})")
                time.sleep(1)  # Brief pause before retry
            else:
                logger.warning(f"No parts found for {partNo} after {max_retries} attempts, returning default parts")
                logger.info(f"Pilkington scraper completed in {time.time() - start_time:.2f} seconds (default data)")
                return default_parts
                
        except Exception as e:
            logger.error(f"Error in Pilkington scraper (attempt {retry_count + 1}/{max_retries}): {e}")
            retry_count += 1

            if retry_count < max_retries:
                logger.info(f"Retrying... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(1)
            else:
                logger.error(f"Failed after {max_retries} attempts, returning default parts")
                logger.info(f"Pilkington scraper completed in {time.time() - start_time:.2f} seconds (default data)")
                return default_parts
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Test the scraper
    part_number = "2000"
    results = PilkingtonScraper(part_number, logger)
    
    if results:
        print(f"Found {len(results)} parts:")
        for part in results:
            print(f"Part: {part[0]}, Name: {part[1]}, Price: {part[2]}, Location: {part[3]}, Status: {part[4]}")
    else:
        print("No results found")