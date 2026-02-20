# Indeed Job Scraper (Python)

A Python-based web scraper that searches Indeed for job listings using specific keywords across multiple categories (Amazon, Marketplace, Leadership, and Related roles).

## Features

✅ **Multi-keyword search** - Scrapes jobs for 26 different keywords across 4 categories  
✅ **Selenium automation** - Uses Chrome WebDriver for reliable scraping  
✅ **Pagination support** - Automatically navigates through multiple pages  
✅ **Rate limiting** - Built-in delays to avoid being blocked  
✅ **Duplicate removal** - Automatically deduplicates job listings  
✅ **Multiple outputs** - Saves results to both CSV and JSON  
✅ **Detailed reporting** - Summary statistics by category, keyword, and location  
✅ **Virtual environment** - Isolated Python dependencies  

## Installation

### 1. Navigate to the project directory
```bash
cd "/Users/rayan/Documents/app script/script/indeed-scraper"
```

### 2. Create a Python virtual environment
```bash
python3 -m venv venv
```

### 3. Activate the virtual environment
```bash
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Run the scraper
Make sure your virtual environment is activated first!

```bash
source venv/bin/activate  # If not already activated
python scraper.py
```

### Deactivate virtual environment when done
```bash
deactivate
```

## Configuration

Edit `config.py` to customize scraper settings:

```python
CONFIG = {
    'location': '',              # '' = all locations, or 'Remote', 'New York, NY', etc.
    'results_per_keyword': 50,   # Number of jobs per keyword
    'delay_between_requests': 2, # Seconds between searches
    'delay_between_pages': 1.5,  # Seconds between pagination
    'headless': True,            # False to see browser
    'max_retries': 3,
    'timeout': 30
}
```

## Output Files

The scraper generates timestamped files:

- **`indeed_jobs_YYYY-MM-DD_HH-MM-SS.csv`** - Excel-compatible spreadsheet
- **`indeed_jobs_YYYY-MM-DD_HH-MM-SS.json`** - JSON format for data processing

### Output Fields

Each job listing includes:
- **category** - Job category
- **keyword** - Search keyword used
- **title** - Job title
- **company** - Company name
- **location** - Job location
- **salary** - Salary range (if available)
- **description** - Job description snippet
- **url** - Direct link to job posting
- **posted_date** - When the job was posted

## Keywords Searched

### Amazon-Specific (7 keywords)
- Amazon Marketplace Manager, Amazon Account Manager, Amazon Brand Manager
- Amazon PPC Specialist, Amazon Operations Manager
- FBA Manager, Amazon Vendor Manager

### Marketplace General (6 keywords)
- Marketplace Specialist, Marketplace Manager, E-commerce Manager
- Ecommerce Operations, Marketplace Operations, Digital Marketplace

### Leadership Roles (5 keywords)
- Director of Ecommerce, VP Ecommerce, Head of Marketplace
- Director Amazon, Ecommerce Director

### Related Roles (6 keywords)
- DTC Manager, Shopify Manager, Retail Media Manager
- Catalog Manager, Listing Specialist, Channel Manager

## Troubleshooting

### ChromeDriver Issues
The scraper automatically downloads the correct ChromeDriver version using `webdriver-manager`. If you encounter issues:
- Make sure Chrome browser is installed
- Try running with `headless: False` in config.py

### No Jobs Found
- **Rate limiting**: Indeed may be blocking requests. Increase delays in `config.py`
- **Network issues**: Check your internet connection
- **Selectors changed**: Indeed may have updated their HTML structure

### Scraper is Slow
- Reduce `results_per_keyword` to scrape fewer jobs
- Decrease `delay_between_requests` (but risk being blocked)

### Virtual Environment Issues
If you can't activate the virtual environment:
```bash
# Delete and recreate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Project Structure

```
indeed-scraper/
├── venv/                  # Virtual environment (created after setup)
├── scraper.py            # Main scraper script
├── config.py             # Configuration settings
├── save_results.py       # Result saving and reporting
├── keywords.json         # Job search keywords
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Requirements

- Python 3.7 or higher
- Chrome browser
- Internet connection

## Notes

⚠️ **Web scraping considerations**:
- Always respect Indeed's Terms of Service
- Use reasonable rate limits to avoid overloading servers
- Indeed's page structure may change, breaking the scraper
- Consider using Indeed's official API for production use

## License

ISC
