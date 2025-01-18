import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import math
import numpy as np
import os

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
    node_sizes = {}  # New dictionary to store node sizes
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

    # Set wallet positions
    for i, (wallet, tickers) in enumerate(wallet_ticker_map.items()):
        angle = (2 * math.pi * i) / num_wallets
        radius = 6
        wallet_x = radius * math.cos(angle)
        wallet_y = radius * math.sin(angle)
        pos[wallet] = np.array([wallet_x, wallet_y])
        node_sizes[wallet] = 1000  # Larger size for wallet nodes
        
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
                node_sizes[ticker_id] = 100  # Small size for zero profit
            else:
                numeric_profit = parse_profit_value(profit_value)
                if numeric_profit >= 0:
                    # Moderate distance scaling with log
                    ticker_radius = 0.8 + (math.log10(abs(numeric_profit) + 1) * 0.2)
                    # Node size scaling with log
                    node_sizes[ticker_id] = 100 + (math.log10(abs(numeric_profit) + 1) * 50)
                else:
                    ticker_radius = 0.8
                    node_sizes[ticker_id] = 100  # Base size for negative profit
                
                print(f"Ticker: {ticker}, Profit: {profit_value}, Radius: {ticker_radius}, Size: {node_sizes[ticker_id]}")
            
            ticker_x = wallet_x + ticker_radius * math.cos(ticker_angle)
            ticker_y = wallet_y + ticker_radius * math.sin(ticker_angle)
            pos[ticker_id] = np.array([ticker_x, ticker_y])
    
    return pos, node_sizes

