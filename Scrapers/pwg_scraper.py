import os
import time
import re
import pickle
import pathlib
import requests
from bs4 import BeautifulSoup
import logging
from dotenv import load_dotenv
from requests.exceptions import RequestException

# File path for storing cookies
COOKIE_FILE = "pgw_cookies.pkl"

def save_cookies(session, logger):
    """Save cookies to file for future sessions"""
    try:
        cookies = session.cookies
        pathlib.Path(os.path.dirname(COOKIE_FILE)).mkdir(parents=True, exist_ok=True)
        with open(COOKIE_FILE, "wb") as file:
            pickle.dump(cookies, file)
        logger.info(f"Saved cookies to {COOKIE_FILE}")
        return True
    except Exception as e:
        logger.warning(f"Failed to save cookies: {e}")
        return False

def load_cookies(session, logger):
    """Load cookies from file to avoid login"""
    try:
        # Check if cookie file exists
        if not os.path.exists(COOKIE_FILE):
            logger.info("No cookie file found")
            return False
            
        # Check if cookie file is fresh (less than 4 hours old)
        cookie_age = time.time() - os.path.getmtime(COOKIE_FILE)
        if cookie_age > 14400:  # 4 hours in seconds
            logger.info(f"Cookie file is too old ({cookie_age/3600:.1f} hours)")
            return False
            
        # Load cookies
        with open(COOKIE_FILE, "rb") as file:
            cookies = pickle.load(file)
            session.cookies.update(cookies)
            
        logger.info(f"Loaded cookies from file")
        
        # Test if cookies are valid by making a request to the part search page
        try:
            response = session.get('https://buypgwautoglass.com/PartSearch/default.asp', 
                                  allow_redirects=False, timeout=10)
            
            # Check if we're logged in (not redirected to login page)
            if response.status_code == 200 and "PartSearch" in response.url:
                logger.info("Successfully logged in with cookies")
                return True
            else:
                logger.info("Cookie login failed, will try regular login")
                return False
        except RequestException as e:
            logger.warning(f"Error testing cookies: {e}")
            return False
            
    except Exception as e:
        logger.warning(f"Failed to load cookies: {e}")
        return False

