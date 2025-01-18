import re
import csv

# Input and output file paths
input_file = "scraped_data3.txt"  # Replace with your raw text file name
output_file = "parsed_data3.csv"

# Initialize list to store parsed data
parsed_data = []

# Define regex patterns to extract fields
patterns = {
    "wallet": r"Wallet Address:\s*(.+)",
    "ticker": r"Ticker Name:\s*(.+)",
    "unrealized": r"Unrealized Value:\s*(.+)",
    "realized": r"Realized Profit:\s*(.+)",
    "total_profit": r"Total Profit:\s*(.+)",
    "balance": r"Balance:\s*(.+)",
    "position": r"Position %:\s*(.+)",
    "bought_avg": r"Bought Avg:\s*(.+)",
    "sold_avg": r"Sold Avg:\s*(.+)"
}

# Read the input file and process each block
with open(input_file, "r") as file:
    content = file.read()

# Split data by "Scraping data from PnL row"
blocks = content.split("Scraping data from PnL row")
for block in blocks[1:]:  # Skip the first part before the first row
    # Initialize a dictionary to store extracted fields
    row_data = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, block)
        row_data[key] = match.group(1).strip() if match else "N/A"
    
    # Condition to skip empty or invalid rows
    if row_data["ticker"] != "\\" and row_data["ticker"] != "":
        parsed_data.append(row_data)

# Write parsed data to a CSV file
with open(output_file, "w", newline="") as csvfile:
    fieldnames = [
        "wallet", "ticker", "unrealized", "realized", 
        "total_profit", "balance", "position", 
        "bought_avg", "sold_avg"
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()  # Write CSV header
    writer.writerows(parsed_data)

print(f"Data successfully parsed and saved to {output_file}")