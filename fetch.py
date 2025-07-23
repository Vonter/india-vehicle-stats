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

# Global variables
BUTTONS = {}
YEARS = ['2025', '2024', '2023', '2022', '2021']
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
def setup_logger():
    """Set up and configure the logger."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create handlers
    stdout_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('debug.log')

    # Set levels for handlers
    stdout_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)

    # Create formatters
    stdout_formatter = logging.Formatter('%(levelname)s: %(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    stdout_handler.setFormatter(stdout_formatter)
    file_handler.setFormatter(file_formatter)

    # Add handlers to logger
    logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()

# Custom exception for view expiration
class ViewExpiredException(Exception):
    """Exception raised when the view state expires."""
    pass

def find_and_delete_blank_files(directory="raw/"):
    """Find and delete blank HTML files created due to missing month IDs."""
    search_string = "<p>No data available - blank file created due to missing month ID.</p>"
    deleted_count = 0
    
    # Ensure directory exists
    if not os.path.exists(directory):
        return deleted_count
    
    # Walk through all subdirectories
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    if search_string in content:
                        os.remove(file_path)
                        logger.debug(f"Deleted: {file_path}")
                        deleted_count += 1
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
    
    return deleted_count

def parse_state_rtos(state_html):
    """Parse RTO options from state HTML response and save list of RTOs to raw/rtos.txt."""
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

def retry_on_view_expired():
    """Decorator to retry functions when ViewExpiredException occurs."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(self, *args, **kwargs)
                except ViewExpiredException:
                    attempt += 1
                    logger.warning(
                        f"{func.__name__} failed with ViewExpiredException. "
                        f"Retrying (attempt {attempt})..."
                    )
                    self._reset_session()
            return False
        return wrapper
    return decorator

