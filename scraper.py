"""
Indeed Job Scraper — Broad Search + Content-Filter Edition

Strategy:
  1. Run BROAD searches (e.g. "Amazon marketplace", "Amazon ecommerce") instead
     of exact job-title keywords.
  2. Collect every job card from search results (no title-match filter).
  3. Open each job page and fetch the FULL job description.
  4. Keep a job only if it passes the relevance filter:
       - "amazon" appears in title OR description  (configurable)
       - At least one marketplace-related term appears  (configurable)
  5. AFTER keeping the job, assign it a category based on its content.
     Keywords are used for categorisation only, NOT for filtering.
"""

import time
import random
import json
import logging
import re
from datetime import datetime
from urllib.parse import urlencode

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from config import CONFIG
import os as _os, json as _json

_runtime = {}
if _os.path.exists("runtime_config.json"):
    with open("runtime_config.json") as _f:
        _runtime = _json.load(_f)

# Override CONFIG values if api.py passed a runtime config
if _runtime:
    CONFIG['location']             = _runtime.get('location',             CONFIG['location'])
    CONFIG['results_per_keyword']  = _runtime.get('results_per_keyword',  CONFIG['results_per_keyword'])
    CONFIG['require_amazon']       = _runtime.get('require_amazon',       CONFIG['require_amazon'])
    CONFIG['require_marketplace']  = _runtime.get('require_marketplace',  CONFIG['require_marketplace'])
    CONFIG['headless']             = _runtime.get('headless',             CONFIG['headless'])

# ── END OF PATCH ─────
from save_results import save_to_csv, save_to_json, generate_summary

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rand_delay(range_cfg):
    """Sleep for a random duration within the configured [min, max] range."""
    lo, hi = range_cfg
    time.sleep(random.uniform(lo, hi))


def contains_any(text: str, terms: list) -> bool:
    """Return True if any term from *terms* appears in *text* (case-insensitive)."""
    text_lower = text.lower()
    return any(t.lower() in text_lower for t in terms)


# ---------------------------------------------------------------------------
# Company Blacklist — jobs from these companies will be rejected
# Add or remove companies here as needed
# ---------------------------------------------------------------------------
BLACKLISTED_COMPANIES = [
    "amazon", "walmart", "fedex", "ups", "target", "costco",
    "home depot", "kroger", "walgreens", "cvs", "best buy",
    "apple", "google", "microsoft", "meta", "netflix", "tesla",
    "nike", "adidas", "starbucks", "mcdonalds", "coca-cola",
    "pepsi", "johnson & johnson", "procter & gamble", "unilever",
    "ebay", "alibaba", "jd.com", "rakuten", "wayfair", "chewy",
    "etsy", "wish", "temu", "shein", "samsung", "sony", "lg",
    "deloitte", "accenture", "pwc", "kpmg", "ernst & young",
    "capgemini", "infosys", "tcs", "wipro", "cognizant",
]


# ---------------------------------------------------------------------------
# Main Scraper Class
# ---------------------------------------------------------------------------