def create_visualization(data, output_file='wallet_visualizer_memesai.html'):
    # Clean the ticker data by removing newlines
    data['ticker'] = data['ticker'].str.strip()
    
    # Create wallet-ticker mapping
    wallet_ticker_map = {}
    # Create ticker-profit mapping with wallet-specific keys
    ticker_profit_map = {}
    
    for wallet in data['wallet_address'].unique():
        wallet_data = data[data['wallet_address'] == wallet]
        wallet_tickers = wallet_data['ticker'].unique()
        wallet_ticker_map[wallet] = list(wallet_tickers)
        
        # Store profits for each ticker with wallet-specific keys
        for _, row in wallet_data.iterrows():
            ticker = row['ticker'].strip()  # Clean the ticker
            profit = row['total_profit']
            # Create a unique key for each wallet-ticker combination
            ticker_key = f"{wallet}_{ticker}"
            ticker_profit_map[ticker_key] = profit
    
    # Create graph
    G = nx.Graph()
    nodes = []
    edges = []
    
    # Process wallets and tickers
    for wallet, tickers in wallet_ticker_map.items():
        wallet_profit = data[data['wallet_address'] == wallet]['total_profit_numeric'].sum()
        
        # Add wallet node
        nodes.append({
            'id': wallet,
            'label': wallet,
            'size': 30,
            'profit': wallet_profit,
            'color': '#808080'
        })
        
        # Add ticker nodes and edges with wallet-specific IDs
        for ticker in tickers:
            ticker_id = f"{wallet}_{ticker}"
            # More flexible matching for any variation of "memesai"
            is_memesai = 'memesai' in ticker.lower().replace(' ', '')
            profit = ticker_profit_map[ticker_id]
            
            # Calculate size based on both MemesAI status and profit
            base_size = 20  # Default size for non-MemesAI tickers
            if is_memesai:
                if profit != '$0' and profit != '$0.00' and 'HODL' not in str(profit) and 'Sell All' not in str(profit):
                    base_size = 150  # Increased size for profitable MemesAI (changed from 35 to 50)
                else:
                    base_size = 25  # Standard MemesAI size for non-profitable ones
            
            nodes.append({
                'id': ticker_id,
                'label': ticker,
                'size': base_size,
                'profit': profit,
                'color': '#ff0000' if is_memesai else '#808080'
            })
            edges.append((wallet, ticker_id))
    
    # Add edges to graph
    G.add_edges_from(edges)
    
    # Create custom cluster layout
    pos, node_sizes = create_cluster_layout(G, wallet_ticker_map, ticker_profit_map)
    
    # Create edge trace
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')
    
    # Create node trace
    node_x = []
    node_y = []
    node_text = []
    node_size = []
    node_color = []
    node_line_width = []  # New list for border widths
    
    for i, node in enumerate(nodes):
        if 'memesai' in str(node['label']).lower():
            print(f"MemesAI node found: {node['label']}, Profit: {node['profit']}, Size: {node['size']}, Color: {node['color']}")
        x, y = pos[node['id']]
        node_x.append(x)
        node_y.append(y)
        node_text.append(f"{node['label']}: {node['profit']}")
        
        # Remove this line that was overriding our earlier size settings
        # node_size.append(40 if len(node['id']) < 45 else 15)
        
        # Instead, use the size from the node definition
        node_size.append(node['size'])
        
        # Keep the color from the node definition
        node_color.append(node['color'])
        
        # Set border width based on whether it's a ticker and if it has profit
        if len(node['id']) >= 45:  # If it's a ticker
            # Check if it's a no-profit ticker
            if (node['profit'] == '$0' or 
                node['profit'] == '$0.00' or 
                node['profit'] == 'HODL' or 
                node['profit'] == 'Sell All' or 
                node['profit'] == '$0\n0%' or 
                '$0' in str(node['profit'])):
                node_line_width.append(0)  # No border for no-profit tickers
            else:
                node_line_width.append(2)  # Border for profit tickers
        else:
            node_line_width.append(2)  # Border for wallet nodes
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        text=node_text,
        customdata=[node['id'] for node in nodes],
        marker=dict(
            size=node_size,
            color=node_color,
            line=dict(
                width=node_line_width,
                color='#FFFFFF'
            ),
            sizemode='area',
            sizeref=1,
        ))
    
    # Create figure
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                       title='Wallet-Ticker Visualization (MemesAI Highlighted in Red)',
                       titlefont_size=16,
                       showlegend=False,
                       hovermode='closest',
                       margin=dict(b=20,l=5,r=5,t=40),
                       xaxis=dict(
                           showgrid=False, 
                           zeroline=False, 
                           showticklabels=False,
                           autorange=True,
                           showspikes=False,
                           scaleanchor="y",
                           scaleratio=1
                       ),
                       yaxis=dict(
                           showgrid=False, 
                           zeroline=False, 
                           showticklabels=False,
                           autorange=True,
                           showspikes=False
                       ),
                       plot_bgcolor='black',
                       paper_bgcolor='black',
                       font=dict(color='#FFFFFF'),
                       width=1800,
                       height=1800,
                       dragmode='pan',
                       modebar=dict(
                           bgcolor='rgba(0,0,0,0.3)',
                           color='white',
                           activecolor='white'
                       ),
                       clickmode='event+select'
                   ))
    
    # Update the layout to include the click handling JavaScript
    fig.update_layout(
        clickmode='event',
        updatemenus=[],
        annotations=[],
    )

    # Define the config before using it
    config = {
        'scrollZoom': True,
        'modeBarButtons': [[
            'pan2d',
            'zoom2d',
            'resetScale2d'
        ]],
        'displayModeBar': True
    }

    # Add CSS for the info box overlay
    custom_css = """
    <style>
        .info-box {
            position: fixed;
            bottom: 20px;
            left: 20px;
            width: 300px;
            height: 400px;
            background-color: rgba(0, 0, 0, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            color: white;
            padding: 15px;
            font-family: Arial, sans-serif;
            z-index: 1000;
            backdrop-filter: blur(5px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
    </style>
    """

    # Create the HTML with custom JavaScript
    html_content = fig.to_html(
        config=config,
        include_plotlyjs=True,
        full_html=True
    )

    # Add the info box HTML
    info_box_html = """
    <div class="info-box">
    </div>
    """

    # Define our custom JavaScript
    custom_js = """
    <script>
        var plot = document.getElementsByClassName('plotly-graph-div')[0];
        var activeWallet = null;
        
        plot.on('plotly_click', function(data) {
            var point = data.points[0];
            console.log('Clicked point:', point);
            
            if (point.customdata && !point.customdata.includes('_')) {
                var clickedWallet = point.customdata;
                console.log('Clicked wallet:', clickedWallet);
                
                // Get current data
                var nodeTrace = plot.data[1];  // The node trace
                var edgeTrace = plot.data[0];  // The edge trace
                
                // Create visibility arrays
                var nodeVisibility = new Array(nodeTrace.x.length).fill(0);
                var edgeVisibility = new Array(edgeTrace.x.length).fill(0);
                
                // Mark nodes to show
                for (var i = 0; i < nodeTrace.customdata.length; i++) {
                    if (nodeTrace.customdata[i] === clickedWallet || 
                        nodeTrace.customdata[i].startsWith(clickedWallet + '_')) {
                        nodeVisibility[i] = 1;
                        
                        // Find connected edges
                        for (var j = 0; j < edgeTrace.x.length; j += 3) {
                            if (Math.abs(edgeTrace.x[j] - nodeTrace.x[i]) < 0.01 &&
                                Math.abs(edgeTrace.y[j] - nodeTrace.y[i]) < 0.01) {
                                edgeVisibility[j] = 1;
                                edgeVisibility[j + 1] = 1;
                                edgeVisibility[j + 2] = 1;
                            }
                        }
                    }
                }
                
                // Update the plot
                Plotly.restyle(plot, {
                    'marker.opacity': [nodeVisibility],
                    'opacity': [edgeVisibility]
                }, [1]);  // Update node trace
                
                Plotly.restyle(plot, {
                    'opacity': [edgeVisibility]
                }, [0]);  // Update edge trace
            }
        });
        
        // Double-click to reset
        plot.on('plotly_doubleclick', function() {
            Plotly.restyle(plot, {
                'marker.opacity': 1,
                'opacity': 1
            });
        });
    </script>
    </body>
    """

    # Insert our custom CSS, info box, and JavaScript before the closing body tag
    html_content = html_content.replace('</body>', f'{custom_css}{info_box_html}{custom_js}')
    
    # Write the modified HTML to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Visualization saved as '{output_file}'. Open in a browser to visit.")

def show_file_location(file_path):
    """Show the file location in the system's file explorer"""
    import platform
    import subprocess
    
    try:
        # Get absolute path
        abs_path = os.path.abspath(file_path)
        
        # Handle different operating systems
        system = platform.system()
        if system == 'Darwin':  # macOS
            subprocess.run(['open', '-R', abs_path])
        elif system == 'Windows':
            subprocess.run(['explorer', '/select,', abs_path])
        elif system == 'Linux':
            subprocess.run(['xdg-open', os.path.dirname(abs_path)])
            
        print(f"\nFile location: {abs_path}")
    except Exception as e:
        print(f"Error showing file location: {e}")

# Load data and create visualization
data = pd.read_csv('wallet_data_20241228_224935.csv')
data['total_profit_numeric'] = data['total_profit'].apply(parse_profit)
output_file = 'wallet_visualizer_memesai.html'
create_visualization(data, output_file)
show_file_location(output_file)