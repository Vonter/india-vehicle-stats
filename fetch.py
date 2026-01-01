import requests
import xml.etree.ElementTree as ET
import os
import datetime
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from functools import wraps
import argparse
import json
import traceback
import time
import re

# Global variables
BUTTONS = {}
YEARS = ['2026', '2025', '2024', '2023', '2022']
MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
STATES = [
    'KA',
    'AP', 'AR', 'AS', 'BR', 'CG', 'GA', 'GJ', 'HR', 'HP', 'JH',
    'KA', 'KL', 'MP', 'MH', 'MN', 'ML', 'MZ', 'NL', 'OD', 'PB',
    'RJ', 'SK', 'TN', 'TS', 'TR', 'UK', 'UP', 'WB', 'AN', 'CH',
    'DN', 'DD', 'DL', 'LD', 'PY', 'JK'
]
URL = "https://vahan.parivahan.gov.in/vahan4dashboard/"

# Panel types for registration data
REGISTRATION_PANELS = {
    'panel_vhClass': 'registration_class',
    'panel_vhCatg': 'registration_category',
    'panel_fuel': 'registration_fuel',
    'panel_norms': 'registration_standard',
    'panel_maker': 'registration_manufacturer'
}

# Panel types for transaction data
TRANSACTION_PANELS = {
    'panel_trans': 'transaction'
}

# Panel types for revenue data
REVENUE_PANELS = {
    'panel_rev_fee': 'revenue_fee',
    'panel_rev_tax': 'revenue_tax'
}

# Panel types for permit data
PERMIT_PANELS = {
    'panel_permitType': 'permit_type',
    'panel_permitCatg': 'permit_category',
    'panel_permitPurpose': 'permit_purpose'
}

# All panel types combined
ALL_PANELS = {
    'regn': REGISTRATION_PANELS,
    'trans': TRANSACTION_PANELS,
    'revenue': REVENUE_PANELS,
    'permit': PERMIT_PANELS
}

# Utility functions
def setup_logger(debug=False):
    """Set up and configure the logger.
    
    Args:
        debug: If True, enable debug logging. If False, only log INFO and above.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Create handlers
    stdout_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('debug.log')

    # Set levels for handlers
    stdout_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)

    # Create formatters
    stdout_formatter = logging.Formatter('%(levelname)s: %(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    stdout_handler.setFormatter(stdout_formatter)
    file_handler.setFormatter(file_formatter)

    # Add handlers to logger
    logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)

    return logger

logger = None  # Will be initialized in main

# Custom exception for view expiration
class ViewExpiredException(Exception):
    """Exception raised when the view state expires."""
    pass

def parse_state_rtos(state_html):
    """Parse RTO options from state HTML response and save list of RTOs to raw/rtos.txt."""
    # HTML fragments from AJAX responses are HTML, not XML
    soup = BeautifulSoup(state_html, 'html.parser')
    options = soup.find_all('option')[1:]  # Skip first placeholder option
    
    # Extract RTO values and text content
    rtos = [opt.get('value') for opt in options if opt.get('value')]
    rto_texts = [opt.get_text(strip=True) for opt in options if opt.get_text(strip=True)]
    
    if rto_texts:
        rtos_file = Path('raw/rtos.txt')
        rtos_file.parent.mkdir(exist_ok=True)
        
        # Load existing RTOs, add new ones, sort and save
        existing = set()
        if rtos_file.exists():
            existing = set(rtos_file.read_text(encoding='utf-8').strip().split('\n'))
        
        existing.update(rto_texts)
        rtos_file.write_text('\n'.join(sorted(existing)) + '\n', encoding='utf-8')
    
    return rtos

def save_to_file(data, state, rto, year, month, category, file_suffix):
    """Save data to a file, creating directories if needed.
    
    Args:
        data: The data to save
        state: State code for subdirectory organization
        rto: RTO code for subdirectory organization
        year: Year for subdirectory organization
        month: Month for subdirectory organization
        category: Category for subdirectory organization
        file_suffix: Suffix for the file name
    """
    # Normalize filepath components
    month = month.lower()
    category_mapping = {'regn': 'registration', 'trans': 'transaction', 'revenue': 'revenue', 'permit': 'permit'}
    category = category_mapping[category]
    if '_' in file_suffix:
        file_suffix = file_suffix.split('_')[1]

    # Create the state-specific subdirectory path
    filepath = os.path.join('raw', state, rto, year, month, category, f'{file_suffix}.html')
    
    # Create the directory if it doesn't exist
    Path(os.path.dirname(filepath)).mkdir(parents=True, exist_ok=True)

    # Check if the data contains the expected content
    if 'class="ui-panel ui-widget ui-widget-content ui-corner-all"' not in data:
        raise Exception("Expected content not found in data, possible incomplete fetch")

    # Write the data to the file
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(data)

def create_blank_html_file(file_suffix, state=None, rto=None, year=None, month=None, category=None):
    """Create a blank HTML file with minimal valid structure.
    
    Args:
        file_suffix: The suffix of the file to create
        state: State code for subdirectory organization
        rto: RTO code for subdirectory organization
        year: Year for subdirectory organization
        month: Month for subdirectory organization
        category: Category for subdirectory organization
    """
    # Normalize filepath components
    month = month.lower()
    category_mapping = {'regn': 'registration', 'trans': 'transaction', 'revenue': 'revenue', 'permit': 'permit'}
    category = category_mapping[category]
    if '_' in file_suffix:
        file_suffix = file_suffix.split('_')[1]

    # Create the state-specific subdirectory path
    filepath = os.path.join('raw', state, rto, year, month, category, f'{file_suffix}.html')
    
    # Create the directory if it doesn't exist
    Path(os.path.dirname(filepath)).mkdir(parents=True, exist_ok=True)
    
    # Create a minimal valid HTML content with the expected panel class
    blank_html = """
    <div class="ui-panel ui-widget ui-widget-content ui-corner-all">
        <div class="ui-panel-content ui-widget-content">
            <p>No data available - blank file created due to missing month ID.</p>
        </div>
    </div>
    """
    
    # Write the data to the file
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(blank_html)

def retry_on_view_expired(max_retries=3):
    """Decorator to retry functions when ViewExpiredException occurs.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            attempt = 0
            while attempt < max_retries:
                try:
                    return func(self, *args, **kwargs)
                except ViewExpiredException:
                    attempt += 1
                    if attempt >= max_retries:
                        logger.error(
                            f"{func.__name__} failed with ViewExpiredException after {max_retries} attempts"
                        )
                        raise
                    
                    logger.warning(
                        f"{func.__name__} failed with ViewExpiredException. "
                        f"Retrying (attempt {attempt}/{max_retries})..."
                    )
                    # Exponential backoff
                    time.sleep(1 * attempt)
                    self._reset_session()
                    # Re-initialize session after reset
                    try:
                        self.initialize()
                    except Exception as e:
                        logger.error(f"Failed to re-initialize session: {str(e)}")
                        if attempt >= max_retries - 1:
                            raise
            return False
        return wrapper
    return decorator

