import pandas as pd

# Read your results
df = pd.read_csv('archeo_results_final.csv')

# Create a review spreadsheet
review_df = df[['species_search_term', 'automated_count', 'search_url']].copy()

# Add columns for geographic filtering
review_df['titles_checked'] = 10  # Number of titles you'll review (first page)
review_df['outside_study_area'] = None  # How many are outside California/Southern California
review_df['in_study_area'] = None  # How many are in study area
review_df['adjusted_count'] = None  # Will calculate after review
review_df['notes'] = None  # Any observations
review_df['review_date'] = None

# Save template for manual review
review_df.to_csv('geographic_filter_template.csv', index=False)

print("=" * 60)
print("GEOGRAPHIC FILTERING TEMPLATE CREATED")
print("=" * 60)
print("\nSaved to: geographic_filter_template.csv")
print("\nInstructions:")
print("1. Open geographic_filter_template.csv in Excel/Google Sheets")
print("2. For each species, click the search_url link")
print("3. Review the first page of results (usually 10 titles)")
print("4. Count how many are OUTSIDE your study area")
print("5. Enter that number in 'outside_study_area' column")
print("6. The script will calculate adjusted counts")
print("\nWhen done, save the file and run the calculation script.")