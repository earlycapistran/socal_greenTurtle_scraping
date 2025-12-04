import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime
import sqlite3
import re


def extract_doi(result_div):
    """
    Try to extract DOI from a result entry
    """
    # Look for DOI in links
    links = result_div.find_all('a')
    for link in links:
        href = link.get('href', '')
        # Check if link contains DOI
        if 'doi.org' in href:
            # Extract DOI from URL
            match = re.search(r'doi\.org/(10\.\d+/[^\s&]+)', href)
            if match:
                return match.group(1)

    # Look for DOI in text
    text = result_div.get_text()
    match = re.search(r'\b(10\.\d+/[^\s]+)', text)
    if match:
        return match.group(1)

    return None


def scrape_all_titles(url, max_pages=10):
    """
    Scrape all titles from a Google Scholar search URL

    Args:
        url: The Google Scholar search URL
        max_pages: Maximum number of pages to scrape

    Returns:
        list of dicts with title info
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]

    all_titles = []

    for page in range(max_pages):
        # Add pagination parameter
        page_url = url if page == 0 else f"{url}&start={page * 10}"

        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        try:
            print(f"    Scraping page {page + 1}...")
            response = requests.get(page_url, headers=headers, timeout=15)

            if response.status_code != 200:
                print(f"    HTTP {response.status_code} on page {page + 1}")
                break

            soup = BeautifulSoup(response.content, 'html.parser')

            # Check for CAPTCHA
            if soup.find('form', {'id': 'captcha-form'}) or 'unusual traffic' in soup.get_text().lower():
                print("    WARNING: CAPTCHA detected!")
                return None

            # Find all result divs
            result_divs = soup.find_all('div', {'class': 'gs_r gs_or gs_scl'})

            if not result_divs:
                print(f"    No more results on page {page + 1}")
                break

            for result_div in result_divs:
                # Get title
                title_elem = result_div.find('h3', {'class': 'gs_rt'})
                if not title_elem:
                    continue

                # Clean title text
                for tag in title_elem.find_all(['span']):
                    tag.unwrap()
                title_text = title_elem.get_text().strip()

                # Try to extract DOI
                doi = extract_doi(result_div)

                all_titles.append({
                    'title': title_text,
                    'doi': doi,
                    'page': page + 1
                })

            print(f"    Found {len(result_divs)} results on page {page + 1}")

            # Delay between pages
            if page < max_pages - 1:
                wait_time = random.uniform(5, 10)
                print(f"    Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)

        except Exception as e:
            print(f"    Error on page {page + 1}: {e}")
            break

    return all_titles


def init_database(db_path='title_database.db'):
    """
    Initialize SQLite database with titles table
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS titles
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       species_search_term
                       TEXT,
                       base_search_terms
                       TEXT,
                       main_term
                       TEXT,
                       title
                       TEXT,
                       doi
                       TEXT,
                       page
                       INTEGER,
                       search_url
                       TEXT,
                       scraped_date
                       TEXT
                   )
                   ''')

    # Create indexes for faster filtering
    cursor.execute('''
                   CREATE INDEX IF NOT EXISTS idx_species
                       ON titles(species_search_term)
                   ''')

    cursor.execute('''
                   CREATE INDEX IF NOT EXISTS idx_title
                       ON titles(title)
                   ''')

    conn.commit()
    return conn


def save_to_database(conn, records):
    """
    Save title records to SQLite database
    """
    cursor = conn.cursor()

    for record in records:
        cursor.execute('''
                       INSERT INTO titles
                       (species_search_term, base_search_terms, main_term, title, doi, page, search_url, scraped_date)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ''', (
                           record['species_search_term'],
                           record['base_search_terms'],
                           record.get('main_term', ''),
                           record['title'],
                           record['doi'],
                           record['page'],
                           record['search_url'],
                           record['scraped_date']
                       ))

    conn.commit()


# Read the results CSV from Script 1
print("Reading results CSV...")
df = pd.read_csv('archeo_results_final.csv')

# Ask how many pages to scrape per search
print("\nHow many pages to scrape per search?")
print("(1 page ≈ 10 results)")
max_pages = int(input("Pages per search (1-20): "))

# Initialize database
print("\nInitializing database...")
conn = init_database('title_database.db')

# Create a list to store all title records for CSV
all_records = []

print(f"\nBuilding title database for {len(df)} searches...")
print("=" * 60)

try:
    for idx, row in df.iterrows():
        # Skip if no URL
        if pd.isna(row['search_url']):
            print(f"[{idx + 1}/{len(df)}] Skipping {row['species_search_term']} - no URL")
            continue

        print(f"[{idx + 1}/{len(df)}] Scraping: {row['species_search_term']}")

        # Scrape titles
        titles = scrape_all_titles(row['search_url'], max_pages)

        if titles is None:
            print(f"  CAPTCHA/Error - stopping")
            raise Exception("CAPTCHA detected - stopping database build")

        # Add metadata to each title record
        batch_records = []
        dois_found = 0
        for title_record in titles:
            full_record = {
                'species_search_term': row['species_search_term'],
                'base_search_terms': row['base_search_terms'],
                'main_term': row.get('main_term', ''),
                'title': title_record['title'],
                'doi': title_record['doi'],
                'page': title_record['page'],
                'search_url': row['search_url'],
                'scraped_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            if title_record['doi']:
                dois_found += 1
            batch_records.append(full_record)
            all_records.append(full_record)

        # Save to database
        save_to_database(conn, batch_records)

        print(f"  Scraped {len(titles)} titles ({dois_found} with DOIs)")
        print(f"  Total so far: {len(all_records)}")

        # Save progress CSV after each search
        progress_df = pd.DataFrame(all_records)
        progress_df.to_csv('title_database_progress.csv', index=False)

        # Delay between searches
        if idx < len(df) - 1:
            wait_time = random.uniform(30, 60)
            print(f"  Waiting {wait_time:.1f} seconds before next search...")
            time.sleep(wait_time)

except Exception as e:
    print(f"\n{'=' * 60}")
    print(f"DATABASE BUILD STOPPED: {e}")
    print(f"Progress saved")
    print(f"{'=' * 60}")
    # Save what we have
    if all_records:
        progress_df = pd.DataFrame(all_records)
        progress_df.to_csv('title_database_progress.csv', index=False)
    conn.close()
    raise

# Final save
final_df = pd.DataFrame(all_records)
final_df.to_csv('title_database_final.csv', index=False)

# Count DOIs
total_dois = final_df['doi'].notna().sum()

print("=" * 60)
print("DATABASE BUILD COMPLETE!")
print(f"Total titles scraped: {len(all_records)}")
print(f"Titles with DOIs: {total_dois} ({total_dois / len(all_records) * 100:.1f}%)")
print(f"Saved to:")
print(f"  - SQLite: title_database.db")
print(f"  - CSV: title_database_final.csv")
print("=" * 60)

# Close database connection
conn.close()
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime
import sqlite3
import re


def extract_doi(result_div):
    """
    Try to extract DOI from a result entry
    """
    # Look for DOI in links
    links = result_div.find_all('a')
    for link in links:
        href = link.get('href', '')
        # Check if link contains DOI
        if 'doi.org' in href:
            # Extract DOI from URL
            match = re.search(r'doi\.org/(10\.\d+/[^\s&]+)', href)
            if match:
                return match.group(1)

    # Look for DOI in text
    text = result_div.get_text()
    match = re.search(r'\b(10\.\d+/[^\s]+)', text)
    if match:
        return match.group(1)

    return None


def scrape_all_titles(url, max_pages=10):
    """
    Scrape all titles from a Google Scholar search URL

    Args:
        url: The Google Scholar search URL
        max_pages: Maximum number of pages to scrape

    Returns:
        list of dicts with title info
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]

    all_titles = []

    for page in range(max_pages):
        # Add pagination parameter
        page_url = url if page == 0 else f"{url}&start={page * 10}"

        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        try:
            print(f"    Scraping page {page + 1}...")
            response = requests.get(page_url, headers=headers, timeout=15)

            if response.status_code != 200:
                print(f"    HTTP {response.status_code} on page {page + 1}")
                break

            soup = BeautifulSoup(response.content, 'html.parser')

            # Check for CAPTCHA
            if soup.find('form', {'id': 'captcha-form'}) or 'unusual traffic' in soup.get_text().lower():
                print("    WARNING: CAPTCHA detected!")
                return None

            # Find all result divs
            result_divs = soup.find_all('div', {'class': 'gs_r gs_or gs_scl'})

            if not result_divs:
                print(f"    No more results on page {page + 1}")
                break

            for result_div in result_divs:
                # Get title
                title_elem = result_div.find('h3', {'class': 'gs_rt'})
                if not title_elem:
                    continue

                # Clean title text
                for tag in title_elem.find_all(['span']):
                    tag.unwrap()
                title_text = title_elem.get_text().strip()

                # Try to extract DOI
                doi = extract_doi(result_div)

                all_titles.append({
                    'title': title_text,
                    'doi': doi,
                    'page': page + 1
                })

            print(f"    Found {len(result_divs)} results on page {page + 1}")

            # Delay between pages
            if page < max_pages - 1:
                wait_time = random.uniform(5, 10)
                print(f"    Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)

        except Exception as e:
            print(f"    Error on page {page + 1}: {e}")
            break

    return all_titles


def init_database(db_path='title_database.db'):
    """
    Initialize SQLite database with titles table
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS titles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            species_search_term TEXT,
            base_search_terms TEXT,
            main_term TEXT,
            title TEXT,
            doi TEXT,
            page INTEGER,
            search_url TEXT,
            scraped_date TEXT
        )
    ''')

    # Create indexes for faster filtering
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_species 
        ON titles(species_search_term)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_title 
        ON titles(title)
    ''')

    conn.commit()
    return conn


def save_to_database(conn, records):
    """
    Save title records to SQLite database
    """
    cursor = conn.cursor()

    for record in records:
        cursor.execute('''
            INSERT INTO titles 
            (species_search_term, base_search_terms, main_term, title, doi, page, search_url, scraped_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record['species_search_term'],
            record['base_search_terms'],
            record.get('main_term', ''),
            record['title'],
            record['doi'],
            record['page'],
            record['search_url'],
            record['scraped_date']
        ))

    conn.commit()


