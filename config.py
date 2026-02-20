"""
Configuration settings for the Indeed Job Scraper.
"""

CONFIG = {
    # -------------------------------------------------------------------------
    # Search Settings
    # -------------------------------------------------------------------------

    # Location to search for jobs (e.g., "Remote", "New York, NY", "USA")
    # Leave empty "" to search everywhere
    'location': '',

    # Number of job CARDS to collect per broad search query (before filtering)
    'results_per_keyword': 50,

    # -------------------------------------------------------------------------
    # Filtering Logic
    # -------------------------------------------------------------------------

    # Must the word "amazon" appear in title OR description to keep the job?
    # Set True to enforce the Amazon relevance requirement.
    'require_amazon': True,

    # Must the job also have at least one marketplace-related term?
    # Set True to enforce marketplace relevance requirement.
    'require_marketplace': True,

    # -------------------------------------------------------------------------
    # Delays (seconds) — human-like behavior to avoid blocks
    # -------------------------------------------------------------------------

    # Random delay range between keyword searches: [min, max] seconds
    'delay_between_requests': [2, 5],

    # Random delay range between pagination clicks: [min, max] seconds
    'delay_between_pages': [1.5, 3.5],

    # Random delay range when opening a job detail page: [min, max] seconds
    'delay_open_job': [1.0, 2.5],

    # -------------------------------------------------------------------------
    # Browser Settings
    # -------------------------------------------------------------------------

    # Run Chrome in headless mode? True = invisible, False = visible window
    'headless': True,

    # Maximum number of retries per page load on timeout/error
    'max_retries': 3,

    # Timeout for page loading (seconds)
    'timeout': 30,

    # -------------------------------------------------------------------------
    # Output Settings
    # -------------------------------------------------------------------------

    # Prefix for output filenames
    'output_file_prefix': 'indeed_jobs',

    # Save full job description text in CSV/JSON?
    'save_full_description': True,
}
