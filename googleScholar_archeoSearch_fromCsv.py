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

    # Print the actual URL
    full_url = f"{url}?q={requests.utils.quote(query)}&hl=en"
    print(f"    URL: {full_url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)

        if response.status_code != 200:
            print(f"    HTTP {response.status_code}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Check for CAPTCHA
        if soup.find('form', {'id': 'captcha-form'}) or 'unusual traffic' in soup.get_text().lower():
            print("    WARNING: CAPTCHA detected!")
            raise Exception("CAPTCHA blocking - stopping analysis")

        # Debug: print what we found
        results_div = soup.find('div', {'id': 'gs_ab_md'})
        if results_div:
            print(f"    Results div text: {results_div.get_text()}")
        else:
            print(f"    WARNING: No results div found!")
            # Print first 500 chars of page to see what we got
            print(f"    Page preview: {soup.get_text()[:500]}")

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

        return None

    except Exception as e:
        print(f"    Error: {e}")
        return None


# Read the CSV file
print("Reading CSV file...")
df = pd.read_csv('archeo_searchTerms_data_readOnly.csv')

# Add new column for automated counts
df['automated_count'] = None
df['date_searched'] = None

print(f"\nFound {len(df)} searches to perform\n")
print("=" * 60)

# Process each row
for idx, row in df.iterrows():
    search_term = row['base_search_terms']

    # Add excluded terms if they exist
    if pd.notna(row['excluded_terms']):
        search_term = f"{search_term} {row['excluded_terms']}"

    # Add main term if it exists
    if pd.notna(row['main_term']) and row['main_term'].strip():
        search_term = f"{search_term} {row['main_term']}"

    print(f"[{idx + 1}/{len(df)}] Searching: {row['species_search_term']}")
    print(f"  Query: {search_term[:100]}...")

    # Get count
    count = get_scholar_count(search_term)

    # Save to dataframe
    df.at[idx, 'automated_count'] = count
    df.at[idx, 'date_searched'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"  Automated: {count}")
    print(f"  Manual: {row['num_results']}")

    # Check if they match
    if pd.notna(count) and pd.notna(row['num_results']):
        diff = abs(count - row['num_results'])
        if diff <= 5:
            print(f"  ✓ Match (diff: {diff})")
        else:
            print(f"  ✗ Difference: {diff}")

    # Save progress after each search
    df.to_csv('archeo_results_progress.csv', index=False)

# Add random delay between requests (10-30 seconds)
    if idx < len(df) - 1:  # Don't wait after the last one
        wait_time = random.uniform(10, 30)
        print(f"  Waiting {wait_time:.1f} seconds...")
        time.sleep(wait_time)

# Final save
df.to_csv('archeo_results_final.csv', index=False)

print("=" * 60)
print("COMPLETE!")
print(f"Results saved to: archeo_results_final.csv")

# Summary
successful = df['automated_count'].notna().sum()
failed = df['automated_count'].isna().sum()

print(f"\nSuccessful: {successful}/{len(df)}")
print(f"Failed: {failed}/{len(df)}")

if failed > 0:
    print("\nFailed searches:")
    failed_df = df[df['automated_count'].isna()]
    for idx, row in failed_df.iterrows():
        print(f"  - {row['species_search_term']}")