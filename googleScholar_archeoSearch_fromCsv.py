import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import re
import random


def get_scholar_count(query):
    """
    Get result count from Google Scholar
    """
    url = "https://scholar.google.com/scholar"
    params = {'q': query, 'hl': 'en'}

    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)

        if response.status_code != 200:
            print(f"    HTTP {response.status_code}")
            raise Exception(f"HTTP error {response.status_code} - stopping analysis")

        soup = BeautifulSoup(response.content, 'html.parser')

        # Check for CAPTCHA
        if soup.find('form', {'id': 'captcha-form'}) or 'unusual traffic' in soup.get_text().lower():
            print("    WARNING: CAPTCHA detected!")
            raise Exception("CAPTCHA blocking - stopping analysis")

        # Look for results count
        results_div = soup.find('div', {'id': 'gs_ab_md'})
        if results_div:
            text = results_div.get_text()
            print(f"    Results div text: {text}")

            # Try "About X results" format
            match = re.search(r'About ([\d,]+) results?', text)
            if match:
                return int(match.group(1).replace(',', ''))

            # Try "X results" or "X result" format (singular or plural)
            match = re.search(r'([\d,]+) results?', text)
            if match:
                return int(match.group(1).replace(',', ''))

            # If we found the div but no match, likely 0 results
            print(f"    WARNING: Results div found but no count pattern matched")
            print(f"    Page preview: {soup.get_text()[:500]}")
            return 0
        else:
            print(f"    WARNING: No results div found!")
            print(f"    Page preview: {soup.get_text()[:500]}")
            return 0

    except Exception as e:
        print(f"    Error: {e}")
        return None


# Read the CSV file
print("Reading CSV file...")
df = pd.read_csv('archeo_searchTerms_data_readOnly.csv')

# Add new columns
df['automated_count'] = None
df['search_url'] = None
df['date_searched'] = None

print(f"\nFound {len(df)} searches to perform\n")
print("=" * 60)

# Process each row
try:
    for idx, row in df.iterrows():
        search_term = row['base_search_terms']

        # Add excluded terms if they exist
        if pd.notna(row['excluded_terms']):
            search_term = f"{search_term} {row['excluded_terms']}"

        # Add main term if it exists
        if pd.notna(row['main_term']):
            search_term = f"{search_term} {row['main_term']}"

        # Ensure search_term is a string
        search_term = str(search_term)

        # Build the URL
        base_url = "https://scholar.google.com/scholar"
        full_url = f"{base_url}?q={requests.utils.quote(search_term)}&hl=en"

        print(f"[{idx + 1}/{len(df)}] Searching: {row['species_search_term']}")
        print(f"  Full Query: {search_term}")
        print(f"  URL: {full_url}")

        # Get count
        count = get_scholar_count(search_term)

        # Save to dataframe
        df.at[idx, 'automated_count'] = count
        df.at[idx, 'search_url'] = full_url
        df.at[idx, 'date_searched'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print(f"  Automated: {count}")

        # Save progress after each search
        df.to_csv('archeo_results_progress.csv', index=False)

        # Random delay between requests
        if idx < len(df) - 1:
            wait_time = random.uniform(15, 30)
            print(f"  Waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)

except Exception as e:
    print(f"\n{'=' * 60}")
    print(f"ANALYSIS STOPPED DUE TO ERROR: {e}")
    print(f"Progress saved to: archeo_results_progress.csv")
    print(f"{'=' * 60}")
    df.to_csv('archeo_results_progress.csv', index=False)
    raise

# Final save
df.to_csv('archeo_results_final.csv', index=False)

print("=" * 60)
print("COMPLETE!")
print(f"Results saved to: archeo_results_final.csv")