# Read the results CSV from Script 1
print("Reading results CSV...")
df = pd.read_csv('archeo_results_final.csv')

# Ask how many pages to scrape per search
print("\nHow many pages to scrape per search?")
print("(1 page ≈ 10 results)")
max_pages = int(input("Pages per search (1-20): "))

# Initialize database
print("\nInitializing database...")
conn = init_database('title_database.db')

# Create a list to store all title records for CSV
all_records = []

print(f"\nBuilding title database for {len(df)} searches...")
print("=" * 60)

try:
    for idx, row in df.iterrows():
        # Skip if no URL
        if pd.isna(row['search_url']):
            print(f"[{idx + 1}/{len(df)}] Skipping {row['species_search_term']} - no URL")
            continue

        print(f"[{idx + 1}/{len(df)}] Scraping: {row['species_search_term']}")

        # Scrape titles
        titles = scrape_all_titles(row['search_url'], max_pages)

        if titles is None:
            print(f"  CAPTCHA/Error - stopping")
            raise Exception("CAPTCHA detected - stopping database build")

        # Add metadata to each title record
        batch_records = []
        dois_found = 0
        for title_record in titles:
            full_record = {
                'species_search_term': row['species_search_term'],
                'base_search_terms': row['base_search_terms'],
                'main_term': row.get('main_term', ''),
                'title': title_record['title'],
                'doi': title_record['doi'],
                'page': title_record['page'],
                'search_url': row['search_url'],
                'scraped_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            if title_record['doi']:
                dois_found += 1
            batch_records.append(full_record)
            all_records.append(full_record)

        # Save to database
        save_to_database(conn, batch_records)

        print(f"  Scraped {len(titles)} titles ({dois_found} with DOIs)")
        print(f"  Total so far: {len(all_records)}")

        # Save progress CSV after each search
        progress_df = pd.DataFrame(all_records)
        progress_df.to_csv('title_database_progress.csv', index=False)

        # Delay between searches
        if idx < len(df) - 1:
            wait_time = random.uniform(30, 60)
            print(f"  Waiting {wait_time:.1f} seconds before next search...")
            time.sleep(wait_time)

except Exception as e:
    print(f"\n{'='*60}")
    print(f"DATABASE BUILD STOPPED: {e}")
    print(f"Progress saved")
    print(f"{'='*60}")
    # Save what we have
    if all_records:
        progress_df = pd.DataFrame(all_records)
        progress_df.to_csv('title_database_progress.csv', index=False)
    conn.close()
    raise

# Final save
final_df = pd.DataFrame(all_records)
final_df.to_csv('title_database_final.csv', index=False)

# Count DOIs
total_dois = final_df['doi'].notna().sum()

print("=" * 60)
print("DATABASE BUILD COMPLETE!")
print(f"Total titles scraped: {len(all_records)}")
print(f"Titles with DOIs: {total_dois} ({total_dois/len(all_records)*100:.1f}%)")
print(f"Saved to:")
print(f"  - SQLite: title_database.db")
print(f"  - CSV: title_database_final.csv")
print("=" * 60)

# Close database connection
conn.close()