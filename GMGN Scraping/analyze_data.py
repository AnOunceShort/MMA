import re

# Function to parse and clean Total Profit values
def parse_profit(value):
    try:
        value = value.replace("$", "").replace(",", "").replace("\\", "").strip()
        if "K" in value:
            return float(value.replace("K", "")) * 1000
        return float(value)
    except ValueError:
        return None  # Return None for parsing errors

# Function to find the top N most profitable trades across all wallets
def find_top_profitable_trades(data, top_n=5):
    print("\nFinding the Top Profitable Trades\n")
    lines = data.splitlines()

    current_wallet = None
    trades = []  # List of tuples: (profit, wallet, block)
    current_block = []

    for line in lines:
        if line.startswith("Wallet Address:"):
            if current_block:
                process_block_for_trades(current_block, trades, current_wallet)
                current_block = []
            current_wallet = line.split("Wallet Address:")[1].strip()

        if current_wallet:
            current_block.append(line)

    # Process the last block
    if current_block:
        process_block_for_trades(current_block, trades, current_wallet)

    # Sort trades by profit in descending order
    sorted_trades = sorted(trades, key=lambda x: x[0], reverse=True)

    # Display top N trades
    for idx, (profit, wallet, block) in enumerate(sorted_trades[:top_n], start=1):
        print(f"{idx}. Wallet Address: {wallet}\n   Profit: ${profit:,.2f}")
        print("   Associated Block:")
        print(block)
        print("--------")

def process_block_for_trades(block, trades, wallet):
    """Process a block of data to extract trade information."""
    for line in block:
        if "Total Profit:" in line:
            profit_value = line.split("Total Profit:")[1].strip()
            profit = parse_profit(profit_value)
            if profit is not None:
                trades.append((profit, wallet, "\n".join(block)))
                break  # Only one trade per block

# Function to find the single most profitable trade
def find_most_profitable(data):
    print("\nFinding the Most Profitable Ticker\n")
    lines = data.splitlines()

    current_wallet = None
    max_profit = -float('inf')
    most_profitable_ticker = None
    most_profitable_wallet = None
    most_profitable_block = None
    current_block = []

    for line in lines:
        if line.startswith("Wallet Address:"):
            if current_block:
                # Process the completed block
                for block_line in current_block:
                    if "Total Profit:" in block_line:
                        profit_value = block_line.split("Total Profit:")[1].strip()
                        profit = parse_profit(profit_value)
                        if profit is not None and profit > max_profit:
                            max_profit = profit
                            most_profitable_ticker = next(
                                (l.split("Ticker Name:")[1].strip() for l in current_block if "Ticker Name:" in l), None
                            )
                            most_profitable_wallet = current_wallet
                            most_profitable_block = "\n".join(current_block)
                current_block = []
            # Start a new block
            current_wallet = line.split("Wallet Address:")[1].strip()

        if current_wallet:
            current_block.append(line)

    # Process the last block
    if current_block:
        for block_line in current_block:
            if "Total Profit:" in block_line:
                profit_value = block_line.split("Total Profit:")[1].strip()
                profit = parse_profit(profit_value)
                if profit is not None and profit > max_profit:
                    max_profit = profit
                    most_profitable_ticker = next(
                        (l.split("Ticker Name:")[1].strip() for l in current_block if "Ticker Name:" in l), None
                    )
                    most_profitable_wallet = current_wallet
                    most_profitable_block = "\n".join(current_block)

    if most_profitable_ticker and most_profitable_wallet:
        print(f"Most Profitable Ticker: {most_profitable_ticker}")
        print(f"Wallet Address: {most_profitable_wallet}")
        print(f"Total Profit: ${max_profit:,.2f}")
        print("\nAssociated Block:")
        print(most_profitable_block)
    else:
        print("No valid profit data found.\n")

# Main function to load data and process user queries
def main():
    filename = input("Enter the file name for analysis (default: scraped_data.txt): ").strip() or "scraped_data.txt"
    try:
        with open(filename, "r") as file:
            data = file.read()
    except FileNotFoundError:
        print(f"Error: '{filename}' not found in the current directory.")
        return

    find_most_profitable(data)
    find_top_profitable_trades(data)

    while True:
        print("\nOptions:")
        print("1. Search for a ticker and its associated metrics.")
        print("2. Exit.")
        choice = input("\nEnter your choice: ")

        if choice == "1":
            ticker = input("Enter the ticker you want to search for: ")
            search_ticker_with_metrics(ticker, data)
        elif choice == "2":
            print("Exiting the program. Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1 or 2.")

if __name__ == "__main__":
    main()