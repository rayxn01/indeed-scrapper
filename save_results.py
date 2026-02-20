"""
Save scraped job results to CSV and JSON files.
"""

import json
import pandas as pd
from datetime import datetime
from config import CONFIG


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def save_to_csv(jobs, filename=None):
    """Save jobs list to a CSV file. Returns the filename used."""
    if not jobs:
        print("No jobs to save.")
        return None

    if filename is None:
        filename = f"{CONFIG['output_file_prefix']}_{_timestamp()}.csv"

    df = pd.DataFrame(jobs)

    # Preferred column order
    preferred = ['category', 'keyword', 'search_query', 'title', 'company',
                 'location', 'salary', 'posted_date', 'url', 'description']
    cols = [c for c in preferred if c in df.columns] + \
           [c for c in df.columns if c not in preferred]
    df = df[cols]

    try:
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✅ Saved {len(jobs)} jobs → {filename}")
    except Exception as e:
        print(f"❌ Error saving CSV: {e}")

    return filename


def save_to_json(jobs, filename=None):
    """Save jobs list to a JSON file. Returns the filename used."""
    if not jobs:
        return None

    if filename is None:
        filename = f"{CONFIG['output_file_prefix']}_{_timestamp()}.json"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(jobs)} jobs → {filename}")
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")

    return filename


def generate_summary(jobs):
    """Print a human-readable summary of scraped jobs."""
    if not jobs:
        return

    df = pd.DataFrame(jobs)

    print("\n" + "="*60)
    print("📊 SCRAPING SUMMARY")
    print("="*60)
    print(f"Total Jobs Kept: {len(df)}")

    if 'category' in df.columns:
        print("\n📂 Jobs by Category:")
        for cat, cnt in df['category'].value_counts().items():
            print(f"   {cat}: {cnt}")

    if 'search_query' in df.columns:
        print("\n🔍 Jobs by Search Query:")
        for q, cnt in df['search_query'].value_counts().items():
            print(f"   {q}: {cnt}")

    if 'location' in df.columns:
        print("\n📍 Top 10 Locations:")
        for loc, cnt in df['location'].value_counts().head(10).items():
            print(f"   {loc}: {cnt}")

    jobs_with_salary = df[df['salary'].notna() & (df['salary'] != 'N/A')]
    print(f"\n💰 Jobs with Salary Info: {len(jobs_with_salary)} / {len(df)}")
    print("="*60 + "\n")