class IndeedScraper:

    def __init__(self):
        self.driver = None
        self.jobs = []           # accepted jobs
        self.rejected = []       # jobs that failed the relevance filter
        self.seen_urls: set = set()
        self.kw_data = self._load_keywords()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _load_keywords(self) -> dict:
        try:
            with open('keywords.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("keywords.json not found — using minimal defaults.")
            return {
                "broad_searches": ["Amazon marketplace", "Amazon ecommerce"],
                "relevance_filters": {
                    "amazon_terms": ["amazon"],
                    "marketplace_terms": ["marketplace", "ecommerce", "seller"]
                },
                "category_rules": {}
            }

    def _setup_driver(self):
        logger.info("Setting up Chrome WebDriver …")
        opts = Options()
        if CONFIG['headless']:
            opts.add_argument("--headless=new")

        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        logger.info("WebDriver ready.")

    # ------------------------------------------------------------------
    # URL builder
    # ------------------------------------------------------------------

    def _build_url(self, query: str, start: int = 0) -> str:
        params = {'q': query, 'l': CONFIG['location'], 'sort': 'date'}
        if start > 0:
            params['start'] = start
        return "https://www.indeed.com/jobs?" + urlencode(params)

    # ------------------------------------------------------------------
    # Page loading with retry
    # ------------------------------------------------------------------

    def _load_page(self, url: str, wait_selector: str = None) -> bool:
        """
        Navigate to *url* with retry logic.
        Returns True on success, False after all retries exhausted.
        """
        for attempt in range(1, CONFIG['max_retries'] + 1):
            try:
                self.driver.get(url)
                if wait_selector:
                    WebDriverWait(self.driver, CONFIG['timeout']).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                    )
                return True
            except TimeoutException:
                logger.warning(f"Timeout on attempt {attempt}/{CONFIG['max_retries']} for {url}")
                if attempt < CONFIG['max_retries']:
                    time.sleep(3 * attempt)
            except WebDriverException as e:
                logger.warning(f"WebDriver error on attempt {attempt}: {e}")
                if attempt < CONFIG['max_retries']:
                    time.sleep(3 * attempt)
        logger.error(f"All retries failed for {url}")
        return False

    # ------------------------------------------------------------------
    # Relevance filter
    # ------------------------------------------------------------------

    def _is_relevant(self, title: str, description: str, company: str = "") -> bool:
        """
        Return True if the job passes ALL relevance requirements:
          - Company is NOT in the blacklist
          - (optional) "amazon" in title or description
          - (optional) at least one marketplace-related term present
        """

        # ── 1. Company blacklist check ─────────────────────────────────────
        company_lower = company.lower().strip()
        if any(blocked in company_lower for blocked in BLACKLISTED_COMPANIES):
            logger.debug(f"  BLACKLISTED COMPANY: {company}")
            return False

        # ── 2. Amazon relevance check ──────────────────────────────────────
        combined = (title + " " + description).lower()

        if CONFIG.get('require_amazon', True):
            amazon_terms = self.kw_data.get('relevance_filters', {}).get('amazon_terms', ['amazon'])
            if not contains_any(combined, amazon_terms):
                return False

        # ── 3. Marketplace relevance check ─────────────────────────────────
        if CONFIG.get('require_marketplace', True):
            mkt_terms = self.kw_data.get('relevance_filters', {}).get('marketplace_terms', [])
            if mkt_terms and not contains_any(combined, mkt_terms):
                return False

        return True

    # ------------------------------------------------------------------
    # Categorisation (runs AFTER the job is accepted)
    # ------------------------------------------------------------------

    def _categorize(self, title: str, description: str) -> str:
        """
        Assign a category by checking title and description against
        the rules defined in keywords.json → category_rules.
        Falls back to 'Uncategorized' if nothing matches.
        """
        combined = (title + " " + description).lower()
        rules = self.kw_data.get('category_rules', {})

        # Priority order
        priority = [
            "Amazon-Specific",
            "Leadership Roles",
            "Marketplace General",
            "Related Roles",
        ]

        for cat in priority:
            rule = rules.get(cat, {})
            title_kws = rule.get('title_keywords', [])
            desc_kws  = rule.get('description_keywords', [])

            if contains_any(title.lower(), title_kws) or contains_any(combined, desc_kws):
                return cat

        return "Uncategorized"

    # ------------------------------------------------------------------
    # Assign matched keywords (for reporting)
    # ------------------------------------------------------------------

    def _matched_keywords(self, title: str, description: str) -> str:
        """
        Return a comma-separated list of original user keywords that appear
        in the job title or description (used for the 'keyword' column).
        """
        all_kws = []
        rules = self.kw_data.get('category_rules', {})
        for cat_rule in rules.values():
            all_kws.extend(cat_rule.get('title_keywords', []))
            all_kws.extend(cat_rule.get('description_keywords', []))

        combined = (title + " " + description).lower()
        matched = [kw for kw in all_kws if kw.lower() in combined]
        # deduplicate while preserving order
        seen = set()
        unique = []
        for k in matched:
            if k not in seen:
                seen.add(k)
                unique.append(k)
        return ", ".join(unique[:5]) if unique else "broad search"

    # ------------------------------------------------------------------
    # Parse a single job card (from search results page)
    # ------------------------------------------------------------------

    def _parse_card(self, card_soup) -> dict | None:
        """Extract basic fields from a BeautifulSoup job card element."""
        try:
            # Title
            title_el = card_soup.find('h2', class_='jobTitle')
            title = title_el.get_text(strip=True) if title_el else ""

            # URL / job key
            link_el = card_soup.find('a', href=True)
            href = link_el['href'] if link_el else ""
            if href and not href.startswith('http'):
                href = "https://www.indeed.com" + href
            # extract jk param for canonical URL
            jk_match = re.search(r'jk=([a-f0-9]+)', href)
            url = f"https://www.indeed.com/viewjob?jk={jk_match.group(1)}" if jk_match else href

            if not url or url in self.seen_urls:
                return None
            self.seen_urls.add(url)

            # Company
            co_el = (card_soup.find('span', {'data-testid': 'company-name'})
                     or card_soup.find('span', class_='companyName'))
            company = co_el.get_text(strip=True) if co_el else "N/A"

            # Location
            loc_el = (card_soup.find('div', {'data-testid': 'text-location'})
                      or card_soup.find('div', class_='companyLocation'))
            location = loc_el.get_text(strip=True) if loc_el else "N/A"

            # Salary
            sal_el = (card_soup.find('div', class_='salary-snippet-container')
                      or card_soup.find('div', {'data-testid': 'attribute_snippet_testid'}))
            salary = sal_el.get_text(strip=True) if sal_el else "N/A"

            # Snippet description (short)
            snip_el = card_soup.find('div', class_='job-snippet')
            snippet = snip_el.get_text(strip=True) if snip_el else ""

            # Posted date
            date_el = card_soup.find('span', class_='date')
            posted_date = date_el.get_text(strip=True).replace("Posted", "").strip() if date_el else "N/A"

            return {
                'title': title,
                'company': company,
                'location': location,
                'salary': salary,
                'url': url,
                'description': snippet,   # will be replaced with full desc below
                'posted_date': posted_date,
            }
        except Exception as e:
            logger.debug(f"Card parse error: {e}")
            return None

    # ------------------------------------------------------------------
    # Fetch full job description by opening the job page
    # ------------------------------------------------------------------

    def _fetch_full_description(self, url: str) -> str:
        """
        Open the job detail page in a new tab and extract the full description.
        Closes the tab and returns to the search results tab.
        Returns empty string on failure (fallback — job is still kept).
        """
        if not url or not url.startswith('http'):
            return ""

        try:
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])

            rand_delay(CONFIG['delay_open_job'])

            # Try to wait for the description element
            full_text = ""
            for attempt in range(1, CONFIG['max_retries'] + 1):
                try:
                    desc_el = WebDriverWait(self.driver, CONFIG['timeout']).until(
                        EC.presence_of_element_located((By.ID, "jobDescriptionText"))
                    )
                    full_text = desc_el.text.strip()
                    break
                except TimeoutException:
                    logger.warning(f"  Description timeout (attempt {attempt}) for {url}")
                    if attempt < CONFIG['max_retries']:
                        time.sleep(2 * attempt)

        except Exception as e:
            logger.warning(f"  Could not open job page {url}: {e}")
        finally:
            # Always close the tab and return to search results
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except Exception:
                pass

        return full_text

    # ------------------------------------------------------------------
    # Scrape one search query (with pagination)
    # ------------------------------------------------------------------

    def _scrape_query(self, query: str):
        logger.info(f"\n{'='*60}")
        logger.info(f"  SEARCH: {query}")
        logger.info(f"{'='*60}")

        start = 0
        collected = 0
        max_collect = CONFIG['results_per_keyword']

        while collected < max_collect:
            url = self._build_url(query, start)
            logger.info(f"  Page URL: {url}")

            ok = self._load_page(url, wait_selector='#mosaic-provider-jobcards, .jobsearch-ResultsList')
            if not ok:
                logger.error(f"  Skipping query '{query}' — page failed to load after retries.")
                break

            rand_delay(CONFIG['delay_between_pages'])

            soup = BeautifulSoup(self.driver.page_source, 'lxml')

            # Find job cards — try multiple selectors for resilience
            cards = soup.find_all('div', class_='job_seen_beacon')
            if not cards:
                cards = soup.find_all('td', class_='resultContent')
            if not cards:
                logger.warning("  No job cards found on this page — may be blocked or end of results.")
                break

            logger.info(f"  Found {len(cards)} cards on page (start={start})")

            for card in cards:
                if collected >= max_collect:
                    break

                job = self._parse_card(card)
                if not job:
                    continue

                # ── Early company blacklist check BEFORE fetching description ──
                # This saves time by not opening blacklisted company pages at all
                if any(blocked in job.get('company', '').lower() for blocked in BLACKLISTED_COMPANIES):
                    logger.debug(f"  BLACKLISTED (skipped fetch): {job['company']}")
                    self.rejected.append(job)
                    continue

                # Fetch full description
                if CONFIG.get('save_full_description', True):
                    full_desc = self._fetch_full_description(job['url'])
                    if full_desc:
                        job['description'] = full_desc

                # ---- Relevance filter (includes company check) ----
                if not self._is_relevant(job['title'], job['description'], job.get('company', '')):
                    logger.debug(f"  REJECTED: {job['title']} @ {job.get('company', '')}")
                    job['search_query'] = query
                    self.rejected.append(job)
                    continue

                # ---- Categorise & tag ----
                job['category'] = self._categorize(job['title'], job['description'])
                job['keyword']  = self._matched_keywords(job['title'], job['description'])
                job['search_query'] = query

                self.jobs.append(job)
                collected += 1
                logger.info(f"  ✅ KEPT [{collected}]: {job['title']} @ {job['company']} — {job['category']}")

            # Pagination
            try:
                self.driver.find_element(By.CSS_SELECTOR, '[data-testid="pagination-page-next"]')
            except Exception:
                logger.info("  No next page — end of results for this query.")
                break

            start += 10
            rand_delay(CONFIG['delay_between_requests'])

        logger.info(f"  Query done. Kept {collected} jobs (rejected {len(self.rejected)} so far total).")

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self):
        self._setup_driver()

        broad_searches = _runtime.get('keywords') or self.kw_data.get('broad_searches', [])
        logger.info(f"\n🚀 Starting scraper — {len(broad_searches)} broad search queries")
        logger.info(f"   require_amazon={CONFIG['require_amazon']}  require_marketplace={CONFIG['require_marketplace']}")
        logger.info(f"   results_per_query={CONFIG['results_per_keyword']}  headless={CONFIG['headless']}\n")

        try:
            for query in broad_searches:
                self._scrape_query(query)
                rand_delay(CONFIG['delay_between_requests'])

        except KeyboardInterrupt:
            logger.info("\n⚠️  Interrupted by user — saving collected jobs …")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        finally:
            if self.driver:
                self.driver.quit()

            valid = [j for j in self.jobs if j.get('title') and j['title'] != 'N/A']
            logger.info(f"\n✨ Scraping complete — {len(valid)} jobs kept, {len(self.rejected)} rejected.")

            if valid:
                save_to_csv(valid)
                save_to_json(valid)
                generate_summary(valid)
            else:
                logger.warning("No jobs passed the filter. Try setting require_amazon=False or require_marketplace=False in config.py.")

            # Optionally save rejected jobs for inspection
            if self.rejected:
                ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                rej_file = f"rejected_indeed_jobs_{ts}.csv"
                save_to_csv(self.rejected, filename=rej_file)
                logger.info(f"Rejected jobs saved to {rej_file}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    scraper = IndeedScraper()
    scraper.run()