class VahanFetcher:
    """Class to fetch vehicle registration data from Vahan dashboard."""
    
    def __init__(self, completed_fetches=None, fetch_all=False):
        """Initialize the VahanFetcher with default settings."""
        self.session = requests.Session()
        self.viewstate = None
        self.current_date = datetime.datetime.now()
        
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
    
    def make_request(self, data_updates=None):
        """Make a request to the Vahan dashboard with the given data updates.
        
        Args:
            data_updates: Dictionary of parameters to update in the request
            
        Returns:
            Tuple of (response, new_viewstate)
            
        Raises:
            ViewExpiredException: If the session expires
            requests.exceptions.RequestException: For other request errors
        """
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
            response = self.session.post(URL, data=base_data, timeout=30)
            response.raise_for_status()

            logger.debug("Response: " + str(response.text))
            
            # Extract new viewstate from response
            new_viewstate = self._extract_viewstate(response.text)
            
            # Check if view has expired
            if 'javax.faces.application.ViewExpiredException' in response.text:
                raise ViewExpiredException("View state expired")
                
            return response, new_viewstate
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise ViewExpiredException(f"Network error: {str(e)}")

    def _extract_viewstate(self, response_text):
        """Extract viewstate from response text.
        
        Args:
            response_text: HTML response from the server
            
        Returns:
            Extracted viewstate string or the current viewstate if not found
        """
        if '[CDATA[' in response_text and ']]' in response_text:
            viewstate = response_text[
                response_text.rfind("[CDATA["):response_text.rfind("]]")
            ].lstrip("[CDATA[")
            logger.debug("Successfully extracted new viewstate")
            return viewstate
        else:
            logger.warning("Could not extract viewstate from response")
            return self.viewstate  # Return current viewstate if extraction fails

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
        
        return response, new_viewstate

    @retry_on_view_expired()
    def initialize(self):
        """Initialize the session and get initial viewstate."""
        logger.debug("Initializing session...")
        
        # Get initial page and viewstate
        response = self.session.get(URL, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        viewstate_elem = soup.find('input', {'name': 'javax.faces.ViewState'})
        
        if not viewstate_elem or not viewstate_elem.get('value'):
            raise Exception("Could not find viewstate in initial page")
            
        self.viewstate = viewstate_elem['value']

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
            # Create soup from html_content
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
            # Parse the HTML content
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
            if is_fetch_completed(self.completed_fetches, state, rto, category=category):
                logger.info(f"{state}-{rto} {category} already completed.")
                continue

            # Process each year
            for year in self.years[category].keys():
                # If year is already completed for this category, skip
                if is_fetch_completed(self.completed_fetches, state, rto, year=year, category=category):
                    logger.info(f"{state}-{rto} {category} {year} already completed.")
                    continue

                success = self.fetch_year_data(state, rto, year, category)
                if not success:
                    return False

        return True

    @retry_on_view_expired()
    def fetch_year_data(self, state, rto, year, category):
        """Fetch data for a specific year."""            
        # If not fetch_all, only process current year
        if not self.fetch_all and int(year) < self.current_date.year:
            logger.debug(f"Skipping past year {year} for {state}-{rto} (use --fetch-all to fetch all years)")
            
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
                
            # If not fetch_all, only process previous month of current year
            if not self.fetch_all:
                if int(year) == self.current_date.year and month_num != (self.current_date.month - 1):
                    logger.debug(f"Skipping month {year}-{month} for {state}-{rto} (use --fetch-all to fetch all months)")
                    continue
                
            # Check if this month and category is already completed
            if is_fetch_completed(self.completed_fetches, state, rto, year=year, month=month, category=category):
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
        
        for state in STATES:
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

def is_fetch_completed(completed_fetches, state, rto, year=None, month=None, category=None):
    """Check if a fetch has been completed.
    
    Uses a flattened key structure for faster lookups.
    """
    # Build key based on provided parameters
    if rto and category and year and month:
        key = f"{state}:{rto}:{category}:{year}:{month.upper()}"
        if key in completed_fetches:
            return True
        
    if rto and category and year:
        # Check if all months for this year in this category are complete
        year_key = f"{state}:{rto}:{category}:{year}"
        if year_key in completed_fetches:
            return True
        
    if rto and category:
        # Check if entire category is marked complete
        category_key = f"{state}:{rto}:{category}"
        if category_key in completed_fetches:
            return True
            
    if rto and month and year:
        # Check if all categories for this month are complete
        all_categories = ['regn', 'trans', 'revenue', 'permit']
        return all(f"{state}:{rto}:{cat}:{year}:{month.upper()}" in completed_fetches for cat in all_categories)
        
    if rto and year:
        # Check if entire year is marked complete
        all_categories = ['regn', 'trans', 'revenue', 'permit']
        return all(f"{state}:{rto}:{cat}:{year}" in completed_fetches for cat in all_categories)
    
    if rto:
        # Check if entire rto is marked complete
        rto_key = f"{state}:{rto}"
        if rto_key in completed_fetches:
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
    parser.add_argument('--refetch-missing', action='store_true', 
                        help='Refetch files with missing data. By default, only fetches files that don\'t exist.')
    parser.add_argument('--fetch-all', action='store_true',
                        help='Fetch all months from 2021 onwards. By default, only fetches previous month of current year.')
    parser.add_argument('--reset-completed', action='store_true',
                        help='Reset .completed.json')
    args = parser.parse_args()
    
    # Only delete blank files if --refetch-missing is set
    if args.refetch_missing:
        deleted_count = find_and_delete_blank_files()
        logger.info(f"Deleted blank files")

    # Delete .completed.json if --reset-completed is set
    if args.reset_completed:
        os.remove('.completed.json')
        logger.info("Deleted .completed.json")
    
    # Load existing completed fetches
    completed_fetches = load_completed_fetches()
    
    # Scan and update the completion tracking
    logger.info("Scanning raw directory to update completed fetches tracking...")
    scanned_fetches = scan_completed_fetches()
    completed_fetches = update_completed_fetches(completed_fetches, scanned_fetches)
    save_completed_fetches(completed_fetches)
    logger.info("Completed fetches tracking updated based on existing files")

    # Initialize and run the fetcher
    fetcher = VahanFetcher(completed_fetches=completed_fetches, fetch_all=args.fetch_all)
    fetcher.run()