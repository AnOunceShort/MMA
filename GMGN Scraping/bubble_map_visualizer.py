import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import math
import numpy as np
from pyvis.network import Network
import matplotlib.pyplot as plt

def parse_profit(value):
    """Convert profit strings to float values"""
    if pd.isna(value) or value == 'N/A' or value == '$0':
        return 0.0
    
    # Remove '$' and 'K' and 'M', convert to float
    try:
        value = value.replace('$', '').replace(',', '')
        if 'K' in value:
            return float(value.replace('K', '')) * 1000
        elif 'M' in value:
            return float(value.replace('M', '')) * 1000000
        else:
            return float(value)
    except:
        return 0.0

def create_cluster_layout(G, wallet_ticker_map, ticker_profit_map):
    pos = {}
    node_sizes = {}
    num_wallets = len(wallet_ticker_map)
    
    def parse_profit_value(profit_str):
        """Convert profit strings to float values"""
        if pd.isna(profit_str) or profit_str == 'N/A' or profit_str == '$0':
            return 0.0
        
        try:
            value_part = profit_str.split('\n')[0]
            is_negative = '-' in value_part
            value_part = value_part.replace('+', '').replace('-', '')
            value = value_part.replace('$', '').replace(',', '').replace('%', '').strip()
            multiplier = 1
            
            if 'K' in value:
                multiplier = 1000
                value = value.replace('K', '')
            elif 'M' in value:
                multiplier = 1000000
                value = value.replace('M', '')
                
            numeric_value = float(value) * multiplier
            return -numeric_value if is_negative else numeric_value
        except:
            print(f"Failed to parse profit value: {profit_str}")
            return 0.0

    def calculate_node_size(profit):
        """Calculate node size based on profit value"""
        if profit == 0:
            return 5  # Base size for zero profit
        
        abs_profit = abs(profit)
        # Use log scale with base size of 5, max size of 30
        size = 5 + min(25, math.log10(abs_profit + 1) * 5)
        return size

    # Set wallet positions
    for i, (wallet, tickers) in enumerate(wallet_ticker_map.items()):
        angle = (2 * math.pi * i) / num_wallets
        radius = 6
        wallet_x = radius * math.cos(angle)
        wallet_y = radius * math.sin(angle)
        pos[wallet] = np.array([wallet_x, wallet_y])
        node_sizes[wallet] = 30  # Reduced wallet node size
        
        num_tickers = len(tickers)
        
        for j, ticker in enumerate(tickers):
            ticker_id = f"{wallet}_{ticker}"
            profit_value = ticker_profit_map[ticker_id]
            
            ticker_angle = angle + (2 * math.pi * j) / num_tickers
            
            if (profit_value == '$0' or 
                profit_value == '$0.00' or 
                profit_value == 'HODL' or 
                profit_value == 'Sell All' or 
                profit_value == '$0\n0%' or 
                '$0' in str(profit_value)):
                ticker_radius = 0.4
                node_sizes[ticker_id] = calculate_node_size(0)
            else:
                numeric_profit = parse_profit_value(profit_value)
                if numeric_profit >= 0:
                    ticker_radius = 0.8 + (math.log10(abs(numeric_profit) + 1) * 0.2)
                    node_sizes[ticker_id] = calculate_node_size(numeric_profit)
                else:
                    ticker_radius = 0.8
                    node_sizes[ticker_id] = calculate_node_size(numeric_profit)
                
                print(f"Ticker: {ticker}, Profit: {profit_value}, Radius: {ticker_radius}, Size: {node_sizes[ticker_id]}")
            
            ticker_x = wallet_x + ticker_radius * math.cos(ticker_angle)
            ticker_y = wallet_y + ticker_radius * math.sin(ticker_angle)
            pos[ticker_id] = np.array([ticker_x, ticker_y])
    
    return pos, node_sizes

def visualize_network(G, pos, node_sizes, ticker_profit_map):
    # Create the plot
    plt.figure(figsize=(20, 20))
    
    # Draw nodes with fixed size for now
    nx.draw_networkx_nodes(G, pos, node_size=1000, node_color='lightblue', alpha=0.6)
    nx.draw_networkx_edges(G, pos, alpha=0.2)
    
    # Add labels with profit information
    labels = {}
    for node in G.nodes():
        if '_' in str(node):  # This is a ticker node
            try:
                profit_value = ticker_profit_map[node]
                ticker = node.split('_')[1]  # Extract ticker from node ID
                labels[node] = f"{ticker}\n{profit_value}"
            except:
                labels[node] = node
        else:
            labels[node] = node
    
    nx.draw_networkx_labels(G, pos, labels, font_size=8)
    
    # Save the plot
    plt.savefig('bubble_map.png')
    plt.close()

def create_visualization(data):
    # Create a graph
    G = nx.Graph()
    
    # Create mappings
    wallet_ticker_map = {}
    ticker_profit_map = {}
    
    # Print columns to debug
    print("Available columns:", data.columns.tolist())
    
    # Process data
    for _, row in data.iterrows():
        wallet = row['wallet_address']
        ticker = row['ticker']
        profit = row['total_profit']
        
        # Create wallet to ticker mapping
        if wallet not in wallet_ticker_map:
            wallet_ticker_map[wallet] = []
        wallet_ticker_map[wallet].append(ticker)
        
        # Create ticker to profit mapping
        ticker_id = f"{wallet}_{ticker}"
        ticker_profit_map[ticker_id] = profit
        
        # Add nodes and edges to graph
        G.add_node(wallet)
        G.add_node(ticker_id)
        G.add_edge(wallet, ticker_id)
    
    # Create layout
    pos, node_sizes = create_cluster_layout(G, wallet_ticker_map, ticker_profit_map)
    
    # Visualize with ticker_profit_map
    visualize_network(G, pos, node_sizes, ticker_profit_map)

# Read the data
data = pd.read_csv('wallet_data_20241228_224935.csv')
print("\nFirst few rows of data:")
print(data.head())
print("\nColumns in data:")
print(data.columns.tolist())

# Create the visualization
create_visualization(data)