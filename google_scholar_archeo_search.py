import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import re
import os
import random


def get_scholar_count(query, session):
    """
    Get result count from Google Scholar with improved detection avoidance
    """
    url = "https://scholar.google.com/scholar"
    params = {'q': query, 'hl': 'en'}  # Add language parameter

    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
    ]

    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        response = session.get(url, params=params, headers=headers, timeout=15)

        if response.status_code == 429:
            print(f"    Rate limited!")
            return None

        if response.status_code != 200:
            print(f"    HTTP {response.status_code}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Check for CAPTCHA or blocking
        if 'unusual traffic' in response.text.lower() or soup.find('form', {'id': 'captcha-form'}):
            print(f"    CAPTCHA/Block detected!")
            # Save HTML for debugging
            debug_filename = f"evidence/blocked_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"    Saved HTML to {debug_filename}")
            return None

        # Look for results count
        results_div = soup.find('div', {'id': 'gs_ab_md'})
        if results_div:
            text = results_div.get_text()
            # Try "About X results" format
            match = re.search(r'About ([\d,]+) results', text)
            if match:
                return int(match.group(1).replace(',', ''))
            # Try "X results" format
            match = re.search(r'([\d,]+) results', text)
            if match:
                return int(match.group(1).replace(',', ''))

        # If we got here, we couldn't find the count
        print(f"    Could not parse results count")
        # Save HTML for debugging
        debug_filename = f"evidence/debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(debug_filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"    Saved HTML to {debug_filename}")

        return None

    except Exception as e:
        print(f"    Error: {e}")
        return None


# Search terms with "faunal remains" added to all
search_data = [
    ('intitle:california AND intext:archaeology AND intext:"faunal remains" AND intext:"sea turtle" OR intext:"marine turtle" -"baja california" -"environmental impact"',
     'sea turtle'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"sea snake" -"baja california" -"environmental impact"',
     'sea snake'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"abalone" -"baja california" -"environmental impact"',
     'abalone'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"shellfish" -"baja california" -"environmental impact"',
     'shellfish'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"swordfish" -"baja california" -"environmental impact"',
     'swordfish'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"rock fish" -"baja california" -"environmental impact"',
     'rock fish'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"tuna" -"baja california" -"environmental impact"',
     'tuna'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:shark -"baja california" -"environmental impact"',
     'shark'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:barracuda -"baja california" -"environmental impact"',
     'barracuda'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:lingcod -"baja california" -"environmental impact"',
     'lingcod'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:sardine -"baja california" -"environmental impact"',
     'sardine'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:prickleback -"baja california" -"environmental impact"',
     'prickleback'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:flatfish -"baja california" -"environmental impact"',
     'flatfish'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:perch -"baja california" -"environmental impact"',
     'perch'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:sculpin -"baja california" -"environmental impact"',
     'sculpin'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:sheephead -"baja california" -"environmental impact"',
     'sheephead'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:rays -"baja california" -"environmental impact" -"x-ray" -"X-rays" -"X-ray"',
     'rays'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"guadalupe fur seal" -"baja california" -"environmental impact"',
     'guadalupe fur seal'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"northern fur seal" -"baja california" -"environmental impact"',
     'northern fur seal'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"steller sea lion" -"baja california" -"environmental impact"',
     'steller sea lion'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"sea otter" -"baja california" -"environmental impact"',
     'sea otter'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"elephant seal" -"baja california" -"environmental impact"',
     'elephant seal'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"harbor seal" -"baja california" -"environmental impact"',
     'harbor seal'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"california sea lion" -"baja california" -"environmental impact"',
     'california sea lion'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"common dolphin" -"baja california" -"environmental impact"',
     'common dolphin'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"short-finned pilot whale" -"baja california" -"environmental impact"',
     'short-finned pilot whale'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"risso dolphin" -"baja california" -"environmental impact"',
     'risso dolphin'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"pacific white-sided dolphin" -"baja california" -"environmental impact"',
     'pacific white-sided dolphin'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"northern right whale dolphin" -"baja california" -"environmental impact"',
     'northern right whale dolphin'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"killer whale" -"baja california" -"environmental impact"',
     'killer whale'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"sperm whale" -"baja california" -"environmental impact"',
     'sperm whale'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"bottlenose dolphin" -"baja california" -"environmental impact"',
     'bottlenose dolphin'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:seabird -"baja california" -"environmental impact"',
     'seabird'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:auklet -"baja california" -"environmental impact"',
     'auklet'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:cormorant -"baja california" -"environmental impact"',
     'cormorant'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"red abalone" -"baja california" -"environmental impact"',
     'red abalone'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"black abalone" -"baja california" -"environmental impact"',
     'black abalone'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:mussel -"baja california" -"environmental impact"',
     'mussel'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:urchin -"baja california" -"environmental impact"',
     'urchin'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:"turban snail" -"baja california" -"environmental impact"',
     'turban snail'),
    ('intitle:california AND intext:archaeology OR intext:archeology AND intext:"faunal remains" AND intext:chiton -"baja california" -"environmental impact"',
     'chiton'),
]

# Create evidence folder
os.makedirs('evidence', exist_ok=True)

# Create session for connection persistence
session = requests.Session()

results = []
total_searches = len(search_data)

print(f"Starting {total_searches} Google Scholar searches...")
print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

for idx, (query, taxon) in enumerate(search_data, 1):
    print(f"[{idx}/{total_searches}] Searching...")
    print(f"  Taxon: {taxon}")

    # Try up to 2 times with retry logic
    auto_count = None
    for attempt in range(2):
        if attempt > 0:
            wait = 45
            print(f"  Retry attempt {attempt + 1}, waiting {wait}s...")
            time.sleep(wait)

        auto_count = get_scholar_count(query, session)

        if auto_count is not None:
            break

    print(f"  Count: {auto_count}")

    results.append({
        'taxon': taxon,
        'search_term': query,
        'automated_count': auto_count,
        'date_searched': datetime.now().strftime('%Y-%m-%d'),
        'time_searched': datetime.now().strftime('%H:%M:%S')
    })

    # Save intermediate results after each search
    df = pd.DataFrame(results)
    df.to_csv('scholar_counts_progress.csv', index=False)

    # Random delay between 25-45 seconds to appear more human-like
    wait_time = random.randint(25, 45)
    print(f"  Waiting {wait_time} seconds...\n")
    time.sleep(wait_time)

# Final save
df = pd.DataFrame(results)
df.to_csv('scholar_counts_final.csv', index=False)

print("\n" + "=" * 50)
print("COMPLETE!")
print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Results saved to: scholar_counts_final.csv")
print("=" * 50)

# Summary statistics
print("\nSummary:")
print(f"Total searches: {len(results)}")
if any(r['automated_count'] for r in results):
    successful = sum(1 for r in results if r['automated_count'] is not None)
    failed = sum(1 for r in results if r['automated_count'] is None)
    print(f"Successful retrievals: {successful}")
    print(f"Failed retrievals: {failed}")

    if failed > 0:
        print("\nFailed searches:")
        for r in results:
            if r['automated_count'] is None:
                print(f"  - {r['taxon']}")