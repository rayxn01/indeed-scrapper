# Indeed Scraper Documentation

This document explains what the Indeed Job Scraper does and how its various components work together to extract, filter, and categorise job listings from Indeed.

## What It Does

The Indeed Scraper automates the process of finding highly relevant e-commerce and marketplace jobs (especially related to Amazon, Shopify, DTC, etc.) on Indeed. 

Instead of searching for highly specific job titles which might miss variations, the scraper uses a **broad search strategy**:
1. It searches for broad terms (like "Amazon marketplace", "Ecommerce manager").
2. It collects every job card from the search results.
3. It opens each job to fetch the *full* job description.
4. It filters the jobs locally based on whether their title or description contains specific mandatory keywords (e.g., "amazon" or other marketplace terms).
5. If a job passes the filter, it is assigned a specific category (e.g., "Amazon-Specific", "Leadership Roles") based on keyword rules.
6. The compiled list of relevant jobs is saved into CSV and JSON files, alongside a statistical summary. Rejected jobs are saved to a separate log.

---

## How It Works (Component Breakdown)

The system is modular, separated into configuration, logic, search rules, and output handling. 

### 1. `scraper.py` (Core Engine)
This is the main script that orchestrated the entire scraping process.
- **Automation**: Uses Selenium WebDriver (Headless Chrome) to navigate Indeed like a human.
- **Search & Pagination (`_scrape_query`)**: Given a search query, it loads the page and parses job cards using BeautifulSoup. It automatically handles pagination to grab a configurable number of jobs per query.
- **Fetching Descriptions (`_fetch_full_description`)**: To get the complete picture of a job, it opens each job's specific link in a new tab, extracts the description, and closes the tab.
- **Filtering (`_is_relevant`)**: Ensures a job is highly relevant by checking the combined title and description text against required terms (e.g., checking if "amazon" or "marketplace" exists).
- **Categorization (`_categorize`)**: Once a job is accepted, it assigns it a category based on the presence of specific keywords defined in `keywords.json`.
- **Evasion Tactics**: Implements random delays (`rand_delay`), custom User-Agents, and specific Chrome options (like `--disable-blink-features=AutomationControlled`) to prevent Indeed from blocking the scraper.

### 2. `config.py` (Settings)
Controls the scraper's execution parameters without needing to modify the core code.
- **Search Parameters**: Sets the target `location` and `results_per_keyword`.
- **Filtering Logic**: Toggles strict filtering (`require_amazon`, `require_marketplace`). If turned off, the scraper will keep all jobs it finds.
- **Delays**: Defines the minimum and maximum random wait times (in seconds) between requests, pagination, and opening job pages to mimic human browsing behavior.
- **Browser Output**: Options like `headless` (run without opening a visible browser window), `max_retries`, and `timeout`.

### 3. `keywords.json` (Taxonomy & Rules)
Acts as the brain for the scraper's search and categorisation strategy:
- `broad_searches`: The actual search queries typed into Indeed's search bar.
- `relevance_filters`: The mandatory words that signify a job is relevant (checked during `_is_relevant`).
- `category_rules`: Groups of title and description keywords used to assign jobs to specific buckets (e.g., "Amazon-Specific", "Marketplace General", "Leadership Roles"). It also defines the priority order for categorization.

### 4. `save_results.py` (Output Manager)
Handles processing the scraped data into formatted files using `pandas` (for CSV) and the `json` library:
- `save_to_csv`: Exports the accepted jobs to a cleanly formatted, timestamped CSV file with a preferred column order.
- `save_to_json`: Exports to JSON for programmatic access.
- `generate_summary`: Prints a console summary (jobs kept by category, top locations, salary availability) at the very end of a run.

### 5. `api.py` (FastAPI Wrapper)
Provides an HTTP interface to trigger the scraper via a simple POST request (`/scrape`).
- **Usage**: You can run an API server that accepts requests containing keywords, location, and marketplace parameters.
- **Execution**: It uses Python's `subprocess` to trigger `scraper.py` programmatically. 
*(Note: As the script relies primarily on `config.py` now, this API wrapper is a template that might need its arguments synchronized with how `config.py` works if you intend to use it extensively).*
