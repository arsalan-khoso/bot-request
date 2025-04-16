# scrapers/igc_scraper.py
# Import Glass Corp scraper - handles login, search, and result processing

import requests
import pickle
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import logging
import os

# Setup logger
logger = logging.getLogger(__name__)

class IGCScraper:
    def __init__(self):
        """Initialize the IGC Scraper with config and session"""
        self.session = requests.Session()
        
        # Constants
        self.base_url = "https://importglasscorp.com"
        self.search_url = f"{self.base_url}/product/search/"
        self.login_url = f"{self.base_url}/login/validate"
        self.concurrent_requests = 5  # Adjust for parallel requests
        
        # Default credentials (replace with your own in the login method)
        self.credentials = {
            "email": os.getenv('IGC_USER'),
            "customer_number": os.getenv('IGC_CN'),
            "password": os.getenv('IGC_PASS'),
        }
        
        # Headers
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": f"{self.base_url}/login",
            "Origin": self.base_url,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        # Cookies file
        self.cookies_file = 'igc_cookies.pkl'
        
        # Status tracking
        self.logged_in = False
        self.login_time = None
        self.login_response = None
    
    def login(self, email=None, customer_number=None, password=None):
        """
        Login to Import Glass Corp website
        
        Args:
            email: User's email address (optional if set in credentials)
            customer_number: User's customer number (optional if set in credentials)
            password: User's password (optional if set in credentials)
            
        Returns:
            Dictionary with login status and timing info
        """
        start_time = time.time()
        logger.info("[IGC] Starting login process")
        
        # Update credentials if provided
        if email:
            self.credentials["email"] = email
        if customer_number:
            self.credentials["customer_number"] = customer_number
        if password:
            self.credentials["password"] = password
        
        # Check if credentials are provided
        if not all([self.credentials["email"], self.credentials["customer_number"], self.credentials["password"]]):
            logger.error("[IGC] Missing credentials for login")
            return {
                "success": False,
                "message": "Missing credentials for login",
                "time_taken": time.time() - start_time
            }
        
        try:
            # First try to load cookies if available
            if self._load_cookies():
                # Verify if cookies are still valid
                if self._verify_login():
                    elapsed = time.time() - start_time
                    logger.info(f"[IGC] Login successful using saved cookies in {elapsed:.2f} seconds")
                    self.login_time = time.time()
                    
                    return {
                        "success": True,
                        "message": "Login successful using saved cookies",
                        "time_taken": elapsed
                    }
                else:
                    logger.info("[IGC] Saved cookies are invalid, performing fresh login")
            
            # Prepare login payload
            login_payload = self.credentials.copy()
            
            # Send login request
            logger.debug(f"[IGC] Sending login request for {self.credentials['email']}")
            response = self.session.post(self.login_url, data=login_payload, headers=self.headers)
            self.login_response = response
            
            # Check if login was successful
            soup = BeautifulSoup(response.text, 'html.parser')
            customer_info = soup.find('div', id='customer-info')
            
            if customer_info:
                self.logged_in = True
                self.login_time = time.time()
                logger.info("[IGC] Login successful!")
                
                # Save cookies for future use
                self._save_cookies()
                
                elapsed = time.time() - start_time
                return {
                    "success": True,
                    "message": "Login successful",
                    "time_taken": elapsed
                }
            else:
                self.logged_in = False
                logger.error(f"[IGC] Login failed. Status Code: {response.status_code}")
                logger.error(f"[IGC] Redirected to: {response.url}")
                logger.debug(f"[IGC] Response Snippet: {response.text[:500]}...")
                
                elapsed = time.time() - start_time
                return {
                    "success": False,
                    "message": "Login failed. Check credentials or website may be down.",
                    "time_taken": elapsed
                }
                
        except requests.RequestException as e:
            self.logged_in = False
            elapsed = time.time() - start_time
            logger.error(f"[IGC] Connection error during login: {str(e)}")
            return {
                "success": False,
                "message": f"Connection error: {str(e)}",
                "time_taken": elapsed
            }
        except Exception as e:
            self.logged_in = False
            elapsed = time.time() - start_time
            logger.error(f"[IGC] Unexpected error during login: {str(e)}")
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "time_taken": elapsed
            }
    
    def search(self, part_number):
        """
        Search for parts based on part number
        
        Args:
            part_number: The part number to search for
            
        Returns:
            Dictionary with search results and timing info
        """
        start_time = time.time()
        logger.info(f"[IGC] Searching for part number: {part_number}")
        
        # Check if logged in
        if not self.logged_in:
            # Try to login with saved credentials if available
            login_result = self.login()
            if not login_result["success"]:
                logger.error("[IGC] Not logged in and login failed")
                return {
                    "success": False,
                    "message": "Not logged in. Please login first.",
                    "time_taken": time.time() - start_time
                }
        
        try:
            # Prepare search data
            search_data = {'search': part_number}
            
            # Send search request
            logger.debug(f"[IGC] Sending search request for part: {part_number}")
            response = self.session.post(self.search_url, data=search_data, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"[IGC] Search request failed with status code {response.status_code}")
                return {
                    "success": False,
                    "message": f"Search request failed with status code: {response.status_code}",
                    "time_taken": time.time() - start_time
                }
            
            # Parse search results
            search_results = self._parse_search_results(response.text)
            
            elapsed = time.time() - start_time
            logger.info(f"[IGC] Found {len(search_results)} parts in search results in {elapsed:.2f} seconds")
            
            # Process part details if results found
            if search_results:
                details_result = self._process_all_parts(search_results)
                details_result["time_taken"] = time.time() - start_time
                return details_result
            else:
                return {
                    "success": True,
                    "message": f"No parts found for {part_number}",
                    "results": [],
                    "time_taken": elapsed
                }
                
        except requests.RequestException as e:
            elapsed = time.time() - start_time
            logger.error(f"[IGC] Connection error during search: {str(e)}")
            return {
                "success": False,
                "message": f"Connection error: {str(e)}",
                "time_taken": elapsed
            }
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[IGC] Unexpected error during search: {str(e)}")
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "time_taken": elapsed
            }
    
    def _load_cookies(self):
        """Load cookies from file if available"""
        try:
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'rb') as cookie_file:
                    cookies = pickle.load(cookie_file)
                    self.session.cookies.update(cookies)
                    logger.debug("[IGC] Cookies loaded successfully")
                    return True
            return False
        except Exception as e:
            logger.warning(f"[IGC] Error loading cookies: {str(e)}")
            return False
    
    def _save_cookies(self):
        """Save cookies to file"""
        try:
            with open(self.cookies_file, 'wb') as cookie_file:
                pickle.dump(self.session.cookies, cookie_file)
            logger.debug("[IGC] Cookies saved successfully")
            return True
        except Exception as e:
            logger.warning(f"[IGC] Error saving cookies: {str(e)}")
            return False
    
    def _verify_login(self):
        """Verify if current session is logged in"""
        try:
            # Try to access a page that requires login
            response = self.session.get(f"{self.base_url}/account", headers=self.headers)
            
            # Check if we're still logged in
            if "login" not in response.url.lower() and response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                customer_info = soup.find('div', id='customer-info')
                if customer_info:
                    self.logged_in = True
                    logger.debug("[IGC] Session verified as logged in")
                    return True
            
            self.logged_in = False
            logger.debug("[IGC] Session is not logged in")
            return False
        except Exception as e:
            self.logged_in = False
            logger.warning(f"[IGC] Error verifying login: {str(e)}")
            return False
    
    def _parse_search_results(self, html_content):
        """
        Parse the search results page HTML
        
        Args:
            html_content: HTML content of the search results page
        
        Returns:
            List of dictionaries containing part information
        """
        search_results = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            tables = soup.find_all('table')
            
            logger.debug(f"[IGC] Found {len(tables)} tables on the search results page")
            
            for table_idx, table in enumerate(tables):
                category = "Unknown"
                prev = table.find_previous('h4')
                if prev:
                    category = prev.get_text(strip=True)
                    logger.debug(f"[IGC] Table {table_idx+1} category: {category}")
                
                rows = table.find_all('tr')
                logger.debug(f"[IGC] Table {table_idx+1} has {len(rows)} rows")
                
                for row_idx, row in enumerate(rows):
                    cells = row.find_all('td')
                    if len(cells) < 3:
                        continue
                    
                    part_link = cells[0].find('a')
                    if not part_link:
                        continue
                    
                    part_number = part_link.get_text(strip=True)
                    part_url = part_link.get('href')
                    if part_url and not part_url.startswith('http'):
                        part_url = self.base_url + ('' if part_url.startswith('/') else '/') + part_url
                    
                    description = cells[1].get_text(strip=True)
                    
                    # Log the found part
                    logger.debug(f"[IGC] Found part: {part_number}, Description: {description}")
                    
                    search_results.append({
                        'part_number': part_number,
                        'description': description,
                        'category': category,
                        'url': part_url
                    })
            
            return search_results
            
        except Exception as e:
            logger.error(f"[IGC] Error parsing search results: {str(e)}")
            return []
    
    def _fetch_detail_page(self, url):
        """
        Fetch a detail page using the session
        
        Args:
            url: URL of the detail page
            
        Returns:
            HTML content of the page or None if failed
        """
        try:
            response = self.session.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"[IGC] Failed to fetch {url}, status code: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"[IGC] Error fetching {url}: {str(e)}")
            return None
    
    def _parse_detail_page(self, html_content, part_info):
        """
        Parse part detail page and extract data
        
        Args:
            html_content: HTML content of the detail page
            part_info: Original part dictionary
            
        Returns:
            List with part details or None if not found/not in Opa-Locka
        """
        if not html_content:
            return None
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find warehouse location
            location = "Unknown"
            location_elements = soup.find_all('b')
            for element in location_elements:
                text = element.get_text()
                if "Locka" in text or "Warehouse" in text:
                    location = text
                    break
            
            # If not in Opa-Locka, we might not want to include this part
            if location != "Unknown" and "Opa-Locka" not in location:
                logger.debug(f"[IGC] Part {part_info['part_number']} not available in Opa-Locka")
                return None
            
            # Find price and availability in tables
            tables = soup.find_all('table')
            if not tables:
                return None
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 5:
                        continue
                    
                    # Check if this row is for our part
                    row_part_number = cells[0].get_text(strip=True)
                    if part_info['part_number'] not in row_part_number:
                        continue
                    
                    # Extract price
                    price = "Unknown"
                    for i in range(2, min(5, len(cells))):
                        price_elements = cells[i].find_all('b')
                        for p_elem in price_elements:
                            price_text = p_elem.get_text(strip=True)
                            if "$" in price_text or any(c.isdigit() for c in price_text):
                                price = price_text
                                break
                    
                    # Extract availability
                    availability = "No"
                    for cell in cells:
                        cell_text = cell.get_text()
                        if "In Stock" in cell_text:
                            availability = "Yes"
                            break
                    
                    # Return the part details
                    return [
                        part_info["part_number"],
                        availability,
                        price,
                        location
                    ]
            
            return None
            
        except Exception as e:
            logger.warning(f"[IGC] Error parsing detail page for {part_info['part_number']}: {str(e)}")
            return [part_info["part_number"], "Unknown", "Unknown", "Unknown"]
    
    def _process_part_details(self, part_info):
        """
        Process a single part's details
        
        Args:
            part_info: Part dictionary with URL
            
        Returns:
            List with part details or None if failed/not found
        """
        start_time = time.time()
        
        try:
            # Fetch the detail page
            html_content = self._fetch_detail_page(part_info['url'])
            
            # Parse the details
            result = self._parse_detail_page(html_content, part_info)
            
            elapsed = time.time() - start_time
            if result:
                logger.debug(f"[IGC] Processed {part_info['part_number']} in {elapsed:.2f}s")
            else:
                logger.debug(f"[IGC] No matching data for {part_info['part_number']} in {elapsed:.2f}s")
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.warning(f"[IGC] Error processing {part_info['part_number']} after {elapsed:.2f} seconds: {str(e)}")
            return None
    
    def _process_all_parts(self, search_results):
        """
        Process all parts concurrently
        
        Args:
            search_results: List of part dictionaries from search
            
        Returns:
            Dictionary with processed results and metadata
        """
        start_time = time.time()
        logger.info(f"[IGC] Processing details for {len(search_results)} parts")
        
        if not search_results:
            return {
                "success": True,
                "message": "No parts to process",
                "results": [],
                "time_taken": time.time() - start_time
            }
        
        try:
            # Process parts in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.concurrent_requests) as executor:
                # Map the process_part_details function to all parts
                result_generator = executor.map(self._process_part_details, search_results)
                
                # Filter out None results and collect the valid ones
                results = [r for r in result_generator if r]
            
            # Log results
            for r in results:
                logger.info(f"[IGC] Matched Part: {r[0]}, Availability: {r[1]}, Price: {r[2]}, Location: {r[3]}")
            
            elapsed = time.time() - start_time
            logger.info(f"[IGC] Processed {len(results)}/{len(search_results)} parts in {elapsed:.2f} seconds")
            
            # Format results for return
            formatted_results = []
            for r in results:
                formatted_results.append({
                    "part_number": r[0],
                    "availability": r[1],
                    "price": r[2],
                    "location": r[3],
                    "supplier": "Import Glass Corp"
                })
            
            return {
                "success": True,
                "message": f"Found {len(results)} parts at Opa-Locka warehouse",
                "results": formatted_results,
                "time_taken": elapsed
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[IGC] Failed to process parts after {elapsed:.2f} seconds: {str(e)}")
            return {
                "success": False,
                "message": f"Error processing parts: {str(e)}",
                "results": [],
                "time_taken": elapsed
            }