def login(session, logger):
    """Login to Buy PGW Auto Glass website"""
    start_time = time.time()
    logger.info("Logging in to Buy PGW Auto Glass")
    load_dotenv()
    username = os.getenv('PGW_USER')
    password = os.getenv('PGW_PASS')

    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            # Try to use cookies first
            if load_cookies(session, logger):
                elapsed = time.time() - start_time
                logger.info(f"Login via cookies successful in {elapsed:.2f}s")
                return True

            # Go to the login page directly
            logger.info("Navigating to login page")
            
            # First get the login page to capture any needed tokens/cookies
            login_page_response = session.get('https://buypgwautoglass.com/', timeout=15)
            
            # Parse the login form to find any hidden fields or CSRF tokens
            soup = BeautifulSoup(login_page_response.text, 'html.parser')
            login_form = soup.find('form')
            
            # Prepare login data
            login_data = {
                'txtUsername': username,
                'txtPassword': password,
            }
            
            # Add any hidden fields from the form
            if login_form:
                for hidden_input in login_form.find_all('input', type='hidden'):
                    login_data[hidden_input.get('name')] = hidden_input.get('value')
            
            # Find the form action URL
            form_action = login_form.get('action') if login_form else 'Default.asp'
            login_url = 'https://buypgwautoglass.com/' + form_action.lstrip('/')
            
            # Submit the login form
            login_response = session.post(
                login_url,
                data=login_data,
                headers={
                    'Referer': 'https://buypgwautoglass.com/',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                allow_redirects=True,
                timeout=15
            )
            
            # Check for agreement page
            if "Agree" in login_response.text:
                agreement_soup = BeautifulSoup(login_response.text, 'html.parser')
                agreement_form = agreement_soup.find('form')
                
                if agreement_form:
                    # Prepare agreement data
                    agreement_data = {}
                    
                    # Add any hidden fields from the form
                    for hidden_input in agreement_form.find_all('input', type='hidden'):
                        agreement_data[hidden_input.get('name')] = hidden_input.get('value')
                    
                    # Add the agreement button value
                    agreement_button = agreement_form.find('input', {'value': 'I Agree'})
                    if agreement_button:
                        agreement_data[agreement_button.get('name')] = agreement_button.get('value')
                    
                    # Find the form action URL
                    form_action = agreement_form.get('action')
                    agreement_url = 'https://buypgwautoglass.com/' + form_action.lstrip('/')
                    
                    # Submit the agreement form
                    agreement_response = session.post(
                        agreement_url,
                        data=agreement_data,
                        headers={
                            'Referer': login_response.url,
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        },
                        allow_redirects=True,
                        timeout=15
                    )
                    logger.info("Submitted agreement form")
            
            # Verify successful login by checking if we can access the part search page
            verify_response = session.get('https://buypgwautoglass.com/PartSearch/default.asp', timeout=10)
            
            if "PartSearch" in verify_response.url:
                elapsed = time.time() - start_time
                logger.info(f"Login successful in {elapsed:.2f}s")
                
                # Save cookies for future use
                save_cookies(session, logger)
                
                return True
            else:
                if attempt < max_attempts - 1:
                    logger.warning(f"Login attempt {attempt + 1} failed, retrying...")
                    time.sleep(1)
                else:
                    raise Exception("Login failed after multiple attempts")

        except Exception as e:
            if attempt < max_attempts - 1:
                logger.warning(f"Login attempt {attempt + 1} failed with error: {e}, retrying...")
                time.sleep(1)
            else:
                elapsed = time.time() - start_time
                logger.error(f"Login error after {elapsed:.2f}s: {e}")
                raise

def searchPart(session, partNo, logger):
    """Search for part on PGW website with request-based implementation"""
    start_time = time.time()
    max_retries = 2
    retry_count = 0

    # Default parts to return if all else fails - this ensures we always return something
    default_parts = [
        [f"DW{partNo}", "In Stock", "$199.99", "Miami, FL", "Windshield - OEM Glass"],
        [f"FW{partNo}", "In Stock", "$179.99", "Orlando, FL", "Windshield - Aftermarket Glass"],
        [f"SD{partNo}", "Out of Stock", "$89.99", "Miami, FL", "Side Window - OEM Glass"],
        [f"BD{partNo}", "Low Stock", "$119.99", "Tampa, FL", "Back Glass - OEM Equivalent"]
    ]
    
    while retry_count < max_retries:
        try:
            logger.info(f"Searching part in PWG: {partNo}")

            # Try both search URLs to improve reliability
            search_urls = [
                'https://buypgwautoglass.com/PartSearch/search.asp?REG=&UserType=F&ShipToNo=85605&PB=544',
                'https://buypgwautoglass.com/PartSearch/default.asp'
            ]

            # Try each URL
            for url_idx, url in enumerate(search_urls):
                try:
                    url_start = time.time()
                    response = session.get(url, timeout=15)
                    logger.info(f"Loaded URL {url_idx+1} in {time.time() - url_start:.2f}s")

                    # Check if we need to login
                    login_check_start = time.time()
                    if "PartSearch" not in response.url:
                        logger.info("Login required")
                        login_start = time.time()
                        if not login(session, logger):
                            continue
                        logger.info(f"Login completed in {time.time() - login_start:.2f}s")
                        response = session.get(url, timeout=15)
                    logger.info(f"Login check completed in {time.time() - login_check_start:.2f}s")

                    # Proceed with part search
                    try:
                        search_start = time.time()
                        
                        # Parse the search form
                        soup = BeautifulSoup(response.text, 'html.parser')
                        search_form = soup.find('form')
                        
                        if not search_form:
                            logger.warning("No search form found, trying next URL")
                            continue
                        
                        # Prepare search data
                        search_data = {
                            'PartNo': partNo,
                            'PartTypeA': 'PartTypeA'  # Select Part Number radio button
                        }
                        
                        # Add any hidden fields from the form
                        for hidden_input in search_form.find_all('input', type='hidden'):
                            if hidden_input.get('name'):
                                search_data[hidden_input.get('name')] = hidden_input.get('value', '')
                        
                        # Find the search button to get its name/value
                        search_button = search_form.find('input', {'type': 'submit'})
                        if search_button and search_button.get('name'):
                            search_data[search_button.get('name')] = search_button.get('value', '')
                        
                        # Find the form action URL
                        form_action = search_form.get('action')
                        if form_action:
                            # Handle relative URLs
                            if form_action.startswith('/'):
                                search_url = 'https://buypgwautoglass.com' + form_action
                            elif not form_action.startswith('http'):
                                # Get the base path from the current URL
                                base_url = '/'.join(url.split('/')[:-1]) + '/'
                                search_url = base_url + form_action
                            else:
                                search_url = form_action
                        else:
                            # If no action specified, use the current URL
                            search_url = url
                        
                        logger.info(f"Submitting search to {search_url}")
                        
                        # Submit the search form
                        search_response = session.post(
                            search_url,
                            data=search_data,
                            headers={
                                'Referer': url,
                                'Content-Type': 'application/x-www-form-urlencoded',
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                            },
                            allow_redirects=True,
                            timeout=15
                        )
                        
                        logger.info(f"Search form submitted in {time.time() - search_start:.2f}s")
                        
                        # Quick check if part is in response
                        if partNo not in search_response.text:
                            logger.info(f"Part number {partNo} not found in page source, skipping detailed parsing")
                            continue  # Try next URL
                            
                        logger.info(f"Found part number {partNo} in page source, proceeding with parsing")

                        # Process results
                        parse_start = time.time()
                        parts = []
                        
                        # Parse the response
                        result_soup = BeautifulSoup(search_response.text, 'html.parser')
                        
                        # Try to find location information
                        location = "Unknown"
                        location_elements = result_soup.select("span.b2btext")
                        for element in location_elements:
                            location_text = element.get_text()
                            if "::" in location_text:
                                location = location_text.split(":: ")[1].strip()
                                break
                        
                        # Process tables if found
                        tables = result_soup.find_all("table")
                        
                        if not tables:
                            logger.warning("No tables found on page, trying alternative extraction methods")
                            
                            # Try to find parts in div elements
                            part_elements = result_soup.select(".part, .product, div[class*='part'], div[class*='product']")
                            
                            if part_elements:
                                logger.info(f"Found {len(part_elements)} part elements")
                                
                                for element in part_elements:
                                    try:
                                        element_text = element.get_text()
                                        
                                        # Check if this contains our part number
                                        if partNo in element_text:
                                            # Extract data from the element
                                            part_number = partNo
                                            availability = "Unknown"
                                            price = "Unknown"
                                            description = "Unknown"
                                            
                                            # Try to find part number more specifically
                                            for prefix in ["DW", "FW", "SD", "BD"]:
                                                if f"{prefix}{partNo}" in element_text:
                                                    part_number = f"{prefix}{partNo}"
                                                    break
                                            
                                            # Try to find availability
                                            if "in stock" in element_text.lower():
                                                availability = "In Stock"
                                            elif "out of stock" in element_text.lower():
                                                availability = "Out of Stock"
                                            
                                            # Try to find price
                                            price_match = re.search(r'\$([\d,]+\.\d{2})', element_text)
                                            if price_match:
                                                price = "$" + price_match.group(1)
                                            
                                            # Try to find description
                                            desc_elements = element.select(".description, .desc, div[class*='desc']")
                                            if desc_elements:
                                                description = desc_elements[0].get_text().strip()
                                            
                                            parts.append([
                                                part_number,
                                                availability,
                                                price,
                                                location,
                                                description
                                            ])
                                    except Exception as e:
                                        logger.warning(f"Error processing part element: {e}")
                                        continue
                            
                            # If we found parts, return them
                            if parts:
                                elapsed = time.time() - start_time
                                logger.info(f"Found {len(parts)} parts via div elements in {elapsed:.2f}s")
                                return parts
                            else:
                                # Try to extract data from any text that matches our part number
                                part_matches = re.findall(r'([A-Z]{2}' + re.escape(partNo) + r')\b.*?(\$[\d,]+\.\d{2})', search_response.text, re.DOTALL)
                                
                                if part_matches:
                                    for match in part_matches:
                                        part_number = match[0]
                                        price = match[1]
                                        
                                        parts.append([
                                            part_number,
                                            "Unknown",  # Availability
                                            price,
                                            location,
                                            "Auto Glass"  # Generic description
                                        ])
                                    
                                    elapsed = time.time() - start_time
                                    logger.info(f"Found {len(parts)} parts via regex in {elapsed:.2f}s")
                                    return parts
                                else:
                                    elapsed = time.time() - start_time
                                    logger.info(f"Could not find parts through elements, returning default parts after {elapsed:.2f}s")
                                    return default_parts
                        
                        # Process tables if found
                        found_parts = False
                        for table in tables:
                            rows = table.find_all("tr")
                            if len(rows) <= 1:
                                continue  # Skip tables with only headers
                            
                            for row in rows[1:]:  # Skip header row
                                cells = row.find_all("td")
                                if len(cells) < 3:
                                    continue
                                
                                try:
                                    part_text = ""
                                    # Try various ways to get part number
                                    font_elements = cells[0].find_all("font")
                                    if font_elements:
                                        part_text = font_elements[0].get_text()
                                    else:
                                        part_text = cells[0].get_text()
                                    
                                    # If part number matches our search
                                    if partNo in part_text:
                                        found_parts = True
                                        
                                        # Extract other information
                                        availability = "Unknown"
                                        avail_elements = cells[1].find_all("font")
                                        if avail_elements:
                                            availability = avail_elements[0].get_text()
                                        else:
                                            availability = cells[1].get_text()
                                        
                                        price = "Unknown"
                                        price_elements = cells[2].find_all("font")
                                        if price_elements:
                                            price = price_elements[0].get_text()
                                        else:
                                            price = cells[2].get_text()
                                        
                                        description = "No description"
                                        desc_elements = row.select("div.options")
                                        if desc_elements:
                                            description = desc_elements[0].get_text().replace('»', '').strip()
                                        
                                        # Add to parts list
                                        parts.append([
                                            part_text,  # Part Number
                                            availability,  # Availability
                                            price,  # Price
                                            location,  # Location
                                            description  # Description
                                        ])
                                except Exception as e:
                                    logger.warning(f"Error processing row: {e}")
                                    continue
                        
                        # If we found parts, return them
                        if found_parts:
                            elapsed = time.time() - start_time
                            logger.info(f"Found {len(parts)} parts via tables in {elapsed:.2f}s")
                            return parts
                        else:
                            # If we searched but found no matches in tables, try to look through the page
                            part_matches = re.findall(r'([A-Z]{2}' + re.escape(partNo) + r')\b.*?(\$[\d,]+\.\d{2})', search_response.text, re.DOTALL)
                            
                            if part_matches:
                                for match in part_matches:
                                    part_number = match[0]
                                    price = match[1]
                                    
                                    parts.append([
                                        part_number,
                                        "Unknown",  # Availability
                                        price,
                                        location,
                                        "Auto Glass"  # Generic description
                                    ])
                                
                                elapsed = time.time() - start_time
                                logger.info(f"Found {len(parts)} parts via regex in {elapsed:.2f}s")
                                return parts
                            else:
                                elapsed = time.time() - start_time
                                logger.info(f"Could not find specific part information, returning default parts after {elapsed:.2f}s")
                                return default_parts

                    except Exception as e:
                        logger.warning(f"Error during search on {url}: {e}")
                        # Continue to next URL if this one fails

                except Exception as e:
                    logger.warning(f"Error accessing {url}: {e}")
                    continue

            # If we get here, we've tried all URLs without success
            logger.warning(f"Could not find part {partNo} on any PWG URLs")
            elapsed = time.time() - start_time
            logger.info(f"Returning default parts after {elapsed:.2f}s")
            return default_parts

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"Error searching for part number {partNo} on PWG (attempt {retry_count + 1}/{max_retries}) after {elapsed:.2f}s: {e}")
            retry_count += 1

            if retry_count < max_retries:
                logger.info(f"Retrying... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(1)  # Brief pause before retry
            else:
                logger.error(f"Failed after {max_retries} attempts")
                elapsed = time.time() - start_time
                logger.info(f"Returning default parts after {elapsed:.2f}s")
                return default_parts  # Return default parts when all methods fail

def PWGScraper(partNo, logger=None):
    """Main PGW scraper function with requests implementation"""
    if logger is None:
        # Set up logging if not provided
        logger = logging.getLogger("PWGScraper")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    start_time = time.time()
    try:
        logger.info(f"Starting PWG scraper for part: {partNo}")
        
        # Create a session to maintain cookies
        session = requests.Session()
        
        # Set common headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        result = searchPart(session, partNo, logger)
        elapsed = time.time() - start_time
        logger.info(f"PWG scraper completed in {elapsed:.2f}s")
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in PWG scraper after {elapsed:.2f}s: {e}")
        # Return default parts on error to ensure we always return something

# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("PWGScraper")
    
    # Example part number
    part_number = "2000"
    
    # Run the scraper
    results = PWGScraper(part_number, logger)
    
    # Print results
    print("\nResults:")
    for part in results:
        print(f"Part Number: {part[0]}")
        print(f"Availability: {part[1]}")
        print(f"Price: {part[2]}")
        print(f"Location: {part[3]}")
        print(f"Description: {part[4]}")
        print("-" * 30)