class VahanFetcher:
    """Class to fetch vehicle registration data from Vahan dashboard."""
    
    def __init__(self, completed_fetches=None, fetch_all=False, 
                 years_filter=None, months_filter=None, 
                 states_filter=None, rtos_filter=None):
        """Initialize the VahanFetcher with default settings.
        
        Args:
            completed_fetches: Dictionary of completed fetches
            fetch_all: If True, fetch all historical data
            years_filter: List of years to fetch (e.g., ['2024', '2025']). None means all.
            months_filter: List of months to fetch (e.g., ['JAN', 'FEB']). None means all.
            states_filter: List of state codes to fetch (e.g., ['KA', 'MH']). None means all.
            rtos_filter: Dictionary mapping state codes to lists of RTO codes to fetch.
                        Format: {'KA': ['KA01', 'KA02'], 'MH': ['MH01']}. None means all.
        """
        self.session = requests.Session()
        # Set headers globally to match browser behavior
        self._set_global_headers()
        self.viewstate = None
        self.current_date = datetime.datetime.now()
        self.session_start_time = datetime.datetime.now()
        # Session timeout is 15 minutes (900 seconds) based on page meta refresh
        self.session_timeout = 900
        self.last_request_time = None
        
        # Element IDs for various dashboard components
        self.buttons = {}
        # Store year IDs per category
        self.years = {
            'regn': {},
            'trans': {},
            'revenue': {},
            'permit': {}
        }
        self.months = {}
        self.completed_fetches = completed_fetches if completed_fetches is not None else {}
        self.fetch_all = fetch_all
        
        # Filter parameters - convert to sets for faster lookups
        self.years_filter = set(years_filter) if years_filter else None
        self.months_filter = set([m.upper() for m in months_filter]) if months_filter else None
        self.states_filter = set(states_filter) if states_filter else None
        # rtos_filter is already a dict of state -> set of RTOs from main
        self.rtos_filter = rtos_filter if rtos_filter else None
    
    def _set_global_headers(self):
        """Set global headers for all requests to match browser behavior."""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:145.0) Gecko/20100101 Firefox/145.0',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': URL
        })
    
    def _get_parser(self, content, content_type=None):
        """Determine the appropriate parser for BeautifulSoup based on content.
        
        Args:
            content: The content to parse (bytes or str)
            content_type: Optional content type hint
            
        Returns:
            Tuple of (parser_name, is_xml)
        """
        # Check content type header if available
        if content_type:
            if 'xml' in content_type.lower():
                return 'xml', True
            if 'html' in content_type.lower():
                return 'html.parser', False
        
        # Check content itself
        if isinstance(content, bytes):
            content_str = content[:500].decode('utf-8', errors='ignore')
        else:
            content_str = str(content)[:500]
        
        # Check for XML indicators
        if content_str.strip().startswith('<?xml') or '<partial-response>' in content_str:
            return 'xml', True
        
        # Default to HTML parser
        return 'html.parser', False
    
    def _make_request_with_timeout(self, method, url, timeout=30, **kwargs):
        """Make a request with timeout handling and automatic retry on timeout.
        
        Args:
            method: HTTP method ('get' or 'post')
            url: URL to request
            timeout: Timeout in seconds (default: 30)
            **kwargs: Additional arguments to pass to requests method
            
        Returns:
            Response object
            
        Raises:
            requests.exceptions.Timeout: If request times out after retries
            requests.exceptions.RequestException: For other request errors
        """
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                start_time = time.time()
                
                if method.lower() == 'get':
                    response = self.session.get(url, timeout=timeout, **kwargs)
                elif method.lower() == 'post':
                    response = self.session.post(url, timeout=timeout, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                elapsed = time.time() - start_time
                
                # Log if request took a long time
                if elapsed > 10:
                    logger.warning(f"{method.upper()} request to {url} took {elapsed:.2f} seconds")
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"{method.upper()} request to {url} timed out after {max_retries + 1} attempts")
                    raise
                else:
                    wait_time = 2 * retry_count  # Exponential backoff
                    logger.warning(f"{method.upper()} request to {url} timed out, retrying in {wait_time}s (attempt {retry_count}/{max_retries})...")
                    time.sleep(wait_time)
                    # Refresh session on timeout
                    if retry_count == 1:
                        try:
                            self._refresh_session()
                        except Exception as e:
                            logger.warning(f"Failed to refresh session after timeout: {str(e)}")
    
    def _check_session_validity(self):
        """Check if session is still valid and refresh if needed.
        
        The page auto-refreshes every 15 minutes (900 seconds), so we should
        proactively refresh the session before it expires.
        """
        if self.last_request_time is None:
            return True
        
        elapsed = (datetime.datetime.now() - self.last_request_time).total_seconds()
        # Refresh session if more than 12 minutes have passed (80% of 15 min timeout)
        if elapsed > (self.session_timeout * 0.8):
            logger.debug(f"Session approaching timeout ({elapsed:.1f}s elapsed), refreshing...")
            try:
                self._refresh_session()
                return True
            except Exception as e:
                logger.warning(f"Failed to refresh session: {str(e)}")
                return False
        return True
    
    def _refresh_session(self):
        """Refresh the session by re-initializing it."""
        logger.debug("Refreshing session...")
        self._reset_session()
        self.initialize()
        self.session_start_time = datetime.datetime.now()
        self.last_request_time = datetime.datetime.now()
    
    def make_request(self, data_updates=None, retry_count=0):
        """Make a request to the Vahan dashboard with the given data updates.
        
        Args:
            data_updates: Dictionary of parameters to update in the request
            retry_count: Internal counter for retry attempts
            
        Returns:
            Tuple of (response, new_viewstate)
            
        Raises:
            ViewExpiredException: If the session expires
            requests.exceptions.RequestException: For other request errors
        """
        # Check session validity before making request
        if not self._check_session_validity():
            raise ViewExpiredException("Session refresh failed")
        
        # Validate viewstate before making request
        if not self.viewstate:
            logger.warning("No viewstate available, re-initializing session...")
            self._refresh_session()
        
        # Add small delay between requests to avoid overwhelming the server
        if self.last_request_time:
            elapsed = (datetime.datetime.now() - self.last_request_time).total_seconds()
            if elapsed < 0.5:  # Minimum 500ms between requests
                time.sleep(0.5 - elapsed)
        
        # Set AJAX-specific headers for POST requests
        post_headers = {
            'Accept': 'application/xml, text/xml, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Faces-Request': 'partial/ajax',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
        
        base_data = {
            'javax.faces.partial.ajax': 'true',
            'masterLayout_formlogin': 'masterLayout_formlogin',
            'j_idt17_focus': '',
            'j_idt17_input': 'M',
            'j_idt30_focus': '',
            'j_idt30_input': 'A',
            'selectedRto_focus': '',
            'selectedRto_input': '-1',
            'selectedType_focus': '',
            'selectedType_filter': '',
            'regnYearWiseCompChart_active': '0',
            'transYearWiseBestChart_active': '0',
            'revYearWiseBestChart_active': '0',
            'perYearWiseBestChart_active': '0',
            'TotalSitesComp2_active': '0',
            'javax.faces.ViewState': self.viewstate,
        }
        
        # If state dropdown ID is available, add it to base data
        if 'state' in self.buttons:
            base_data[f'{self.buttons["state"]}_focus'] = ''
            base_data[f'{self.buttons["state"]}_input'] = '-1'
        
        if data_updates:
            base_data.update(data_updates)
            logger.debug(f"Request data: {data_updates}")
        
        try:
            # Use timeout-handled request method
            response = self._make_request_with_timeout('post', URL, timeout=30, 
                                                      data=base_data, headers=post_headers)

            logger.debug("Response: " + str(response.text))
            
            # Check if view has expired BEFORE extracting viewstate
            if 'javax.faces.application.ViewExpiredException' in response.text:
                logger.warning("ViewExpiredException detected in response")
                if retry_count < 2:  # Allow up to 2 retries
                    logger.info(f"Retrying request after session refresh (attempt {retry_count + 1})...")
                    self._refresh_session()
                    return self.make_request(data_updates, retry_count + 1)
                raise ViewExpiredException("View state expired after retries")
            
            # Extract new viewstate from response
            new_viewstate = self._extract_viewstate(response.text)
            
            # Validate extracted viewstate
            if new_viewstate is None:
                logger.warning("Failed to extract viewstate from response")
                if retry_count < 1:  # One retry for viewstate extraction failure
                    logger.info("Retrying request after session refresh...")
                    self._refresh_session()
                    return self.make_request(data_updates, retry_count + 1)
                # If we still have the old viewstate, use it
                if self.viewstate:
                    logger.warning("Using previous viewstate")
                    new_viewstate = self.viewstate
                else:
                    raise ViewExpiredException("Could not extract or maintain viewstate")
            
            # Update viewstate and request time
            self.viewstate = new_viewstate
            self.last_request_time = datetime.datetime.now()
                
            return response, new_viewstate
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out after 30 seconds: {str(e)}")
            if retry_count < 2:
                logger.info(f"Retrying request after timeout (attempt {retry_count + 1})...")
                time.sleep(2 * (retry_count + 1))  # Exponential backoff for timeouts
                self._refresh_session()
                return self.make_request(data_updates, retry_count + 1)
            raise ViewExpiredException(f"Request timeout after retries: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            if retry_count < 2:
                logger.info(f"Retrying request after error (attempt {retry_count + 1})...")
                time.sleep(1 * (retry_count + 1))  # Exponential backoff
                self._refresh_session()
                return self.make_request(data_updates, retry_count + 1)
            raise ViewExpiredException(f"Network error: {str(e)}")

    def _extract_viewstate(self, response_text):
        """Extract viewstate from response text.
        
        Args:
            response_text: HTML response from the server
            
        Returns:
            Extracted viewstate string or None if not found
        """
        # Method 1: Extract from CDATA section (most common in AJAX responses)
        if '[CDATA[' in response_text and ']]' in response_text:
            try:
                start_idx = response_text.rfind("[CDATA[")
                end_idx = response_text.rfind("]]")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    viewstate = response_text[start_idx + 7:end_idx].strip()
                    if viewstate:
                        logger.debug("Successfully extracted new viewstate from CDATA")
                        return viewstate
            except Exception as e:
                logger.debug(f"Error extracting viewstate from CDATA: {str(e)}")
        
        # Method 2: Extract from hidden input field in HTML/XML
        try:
            parser, _ = self._get_parser(response_text)
            soup = BeautifulSoup(response_text, parser)
            viewstate_input = soup.find('input', {'name': 'javax.faces.ViewState'})
            if viewstate_input and viewstate_input.get('value'):
                viewstate = viewstate_input['value']
                logger.debug("Successfully extracted new viewstate from HTML/XML input")
                return viewstate
        except Exception as e:
            logger.debug(f"Error extracting viewstate from HTML/XML: {str(e)}")
        
        # Method 3: Try regex pattern for viewstate in XML/HTML
        try:
            # Pattern for viewstate in various formats
            patterns = [
                r'<update id="javax\.faces\.ViewState"><!\[CDATA\[([^\]]+)\]\]></update>',
                r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"',
                r'id="[^"]*ViewState[^"]*"[^>]*value="([^"]+)"',
            ]
            for pattern in patterns:
                match = re.search(pattern, response_text)
                if match:
                    viewstate = match.group(1)
                    if viewstate:
                        logger.debug("Successfully extracted new viewstate using regex")
                        return viewstate
        except Exception as e:
            logger.debug(f"Error extracting viewstate using regex: {str(e)}")
        
        logger.warning("Could not extract viewstate from response")
        return None  # Return None to indicate failure

    def make_base_request(self, source, render, state='-1', rto='-1'):
        """Make a base request with standard parameters.
        
        Args:
            source: Source component ID
            render: Render component ID
            state: State code (default: '-1')
            rto: RTO code (default: '-1')
            
        Returns:
            Tuple of (response, new_viewstate)
        """
        state_param = {}
        if 'state' in self.buttons:
            state_param = {f'{self.buttons["state"]}_input': state}
            
        response, new_viewstate = self.make_request({
            'javax.faces.source': source,
            'javax.faces.partial.execute': '@all',
            'javax.faces.partial.render': render,
            f'{source}': source,
            'selectedRto_input': rto,
            **state_param
        })
        
        # make_request already updates self.viewstate, but return it for consistency
        return response, self.viewstate

    @retry_on_view_expired()
    def initialize(self):
        """Initialize the session and get initial viewstate."""
        logger.debug("Initializing session...")
        
        # Get initial page and viewstate
        # For initial GET request, use HTML accept header
        get_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        # Use timeout-handled request method
        response = self._make_request_with_timeout('get', URL, timeout=30, headers=get_headers)
        
        # Parse the response to get soup for button extraction
        parser, _ = self._get_parser(response.content, response.headers.get('Content-Type', ''))
        soup = BeautifulSoup(response.content, parser)
        
        # Try to extract viewstate using multiple methods
        viewstate = self._extract_viewstate(response.text)
        
        if not viewstate:
            # Fallback: try parsing as HTML
            viewstate_elem = soup.find('input', {'name': 'javax.faces.ViewState'})
            
            if viewstate_elem and viewstate_elem.get('value'):
                viewstate = viewstate_elem['value']
            else:
                # Last resort: try regex on raw content
                patterns = [
                    r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"',
                    r'id="[^"]*ViewState[^"]*"[^>]*value="([^"]+)"',
                ]
                for pattern in patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        viewstate = match.group(1)
                        break
                
                if not viewstate:
                    raise Exception("Could not find viewstate in initial page")
            
        self.viewstate = viewstate
        self.last_request_time = datetime.datetime.now()
        self.session_start_time = datetime.datetime.now()

        # Extract button IDs from the page
        self._extract_button_ids(soup)
        
        # Initialize components in sequence
        
        # 1. Main block initialization
        response, self.viewstate = self.make_base_request(
            self.buttons['initialBlock'], 'initialBlock')
        logger.debug("Initial block initialized")

        # 2. Initialize main dashboard panels
        self._initialize_dashboard_panels()
        
        # 3. Initialize charts
        self._initialize_charts()
        
        logger.debug("Session initialization complete")
        return self.viewstate
    
    def _extract_button_ids(self, soup):
        """Extract button IDs from the page HTML.
        
        Args:
            soup: BeautifulSoup object of the page HTML
        """
        logger.debug("Extracting button IDs from page...")
        
        # Define button categories for more organized extraction
        button_categories = {
            'basic': ['initialBlock', 'comparison'],
            'main_panels': ['mainpagepnl_regn', 'mainpagepnl_trans', 'mainpagepnl_revenue', 
                            'mainpagepnl_permit', 'mainpagepnl_taxDef'],
            'regular_panels': ['pnl_regn', 'pnl_trans', 'pnl_revenue', 'pnl_permit'],
            'charts': ['regnYearWiseCompChart', 'transYearWiseBestChart', 'revYearWiseBestChart', 
                       'perYearWiseBestChart', 'TotalSitesComp2'],
            'detail_panels': ['panel_vhClass', 'panel_vhCatg', 'panel_fuel', 'panel_norms', 'panel_maker', 'panel_trans', 'panel_rev_fee', 'panel_rev_tax', 'panel_permitType', 'panel_permitCatg', 'panel_permitPurpose'],
            '1': ['panelHeader'],
            'infoMsg': ['infoMsg']
        }
        
        # Extract state dropdown ID
        state_option = soup.find('option', string=lambda s: s and 'All Vahan4 Running States' in s)
        if state_option and state_option.parent and state_option.parent.get('id'):
            self.buttons['state'] = state_option.parent.get('id').replace("_input", "")
            logger.debug(f"Found state dropdown ID: {self.buttons['state']}")
        
        # Process basic elements
        for button_id in button_categories['basic']:
            element = soup.find(id=button_id)
            if element:
                script_element = element.find('script')
                if script_element and script_element.get('id'):
                    element_id = script_element['id'].replace("_s", "")
                    if element_id and element_id.startswith('j_idt'):
                        self.buttons[button_id] = element_id
                        logger.debug(f"Found {button_id} button ID: {element_id}")
        
        # Special handling for the comparison button
        if 'comparison' not in self.buttons:
            refresh_buttons = soup.find_all('button', {'class': 'ui-button ui-widget ui-state-default ui-corner-all ui-button-icon-only'})
            for button in refresh_buttons:
                onclick_attr = button.get('onclick', '')
                if 'comparison' in onclick_attr and 'dashboardContentsPanel' in onclick_attr:
                    script_element = button.find_next('script')
                    if script_element and script_element.get('id'):
                        element_id = script_element['id'].replace("_s", "")
                        if element_id and element_id.startswith('j_idt'):
                            self.buttons['comparison'] = element_id
                            logger.debug(f"Found comparison button ID: {element_id}")
                            break
        
        # Process panels and charts with different script structure
        for category, button_ids in list(button_categories.items())[1:4]:  # Middle 3 categories
            for button_id in button_ids:
                element = soup.find(id=button_id)
                if element:
                    script_element = None
                    script_tags = element.find_all('script')
                    
                    if len(script_tags) >= 1:
                        script_element = script_tags[-1].find_next('script').find_next('script')

                    if category == 'charts':
                        script_element = element.find_next('script').find_next('script').find_next('script')
                    
                    if script_element and script_element.get('id'):
                        element_id = script_element['id'].replace("_s", "")
                        if element_id and element_id.startswith('j_idt'):
                            self.buttons[button_id] = element_id
                            logger.debug(f"Found {button_id} button ID: {element_id}")
        
        # Process detail panels with a different script structure
        for button_id in button_categories['detail_panels']:
            element = soup.find(id=button_id)
            if element:
                # Find the fourth script element
                script_element = element.find_next('script').find_next('script').find_next('script').find_next('script')
                
                if script_element and script_element.get('id'):
                    element_id = script_element['id'].replace("_s", "")
                    if element_id and element_id.startswith('j_idt'):
                        self.buttons[button_id] = element_id
                        logger.debug(f"Found {button_id} button ID: {element_id}")

        # Process 1 panels with a different script structure
        for button_id in button_categories['1']:
            if self.buttons.get(button_id):
                continue
            else:
                element = soup.find(id=button_id)
                if element:
                    script_element = element.find_next('script')
                self.buttons[button_id] = script_element.get('id').replace("_s", "")
                logger.debug(f"Found {button_id} button ID: {self.buttons[button_id]}")                
        
        # Log all button IDs for debugging
        for button_name, button_id in self.buttons.items():
            logger.debug(f"Button ID: {button_name} = {button_id}")
    
    def _extract_year_ids(self, html_content=None, category='regn'):
        """Extract year selection IDs for category from HTML content.
        
        Args:
            html_content: HTML content to parse
            category: Data category to determine which instance of year IDs to use
        """
        logger.debug(f"Extracting year selection IDs for {category}...")
        
        try:
            # Create soup from html_content (HTML fragments from XML responses)
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all year link groups in the panel
            current_group = soup.find_all('div', {'id': f'pnl_{category}'})
            
            # Find year links in the selected group
            year_links = current_group[0].find_all('a', {'class': 'ui-commandlink ui-widget font-color'})
            
            # Process each year link, skipping "Till Today"
            for link, year in zip(year_links[1:], YEARS):
                element_id = link.get('id')
                self.years[category][year] = element_id
                logger.debug(f"Found year {year} ID: {element_id} for category {category}")
                    
        except Exception as e:
            logger.error(f"Error extracting year IDs for category {category}: {str(e)}")

    def _extract_month_ids(self, html_content, state, rto, year):
        """Extract month selection IDs from the HTML content."""
        logger.debug("Extracting month selection IDs...")
        
        try:
            # Parse the HTML content (HTML fragments from XML responses)
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find month links in the content
            month_links = soup.find_all('div', {'class': 'ui-grid-col-1 link_month'})
            
            # Process each month link
            for i, link in enumerate(month_links[1:]):
                if i < len(MONTHS):
                    month = MONTHS[i]
                    a_tag = link.find('a')
                    if a_tag and a_tag.get('id'):
                        self.months[month] = a_tag.get('id')
                        logger.debug(f"Found month {month} ID: {self.months[month]}")
            
            # Check if all months were found
            found_months = len(self.months)
            if found_months < len(MONTHS):
                missing_months = [month for month in MONTHS if month not in self.months]
                logger.debug(f"Not all months were found. Found {found_months} out of {len(MONTHS)}. Missing: {', '.join(missing_months)}")

                # Create blank files for missing months
                for month in missing_months:
                    for category in ALL_PANELS.keys():
                        for file_suffix in ALL_PANELS[category].values():
                            create_blank_html_file(file_suffix, state, rto, year, month, category)
                            logger.debug(f"Created blank {file_suffix} file at raw/{state}/{rto}/{year}/{month}/{category}")               
                            self.completed_fetches = mark_completion(self.completed_fetches, state, rto, category, year, month)
        
        except Exception as e:
            logger.error(f"Error extracting month IDs: {str(e)}")
            logger.error(traceback.format_exc())

    def _initialize_dashboard_panels(self):
        """Initialize all dashboard panels."""
        panel_types = ['regn', 'trans', 'revenue', 'permit', 'taxDef']
        
        # Initialize main panels
        for panel_type in panel_types:
            panel_id = self.buttons.get(f'mainpagepnl_{panel_type}')
            if panel_id:
                self.make_base_request(panel_id, f'mainpagepnl_{panel_type}')
            else:
                logger.warning(f"No ID found for panel mainpagepnl_{panel_type}")
        
        # Initialize additional panels (excluding taxDef which doesn't have a separate panel)
        for panel_type in panel_types[:-1]:
            panel_id = self.buttons.get(f'pnl_{panel_type}')
            if panel_id:
                response, new_viewstate = self.make_base_request(panel_id, f'pnl_{panel_type}')
                self.viewstate = new_viewstate
                
                # Extract year IDs from the panel response
                if response:
                    root = ET.fromstring(response.text)
                    if len(root) > 0 and len(root[0]) > 0:
                        html_content = root[0][0].text
                        if html_content:
                            self._extract_year_ids(html_content=html_content, category=panel_type)
            else:
                logger.warning(f"No ID found for panel pnl_{panel_type}")
    
    def _initialize_charts(self):
        """Initialize all charts."""
        chart_types = [
            'regnYearWiseCompChart', 
            'transYearWiseBestChart', 
            'revYearWiseBestChart', 
            'perYearWiseBestChart', 
            'TotalSitesComp2'
        ]
        
        for chart in chart_types:
            chart_id = self.buttons.get(chart)
            if chart_id:
                self.make_base_request(chart_id, chart)
            else:
                logger.warning(f"No ID found for chart {chart}")

    @retry_on_view_expired()
    def fetch_state(self, state):
        """Fetch data for a specific state."""
        logger.info(f"{state}")
        response, self.viewstate = self.make_request({
            'javax.faces.source': f'{self.buttons["state"]}',
            'javax.faces.partial.execute': f'{self.buttons["state"]}',
            'javax.faces.partial.render': 'selectedRto',
            'javax.faces.behavior.event': 'change',
            'javax.faces.partial.event': 'change',
            'masterLayout_formlogin': 'masterLayout_formlogin',
            f'{self.buttons["state"]}_input': state,
        })
        root = ET.fromstring(response.text)
        html = root[0][0].text if root is not None and len(root) > 0 and len(root[0]) > 0 else ""
        rtos = parse_state_rtos(html)
        logger.debug(f"Found {len(rtos)} RTOs for state {state}")
        
        # Filter RTOs if rtos_filter is specified
        if self.rtos_filter and state in self.rtos_filter:
            rtos = [rto for rto in rtos if rto in self.rtos_filter[state]]
            logger.debug(f"Filtered to {len(rtos)} RTOs for state {state}")
        elif self.rtos_filter and state not in self.rtos_filter:
            # If rtos_filter is specified but this state is not in it, skip all RTOs
            logger.debug(f"Skipping state {state} (not in RTOs filter)")
            return True
        
        for rto in rtos:
            if is_fetch_completed(self.completed_fetches, state, rto):
                logger.info(f"{state}-{rto} already completed.")
                continue

            logger.info(f"{state}-{rto}")
            success = self.fetch_rto_data(state, rto)
            if not success:
                return False

        return True

    @retry_on_view_expired()
    def fetch_rto_data(self, state, rto):
        """Set the RTO and fetch its data."""
        logger.debug(f"Setting RTO: {state}-{rto}")
        
        # Set the RTO for subsequent requests
        response, self.viewstate = self.make_request({
            'javax.faces.source': 'selectedRto',
            'javax.faces.partial.execute': 'selectedRto',
            'javax.faces.behavior.event': 'change',
            'javax.faces.partial.event': 'change',
            'masterLayout_formlogin': 'masterLayout_formlogin',
            f'{self.buttons["state"]}_input': state,
            'selectedRto_input': rto,
        })

        # Initialize comparison view to access year data
        response, self.viewstate = self.make_request({
            'javax.faces.source': self.buttons['comparison'],
            'javax.faces.partial.execute': '@all',
            'javax.faces.partial.render': 'comparison dashboardContentsPanel mainpagepnl',
            'masterLayout_formlogin': 'masterLayout_formlogin',
            self.buttons['comparison']: self.buttons['comparison'],
            f'{self.buttons["state"]}_input': state,
            'selectedRto_input': rto,
        })

        # Process each data category
        for category in ['regn', 'trans', 'revenue', 'permit']:
            # If category is already completed for this RTO, skip
            if is_fetch_completed(self.completed_fetches, state, rto, category=category,
                                 years_filter=self.years_filter,
                                 months_filter=self.months_filter,
                                 states_filter=self.states_filter,
                                 rtos_filter=self.rtos_filter):
                logger.info(f"{state}-{rto} {category} already completed.")
                continue

            # Process each year - filter by years_filter if specified
            years_to_process = self.years[category].keys()
            if self.years_filter:
                years_to_process = [y for y in years_to_process if y in self.years_filter]
                logger.debug(f"Filtered to {len(years_to_process)} years for {state}-{rto} {category}")
            
            for year in years_to_process:
                # If year is already completed for this category, skip
                if is_fetch_completed(self.completed_fetches, state, rto, year=year, category=category,
                                     years_filter=self.years_filter,
                                     months_filter=self.months_filter,
                                     states_filter=self.states_filter,
                                     rtos_filter=self.rtos_filter):
                    logger.info(f"{state}-{rto} {category} {year} already completed.")
                    continue

                success = self.fetch_year_data(state, rto, year, category)
                if not success:
                    return False

        return True

    @retry_on_view_expired()
    def fetch_year_data(self, state, rto, year, category):
        """Fetch data for a specific year."""
        # Filter by years_filter if specified
        if self.years_filter and year not in self.years_filter:
            logger.debug(f"Skipping year {year} for {state}-{rto} (not in filter)")
            return True  # Return True to continue processing other years
            
        # If not fetch_all and years_filter is not explicitly set, only process current year
        # (years_filter being set means user explicitly wants those years, so respect that)
        if not self.fetch_all and self.years_filter is None and int(year) < self.current_date.year:
            logger.debug(f"Skipping past year {year} for {state}-{rto} (use --fetch-all or --years to fetch other years)")
            return True  # Return True to continue processing other years
            
        year_key = self.years[category].get(year)
        if not year_key:
            logger.debug(f"No ID found for year {year} in category {category}")
            return False
            
        logger.debug(f"Fetching year data: {state}-{rto} for {year} and {category}")

        box_year_label = category
        if category == 'revenue':
            box_year_label = 'rev'
        elif category == 'permit':
            box_year_label = 'per'
        
        # Select the year
        response, self.viewstate = self.make_request({
            'javax.faces.source': year_key,
            'javax.faces.partial.execute': '@all',
            'javax.faces.partial.render': 'infoMsg',
            'masterLayout_formlogin': 'masterLayout_formlogin',
            year_key: year_key,
            'BoxYearLabel': box_year_label,
            f'{self.buttons["state"]}_input': state,
            'selectedRto_input': rto,
        })

        # Extract month IDs from the response
        root = ET.fromstring(response.text)
        html_content = root[0][0].text if root is not None and len(root) > 0 and len(root[0]) > 0 else ""
        if html_content:
            # Re-extract button IDs after selecting a year to get updated IDs
            soup = BeautifulSoup(html_content, 'html.parser')
            self._extract_button_ids(soup)
        
        # Initialize panels for this year
        self._initialize_year_panels(state, rto, year, category)
        
        # Process each month - include all expected months even if they don't have IDs
        processed_months = set()
        
        # First process months that have IDs
        for month in self.months.keys():
            processed_months.add(month)
            
            # Filter by months_filter if specified
            if self.months_filter and month not in self.months_filter:
                logger.debug(f"Skipping month {year}-{month} for {state}-{rto} (not in filter)")
                continue
            
            # Skip future months in current year
            month_num = MONTHS.index(month) + 1
            if int(year) == self.current_date.year and month_num > self.current_date.month:
                logger.debug(f"Skipping future month {year}-{month} for {state}-{rto}")
                # Create blank files for skipped future months  
                for file_suffix in ALL_PANELS[category].values():
                    create_blank_html_file(file_suffix, state, rto, year, month, category)
                    logger.debug(f"Created blank {file_suffix} file at raw/{state}/{rto}/{year}/{month}/{category}")
                    self.completed_fetches = mark_completion(self.completed_fetches, state, rto, category, year, month)
                continue
                
            # If not fetch_all and months_filter is not explicitly set, only process current month of current year
            # (months_filter being set means user explicitly wants those months, so respect that)
            if not self.fetch_all and self.months_filter is None:
                if int(year) == self.current_date.year and month_num != self.current_date.month:
                    logger.debug(f"Skipping month {year}-{month} for {state}-{rto} (use --fetch-all or --months to fetch other months)")
                    continue
                
            # Check if this month and category is already completed
            if is_fetch_completed(self.completed_fetches, state, rto, year=year, month=month, category=category,
                                 years_filter=self.years_filter,
                                 months_filter=self.months_filter,
                                 states_filter=self.states_filter,
                                 rtos_filter=self.rtos_filter):
                logger.info(f"{state}-{rto} {year}-{month} {category} already completed.")
                continue
                
            logger.info(f"{state}-{rto} {year}-{month} {category}")
            success = self.fetch_month_data(state, rto, year, category, month)
            if not success:
                return False
        
        # Save completion state after each year
        save_completed_fetches(self.completed_fetches)
        return True
    
    def _initialize_year_panels(self, state, rto, year, category='regn'):
        """Initialize panels for a specific year.
        
        Args:
            state: State code
            rto: RTO code
            year: Year to fetch
            category: Data category (regn, trans, revenue, permit)
        """
        # Define panel types based on category
        if category == 'regn':
            panel_types = [
                'panelHeader', 'panel_vhClass', 'panel_vhCatg', 
                'panel_fuel', 'panel_norms', 'panel_maker'
            ]
        elif category == 'trans':
            panel_types = ['panelHeader', 'panel_trans']
        elif category == 'revenue':
            panel_types = ['panelHeader', 'panel_rev_fee', 'panel_rev_tax']
        elif category == 'permit':
            panel_types = ['panelHeader', 'panel_permitType', 'panel_permitCatg', 'panel_permitPurpose']
        else:
            logger.warning(f"Invalid category: {category}")
            raise ViewExpiredException("Invalid category")
        
        for panel in panel_types:
            panel_id = self.buttons.get(panel)
            if panel_id:
                response, new_viewstate = self.make_base_request(panel_id, panel, state, rto)
                self.viewstate = new_viewstate
                
                # Extract month IDs from the panelHeader response
                if panel == 'panelHeader' and response:
                    root = ET.fromstring(response.text)
                    if len(root) > 0 and len(root[0]) > 0:
                        html_content = root[0][0].text
                        if html_content:
                            self._extract_month_ids(html_content, state, rto, year)
            else:
                logger.warning(f"No ID found for panel {panel}")
                raise ViewExpiredException("Missing required panel ID")

    @retry_on_view_expired()
    def fetch_month_data(self, state, rto, year, category, month):
        """Fetch data for a specific month."""
        logger.debug(f"Fetching month data: {state}-{rto} for {year}/{month}")
        
        month_key = self.months.get(month)
        
        # If the month key is missing, create blank files
        if not month_key:
            logger.debug(f"No month key found for {month}, creating blank files")
            for file_suffix in ALL_PANELS[category].values():
                create_blank_html_file(file_suffix, state, rto, year, month, category)
                logger.debug(f"Created blank {file_suffix} file at raw/{state}/{rto}/{year}/{month}/{category}")
                self.completed_fetches = mark_completion(self.completed_fetches, state, rto, category, year, month)
            return True
        
        # Select the month
        response, self.viewstate = self.make_request({
            'javax.faces.source': month_key,
            'javax.faces.partial.execute': '@all',
            'javax.faces.partial.render': 'infoMsg',
            month_key: month_key,
            'year': year,
            'month': month,
            'masterLayout_formlogin': 'masterLayout_formlogin',
            f'{self.buttons["state"]}_input': state,
            'selectedRto_input': rto,
            'datatable_VhClass_scrollState': '0,0',
            'datatable_Catg_scrollState': '0,0',
            'datatable_fuel_scrollState': '0,0',
            'datatable_norms_scrollState': '0,0',
            'datatable_maker_scrollState': '0,0',
        })

        # Fetch the appropriate data based on category
        success = self._fetch_panel_data(state, rto, year, month, category)
            
        return success
    
    @retry_on_view_expired()
    def _fetch_panel_data(self, state, rto, year, month, category):
        """Generic method to fetch panel data.
        
        Args:
            state: State code
            rto: RTO code
            year: Year to fetch
            month: Month to fetch
            category: Category to fetch
            
        Returns:
            Boolean indicating success
        """
        logger.debug(f"Fetching panel data for {state}-{rto}-{year}-{month}-{category}")
        success_count = 0
        panels = ALL_PANELS[category]
        
        for panel_key, file_suffix in panels.items():
            panel_id = self.buttons.get(panel_key)
            if not panel_id:
                logger.warning(f"No ID found for panel {panel_key}")
                continue
                
            try:
                # Request panel data
                response, _ = self.make_base_request(panel_id, panel_key, state, rto)
                
                # Parse XML response
                root = ET.fromstring(response.text)
                if len(root) > 0 and len(root[0]) > 0:
                    xml_content = root[0][0].text
                    
                    # Save the data to file with state subdirectory
                    save_to_file(xml_content, state, rto, year, month, category, file_suffix)
                    logger.debug(f"Saved {file_suffix} data to raw/{state}/{rto}/{year}/{month}/{category}")
                    
                    success_count += 1
                else:
                    logger.warning(f"Empty response for {file_suffix}")
                    
            except ViewExpiredException:
                # Let the decorator handle this
                raise
            except Exception as e:
                logger.error(f"Error fetching {file_suffix} for {state}-{rto}-{year}-{month}: {str(e)}")
                # Continue to next panel instead of failing completely
        
        # If we successfully fetched all panels, mark this category as complete
        if success_count == len(panels):
            self.completed_fetches = mark_completion(self.completed_fetches, state, rto, category, year, month)
            logger.debug(f"Marked {state}-{rto}-{year}-{month}-{category} as complete")
        
        # Return True if we successfully fetched at least some of the panel data
        return success_count > 0

    def run(self):
        """Run the fetcher for all states."""
        logger.info("Starting Vahan data fetching process")
        last_save_time = datetime.datetime.now()
        
        # Filter states if states_filter is specified
        states_to_process = STATES
        if self.states_filter:
            states_to_process = [s for s in STATES if s in self.states_filter]
            logger.info(f"Filtered to {len(states_to_process)} states: {', '.join(states_to_process)}")
        
        for state in states_to_process:
            attempt = 0
            while True:
                try:
                    logger.debug(f"Starting fetch for state: {state} (attempt {attempt+1})")
                    
                    # Create a fresh session for each attempt
                    if attempt > 0:
                        self._reset_session()
                    
                    # Initialize session
                    self.initialize()
                    
                    # Fetch state data
                    success = self.fetch_state(state)
                    if success:
                        logger.info(f"Successfully completed state: {state}")
                        break
                    else:
                        logger.debug(f"Failed to complete state {state}, retrying...")
                        self._reset_session()
                        attempt += 1
                        continue
                
                except ViewExpiredException:
                    logger.debug(f"View expired during state {state}. Attempt {attempt+1}")
                    self._reset_session()
                    attempt += 1
                except Exception as e:
                    logger.debug(f"{state} failed! Error: {str(e)}")
                    self._reset_session()
                    attempt += 1
            
            # Always ensure we have a fresh session for the next state
            self._reset_session()
                        
        logger.info("Vahan data fetching process completed")
        # Final save of completion state
        save_completed_fetches(self.completed_fetches)

    def _reset_session(self):
        """Reset the session completely and reinitialize."""
        logger.debug("Resetting session...")
        
        # Close and recreate session
        self.session.close()
        self.session = requests.Session()
        # Restore global headers
        self._set_global_headers()
        
        # Reset state
        self.viewstate = None
        self.buttons = {}
        self.years = {
            'regn': {},
            'trans': {},
            'revenue': {},
            'permit': {}
        }
        self.months = {}
        self.session_start_time = datetime.datetime.now()
        self.last_request_time = None

def load_completed_fetches(file_path='.completed.json'):
    """Load the completed fetches from a JSON file.
    
    Returns:
        Dictionary containing completed fetches with format:
        {
            "state:rto:year:month:category": True,
            "state:rto:year:month": True,  # All categories for month completed
            "state:rto:year": True  # All months for year completed
        }
    """
    if not os.path.exists(file_path):
        return {}
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading completed fetches from {file_path}: {str(e)}")
        return {}

def save_completed_fetches(completed_fetches, file_path='.completed.json'):
    """Save the completed fetches to a JSON file.
    
    Args:
        completed_fetches: Dictionary containing completed fetches
        file_path: Path to save the JSON file
    """
    try:
        # Create temporary file then rename to avoid partial writes
        temp_file = f"{file_path}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(completed_fetches, f, indent=2)
        os.replace(temp_file, file_path)
    except Exception as e:
        logger.error(f"Error saving completed fetches to {file_path}: {str(e)}")

def is_fetch_completed(completed_fetches, state, rto, year=None, month=None, category=None,
                       years_filter=None, months_filter=None, states_filter=None, rtos_filter=None):
    """Check if a fetch has been completed based on what needs to be fetched.
    
    Uses a flattened key structure for faster lookups.
    Considers filters to determine if something is truly complete.
    
    Args:
        completed_fetches: Dictionary of completed fetches
        state: State code
        rto: RTO code
        year: Year (optional)
        month: Month (optional)
        category: Category (optional)
        years_filter: Set of years that need to be fetched (None = all)
        months_filter: Set of months that need to be fetched (None = all)
        states_filter: Set of states that need to be fetched (None = all)
        rtos_filter: Dict mapping state to set of RTOs that need to be fetched (None = all)
    """
    # If state filter is specified and this state is not in it, consider it complete (we don't need it)
    if states_filter and state not in states_filter:
        return True
    
    # If RTO filter is specified and this RTO is not in it, consider it complete (we don't need it)
    if rtos_filter and state in rtos_filter and rto not in rtos_filter[state]:
        return True
    
    # Helper function to check if a specific month/category is complete
    def _is_month_category_complete(y, m, cat):
        """Check if a specific month/category combination is complete."""
        key = f"{state}:{rto}:{cat}:{y}:{m.upper()}"
        if key in completed_fetches:
            return True
        # Check if year-level completion exists
        year_key = f"{state}:{rto}:{cat}:{y}"
        if year_key in completed_fetches:
            return True
        # Check if category-level completion exists
        category_key = f"{state}:{rto}:{cat}"
        if category_key in completed_fetches:
            return True
        # Check if RTO-level completion exists
        rto_key = f"{state}:{rto}"
        if rto_key in completed_fetches:
            return True
        return False
    
    # Determine what we need to check based on filters
    # Convert to sets if they're lists (for consistency)
    if years_filter is not None:
        years_to_check = set(years_filter) if not isinstance(years_filter, set) else years_filter
    else:
        years_to_check = set(YEARS)
    
    if months_filter is not None:
        months_to_check = set([m.upper() for m in months_filter]) if not isinstance(months_filter, set) else months_filter
    else:
        months_to_check = set(MONTHS)
    
    all_categories = ['regn', 'trans', 'revenue', 'permit']
    
    # Build key based on provided parameters
    if rto and category and year and month:
        # Check if this specific month/category is complete
        return _is_month_category_complete(year, month, category)
        
    if rto and category and year:
        # Check if all required months for this year in this category are complete
        for m in months_to_check:
            if not _is_month_category_complete(year, m, category):
                return False
        return True
        
    if rto and category:
        # Check if entire category is marked complete for all required years/months
        for y in years_to_check:
            for m in months_to_check:
                if not _is_month_category_complete(y, m, category):
                    return False
        return True
            
    if rto and month and year:
        # Check if all categories for this month are complete
        for cat in all_categories:
            if not _is_month_category_complete(year, month, cat):
                return False
        return True
        
    if rto and year:
        # Check if entire year is marked complete for all required months
        for cat in all_categories:
            for m in months_to_check:
                if not _is_month_category_complete(year, m, cat):
                    return False
        return True
    
    if rto:
        # Check if entire rto is marked complete for all required years/months
        for cat in all_categories:
            for y in years_to_check:
                for m in months_to_check:
                    if not _is_month_category_complete(y, m, cat):
                        return False
        return True
    
    return False

def scan_completed_fetches(raw_dir="raw/"):
    """Scan the raw directory and build completed fetches data structure efficiently.
    
    Returns:
        Dictionary containing completed fetches based on existing files
    """
    if not os.path.exists(raw_dir):
        return {}

    scanned_fetches = {}
    state_rtos = {}  # Cache of RTOs per state
    
    # Expected file counts for each category
    expected_counts = {
        'regn': len(REGISTRATION_PANELS),
        'trans': len(TRANSACTION_PANELS),
        'revenue': len(REVENUE_PANELS),
        'permit': len(PERMIT_PANELS)
    }
    
    # Category mapping for directory to data category
    category_map = {
        'registration': 'regn',
        'transaction': 'trans',
        'revenue': 'revenue',
        'permit': 'permit'
    }
    
    def check_completion(state, rto, category, year, month):
        """Check and mark completion levels."""
        # Mark month level
        month_key = f"{state}:{rto}:{category}:{year}:{month.upper()}"
        scanned_fetches[month_key] = True
        
        # Check and mark year level
        if all(f"{state}:{rto}:{category}:{year}:{m}" in scanned_fetches for m in MONTHS):
            scanned_fetches[f"{state}:{rto}:{category}:{year}"] = True
            
        # Check and mark category level
        current_year = datetime.datetime.now().year
        if all(f"{state}:{rto}:{category}:{y}" in scanned_fetches 
              for y in YEARS if int(y) <= current_year):
            scanned_fetches[f"{state}:{rto}:{category}"] = True
            
        # Check and mark RTO level
        if all(f"{state}:{rto}:{cat}" in scanned_fetches 
              for cat in expected_counts.keys()):
            scanned_fetches[f"{state}:{rto}"] = True

    # Use os.walk for efficient directory traversal
    for root, dirs, files in os.walk(raw_dir):
        path_parts = Path(root).relative_to(raw_dir).parts
        
        # Skip if not deep enough
        if len(path_parts) < 5:
            # Cache RTOs for each state at state level
            if len(path_parts) == 1:
                state = path_parts[0]
                state_rtos[state] = set(dirs)
            continue
            
        state, rto, year, month, category = path_parts
        
        # Skip if not a valid category
        if category not in category_map:
            continue
            
        # Count valid HTML files
        html_count = sum(1 for f in files if f.endswith('.html'))
        
        # Check if category is complete
        data_category = category_map[category]
        if html_count >= expected_counts[data_category]:
            check_completion(state, rto, data_category, year, month)

        # Mark all future months for this year as complete
        current_month = datetime.datetime.now().strftime('%B').upper()[0:3]
        current_year = datetime.datetime.now().year
        for month in MONTHS[MONTHS.index(current_month):]:
            month_key = f"{state}:{rto}:{data_category}:{current_year}:{month.upper()}"
            scanned_fetches[month_key] = True
    
    # Remove redundant lower-level keys
    keys_to_remove = set()
    for key in scanned_fetches:
        # Check if any parent key exists
        parts = key.split(':')
        for i in range(len(parts) - 1):
            parent_key = ':'.join(parts[:i+1])
            if parent_key in scanned_fetches:
                keys_to_remove.add(key)
                break
    
    # Remove all redundant keys at once
    for key in keys_to_remove:
        del scanned_fetches[key]
    
    return scanned_fetches

def update_completed_fetches(completed_fetches, scanned_fetches):
    """Update the completed fetches based on the scanned fetches.
    
    Simply merges the two dictionaries, with scanned_fetches taking precedence.
    """
    # Create a new dictionary with all entries from both sources
    # Convert to dictionary if not already
    if not isinstance(completed_fetches, dict):
        completed_fetches = dict(completed_fetches)
    if not isinstance(scanned_fetches, dict):
        scanned_fetches = dict(scanned_fetches)
    completed_fetches.update(scanned_fetches)
    return completed_fetches

def mark_completion(completed_fetches, state, rto, category, year=None, month=None):
    """Mark a fetch as completed and check if higher levels are completed.
    
    Args:
        completed_fetches: Dictionary containing completed fetches
        state: State code
        rto: RTO code
        year: Year (optional)
        month: Month (optional)
        category: Category (optional)
    """
    def remove_lower_level_keys(base_key):
        """Remove all keys that are more specific than the given base key."""
        keys_to_remove = []
        for key in completed_fetches:
            if key.startswith(base_key + ":"):  # Only remove keys that are more specific
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del completed_fetches[key]

    # Mark the specific level as complete
    if category and month and year:
        key = f"{state}:{rto}:{category}:{year}:{month.upper()}"
        completed_fetches[key] = True
        
        # Check if all months for this year and category are complete
        if all(f"{state}:{rto}:{category}:{year}:{m}" in completed_fetches for m in MONTHS):
            year_key = f"{state}:{rto}:{category}:{year}"
            completed_fetches[year_key] = True
            remove_lower_level_keys(year_key)  # Remove month-level keys
            
            # Check if all years for this category are complete
            current_year = datetime.datetime.now().year
            if all(f"{state}:{rto}:{category}:{y}" in completed_fetches 
                  for y in YEARS if int(y) <= current_year):
                category_key = f"{state}:{rto}:{category}"
                completed_fetches[category_key] = True
                remove_lower_level_keys(category_key)  # Remove year-level keys
                
                # Check if all categories for this RTO are complete
                all_categories = ['regn', 'trans', 'revenue', 'permit']
                if all(f"{state}:{rto}:{cat}" in completed_fetches for cat in all_categories):
                    rto_key = f"{state}:{rto}"
                    completed_fetches[rto_key] = True
                    remove_lower_level_keys(rto_key)  # Remove category-level keys
    
    # Save after each completion
    save_completed_fetches(completed_fetches)

    return completed_fetches

# Main execution
if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Fetch vehicle registration data from Vahan dashboard.')
    parser.add_argument('--fetch-all', action='store_true',
                        help='Fetch all months from 2021 onwards. By default, only fetches current month of current year.')
    parser.add_argument('--no-debug', action='store_true',
                        help='Disable debug logs. By default, debug logs are enabled.')
    parser.add_argument('--years', nargs='+', type=str,
                        help='Specify which years to fetch (e.g., --years 2024 2025). By default, only current year.')
    parser.add_argument('--months', nargs='+', type=str,
                        help='Specify which months to fetch (e.g., --months JAN FEB MAR). By default, only current month.')
    parser.add_argument('--states', nargs='+', type=str,
                        help='Specify which states to fetch (e.g., --states KA MH). By default, all states.')
    parser.add_argument('--rtos', type=str,
                        help='Specify RTOs to fetch as JSON mapping state to RTOs (e.g., \'{"KA": ["KA01", "KA02"], "MH": ["MH01"]}\'). By default, all RTOs.')
    args = parser.parse_args()
    
    # Initialize logger with debug flag
    logger = setup_logger(debug=not args.no_debug)
    
    # Determine default years and months (current month of current year)
    current_date = datetime.datetime.now()
    current_year = str(current_date.year)
    current_month = MONTHS[current_date.month - 1] if current_date.month <= 12 else MONTHS[11]
    
    # Set years filter
    if args.years:
        years_filter = args.years
    elif args.fetch_all:
        years_filter = None  # All years
    else:
        years_filter = [current_year]  # Default: current year only
    
    # Set months filter
    if args.months:
        months_filter = [m.upper() for m in args.months]
    elif args.fetch_all:
        months_filter = None  # All months
    else:
        months_filter = [current_month]  # Default: current month only
    
    # Set states filter
    states_filter = args.states if args.states else None
    
    # Parse RTOs filter
    rtos_filter = None
    if args.rtos:
        try:
            rtos_filter = json.loads(args.rtos)
            # Convert RTO lists to sets for faster lookup
            rtos_filter = {state: set(rtos) for state, rtos in rtos_filter.items()}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON format for --rtos: {args.rtos}")
            exit(1)
    
    # Log filter settings
    if years_filter:
        logger.info(f"Years filter: {', '.join(years_filter)}")
    else:
        logger.info("Years filter: all years")
    
    if months_filter:
        logger.info(f"Months filter: {', '.join(months_filter)}")
    else:
        logger.info("Months filter: all months")
    
    if states_filter:
        logger.info(f"States filter: {', '.join(states_filter)}")
    else:
        logger.info("States filter: all states")
    
    if rtos_filter:
        logger.info(f"RTOs filter: {len(rtos_filter)} states with specific RTOs")
    else:
        logger.info("RTOs filter: all RTOs")
    
    # Load existing completed fetches
    completed_fetches = load_completed_fetches()
    
    # Scan and update the completion tracking
    logger.info("Scanning raw directory to update completed fetches tracking...")
    scanned_fetches = scan_completed_fetches()
    completed_fetches = update_completed_fetches(completed_fetches, scanned_fetches)
    save_completed_fetches(completed_fetches)
    logger.info("Completed fetches tracking updated based on existing files")

    # Initialize and run the fetcher
    fetcher = VahanFetcher(
        completed_fetches=completed_fetches, 
        fetch_all=args.fetch_all,
        years_filter=years_filter,
        months_filter=months_filter,
        states_filter=states_filter,
        rtos_filter=rtos_filter
    )
    fetcher.run()
