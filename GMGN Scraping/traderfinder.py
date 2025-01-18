import pandas as pd
from datetime import datetime, date

def find_profitable_traders(csv_file='transfer1.csv', min_profit=20000):
    try:
        # Read CSV file
        print(f"Attempting to read {csv_file}...")
        df = pd.read_csv(csv_file)
        print(f"Successfully loaded {len(df)} transactions.")
        
        # Convert timestamp to datetime
        df['Time'] = pd.to_datetime(df['Time'], unit='s')
        
        # Filter for today's transactions
        today = date.today()
        df = df[df['Time'].dt.date == today]
        print(f"Found {len(df)} transactions for today.")
        
        # Convert Value column to numeric
        df['Value'] = pd.to_numeric(df['Value'])
        
        wallet_profits = {}
        wallet_transactions = {}
        
        # Analyze each wallet's transfers
        print("Analyzing wallet profits...")
        for wallet in df['From'].unique():
            # Get all transactions for this wallet
            wallet_txs = df[(df['From'] == wallet) | (df['To'] == wallet)].copy()
            
            # Calculate profits
            sent_mask = wallet_txs['From'] == wallet
            received_mask = wallet_txs['To'] == wallet
            
            wallet_txs.loc[sent_mask, 'Net'] = -wallet_txs.loc[sent_mask, 'Value']
            wallet_txs.loc[received_mask, 'Net'] = wallet_txs.loc[received_mask, 'Value']
            
            net_profit = wallet_txs['Net'].sum()
            
            # Store results if profit is above minimum threshold
            if net_profit >= min_profit:
                wallet_profits[wallet] = net_profit
                wallet_transactions[wallet] = wallet_txs[['Time', 'From', 'To', 'Value', 'Net']]
        
        return wallet_profits, wallet_transactions
    
    except FileNotFoundError:
        print(f"Error: Could not find the file '{csv_file}'. Make sure it's in the same directory as this script.")
        return {}, {}
    except Exception as e:
        print(f"Error: An unexpected error occurred: {str(e)}")
        return {}, {}

def print_results(profits, transactions):
    if not profits:
        print("No wallets found with profits of $20,000 or more for today.")
        return
        
    # Sort wallets by profit (highest to lowest)
    sorted_wallets = sorted(profits.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\nFound {len(profits)} wallets with profits over $20,000:")
    print("=" * 80)
    
    for wallet, profit in sorted_wallets:
        print(f"\nWallet: {wallet}")
        print(f"Total Profit: ${profit:,.2f}")
        print("\nTop Transactions:")
        print("-" * 40)
        
        # Show top 5 largest transactions for this wallet
        txs = transactions[wallet]
        top_txs = txs.nlargest(5, 'Value')
        for _, row in top_txs.iterrows():
            direction = "RECEIVED" if row['To'] == wallet else "SENT"
            print(f"Time: {row['Time']}")
            print(f"Direction: {direction}")
            print(f"Amount: ${row['Value']:,.2f}")
            print(f"Net Impact: ${row['Net']:,.2f}")
            print("-" * 40)

if __name__ == "__main__":
    profits, transactions = find_profitable_traders()
    print_results(profits, transactions)