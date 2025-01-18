import time
import csv
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import threading
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import sys
from datetime import datetime
import os
import traceback
import urllib.parse
import subprocess
import glob
import matplotlib.pyplot as plt

### no views were scraped with this program 

class MultiXScraper:
    def __init__(self, num_accounts=3):
        self.num_accounts = num_accounts
        self.drivers = []
        self.waits = []
        self.all_posts_lock = threading.Lock()
        
        # Add date range properties
        self.start_date = None
        self.end_date = None
        
        # Add account credentials
        self.accounts = [
            {"username": "flowinggrid", "password": "Nosignal777"},
            {"username": "flowinggridd", "password": "Nosignal777"},
            {"username": "7pillarsduo", "password": "Nosignal777"}
        ]
        
        # Initialize multiple Chrome instances
        for _ in range(num_accounts):
            driver = webdriver.Chrome()
            self.drivers.append(driver)
            self.waits.append(WebDriverWait(driver, 10))
            
    def create_new_desktop(self):
        """Create a new desktop and move windows there"""
        try:
            # AppleScript to create new desktop and move windows
            applescript = '''
            tell application "System Events"
                -- Create new desktop
                keystroke "]" using {control down, option down}
                
                -- Wait for animation
                delay 1
                
                -- Move Chrome windows to new desktop
                tell process "Google Chrome"
                    repeat with w in windows
                        keystroke "]" using {control down, shift down}
                        delay 0.5
                    end repeat
                end tell
            end tell
            '''
            
            # Execute AppleScript
            subprocess.run(['osascript', '-e', applescript])
            time.sleep(2)  # Wait for windows to move
            print("✅ Created new desktop and moved Chrome windows")
            return True
        except Exception as e:
            print(f"❌ Error creating new desktop: {str(e)}")
            return False

    def start_sessions(self):
        """Open X homepage in multiple windows and automatically login"""
        # Get screen size (assuming primary monitor)
        screen_width = 1920  # Default width, adjust if needed
        window_width = screen_width // len(self.drivers)
        window_height = 1000  # Adjust height as needed
        
        successful_logins = 0
        
        # First create a new desktop
        print("\nCreating new desktop for Chrome windows...")
        self.create_new_desktop()
        time.sleep(2)  # Wait for new desktop
        
        for i, (driver, wait) in enumerate(zip(self.drivers, self.waits), 1):
            try:
                # Calculate position for each window
                x_position = (i - 1) * window_width
                
                # Set window position and size
                driver.set_window_size(window_width, window_height)
                driver.set_window_position(x_position, 0)
                
                # Attempt auto-login
                account = self.accounts[i-1]
                print(f"\nAttempting to log in to Account {i}...")
                
                # Try login up to 3 times
                for attempt in range(3):
                    if attempt > 0:
                        print(f"Retry attempt {attempt + 1}...")
                        time.sleep(5)
                    
                    success = self.auto_login(
                        driver,
                        wait,
                        account["username"],
                        account["password"]
                    )
                    
                    if success:
                        successful_logins += 1
                        break
                        
                if not success:
                    print(f"❌ All login attempts failed for Account {i}")
                    
            except Exception as e:
                print(f"Error setting up Account {i}: {str(e)}")
        
        if successful_logins == 0:
            print("\n❌ No accounts were successfully logged in!")
            return False
        
        print(f"\n✅ Successfully logged in to {successful_logins} account(s)!")
        return successful_logins > 0
    
    def load_tickers(self, csv_file):
        """Load tickers from CSV file"""
        # Using existing load_tickers logic
        tickers = []
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header row
            for row in reader:
                if row and row[0].strip():
                    tickers.append(row[0].strip())
        return tickers
    
    def distribute_tickers(self, tickers):
        """Distribute tickers among accounts"""
        distributed = {}
        # Remove duplicates from tickers list
        unique_tickers = list(dict.fromkeys(tickers))
        for i, ticker in enumerate(unique_tickers):
            account_index = i % len(self.drivers)
            if account_index not in distributed:
                distributed[account_index] = []
            distributed[account_index].append(ticker)
        return distributed

    def get_date_range(self):
        """Get only the day for searching tweets (assumes 2025 January)"""
        print("\nPlease enter the day for searching tweets:")
        
        # Get only the day
        day = input("Which day of January 2025? (1-31): ")
        
        # Format the date strings (using January 2025)
        self.start_date = f"2025-01-{day.zfill(2)}"
        self.end_date = f"2025-01-{day.zfill(2)}"
        
        print(f"\nSet date range: {self.start_date}")

    def configure_advanced_search(self, driver, wait, ticker):
        """Configure advanced search with date range"""
        try:
            print(f"Configuring advanced search for {ticker}...")
            
            # Construct the search query using Twitter's syntax
            search_query = f"{ticker} since:{self.start_date}"
            encoded_query = urllib.parse.quote(search_query)
            search_url = f"https://twitter.com/search?q={encoded_query}&f=top"
            
            print(f"Navigating to search URL: {search_url}")
            driver.get(search_url)
            time.sleep(3)
            
            print("Advanced search configuration completed")
            return True
            
        except Exception as e:
            print(f"Error configuring advanced search: {str(e)}")
            traceback.print_exc()
            return False

    def search_ticker(self, driver, wait, ticker, limit=20):
        try:
            print(f"\nConfiguring search for {ticker}...")
            
            # Configure advanced search
            if not self.configure_advanced_search(driver, wait, ticker):
                return [], True
            
            print(f"Collecting posts for {ticker}...")
            time.sleep(1)  # Reduced from 3 to 1
            posts_data = []
            
            try:
                last_height = driver.execute_script("return document.body.scrollHeight")
                consecutive_no_new_content = 0
                max_scroll_attempts = 30
                scroll_count = 0
                
                while len(posts_data) < limit and scroll_count < max_scroll_attempts:
                    # Single aggressive scroll instead of multiple small ones
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 2);")
                    time.sleep(0.5)  # Reduced from 2 to 0.5
                    
                    # Get all tweets currently visible
                    tweets = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
                    
                    # Track how many posts we had before processing new tweets
                    posts_before = len(posts_data)
                    
                    # Process only new tweets
                    start_idx = len(posts_data)
                    for tweet in tweets[start_idx:]:
                        if len(posts_data) >= limit:
                            break
                            
                        try:
                            # Get display name using the specific path
                            display_name = tweet.find_element(
                                By.CSS_SELECTOR, 
                                'div[data-testid="User-Name"] div.r-1wbh5a2.r-dnmrzs a div span'
                            ).text.strip()
                            
                            # Get handle (the @username)
                            handle = tweet.find_element(
                                By.CSS_SELECTOR,
                                'div[data-testid="User-Name"] div.css-175oi2r.r-1wbh5a2 a'
                            ).get_attribute("href").split('/')[-1]
                            
                            # Get timestamp
                            time_element = tweet.find_element(By.CSS_SELECTOR, 'time')
                            timestamp = time_element.get_attribute('datetime')
                            
                            text_element = tweet.find_element(
                                By.CSS_SELECTOR,
                                '[data-testid="tweetText"]'
                            )
                            post_text = text_element.text.strip()
                            
                            # Get metrics
                            comment_count = self.get_metric(tweet, "reply")
                            like_count = self.get_metric(tweet, "like")
                            view_count = self.get_metric(tweet, "analytics")
                            
                            # Only add if it's a new post
                            post_data = {
                                'ticker': ticker,
                                'display_name': display_name,
                                'handle': handle,
                                'post_text': post_text,
                                'timestamp': timestamp,
                                'comments': comment_count,
                                'likes': like_count,
                                'views': view_count
                            }
                            
                            if not any(p['timestamp'] == timestamp and p['handle'] == handle for p in posts_data):
                                posts_data.append(post_data)
                                print(f"Found post {len(posts_data)}/{limit} by {display_name} (@{handle})")
                        
                        except Exception as e:
                            continue
                    
                    # Check if we found any new posts
                    if len(posts_data) > posts_before:
                        consecutive_no_new_content = 0
                    else:
                        consecutive_no_new_content += 1
                    
                    if consecutive_no_new_content >= 3:
                        print(f"No new content found after {consecutive_no_new_content} attempts")
                        break
                    
                    scroll_count += 1
                
                print(f"Collected {len(posts_data)} posts for {ticker}")
                return posts_data, False
                
            except Exception as e:
                print(f"Error finding tweets: {str(e)}")
                return posts_data, False
                
        except Exception as e:
            print(f"Error searching for ticker {ticker}: {str(e)}")
            return [], True

    def get_metric(self, tweet, metric_type):
        """Helper method to extract metrics safely"""
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                if metric_type == "analytics":
                    try:
                        # Wait for analytics section to be present
                        analytics_section = WebDriverWait(tweet, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/analytics"]'))
                        )
                        # Then find the view count within that section
                        view_element = analytics_section.find_element(By.CSS_SELECTOR, 'span')
                        value = view_element.text.strip()
                        
                        # Debug print
                        print(f"Found view count: {value}")
                        
                        return self.convert_metric_value(value)
                    except Exception as e:
                        if attempt == max_retries - 1:  # Only print on last attempt
                            print(f"Error getting view count: {str(e)}")
                        time.sleep(retry_delay)
                        continue
                else:
                    # Original logic for comments and likes with wait
                    element = WebDriverWait(tweet, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-testid="{metric_type}"] [dir="ltr"]'))
                    )
                    value = element.text.strip()
                    return self.convert_metric_value(value)
                
            except Exception as e:
                if attempt == max_retries - 1:  # Only print on last attempt
                    print(f"Error in get_metric: {str(e)}")
                time.sleep(retry_delay)
                continue
                
        return 0  # Return 0 if all attempts fail

    def convert_metric_value(self, value):
        """Helper method to convert metric strings to numbers"""
        if not value:
            return 0
        try:
            # Remove any commas and spaces
            value = value.replace(',', '').strip()
            # Convert K/M to numbers
            if 'K' in value:
                return int(float(value.replace('K', '')) * 1000)
            elif 'M' in value:
                return int(float(value.replace('M', '')) * 1000000)
            return int(value)
        except:
            return 0

    def get_comments(self, tweet):
        """Helper method to extract comment count safely"""
        try:
            comment_element = tweet.find_element(By.CSS_SELECTOR, '[data-testid="reply"] [dir="ltr"]')
            value = comment_element.text.strip()
            if not value:
                return 0
            # Convert K/M to numbers
            if 'K' in value:
                return int(float(value.replace('K', '')) * 1000)
            elif 'M' in value:
                return int(float(value.replace('M', '')) * 1000000)
            return int(value)
        except:
            return 0

    def save_posts_with_retry(self, posts, output_file, all_posts_lock):
        """Save posts to CSV with retry logic and create a readable version"""
        max_retries = 3
        retry_count = 0
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Create timestamped output file with consistent naming
        self.current_output_file = f'x_posts_{timestamp}.csv'  # Changed from multi_x_posts to x_posts
        readable_file = f'x_posts_{timestamp}_readable.txt'
        
        while retry_count < max_retries:
            try:
                with all_posts_lock:
                    df = pd.DataFrame(posts)
                    df = df[['ticker', 'display_name', 'handle', 'post_text', 'timestamp', 'comments', 'likes', 'views']]
                    
                    # Save standard CSV
                    df.to_csv(self.current_output_file, index=False)
                    print(f"\n✅ Data saved to: {self.current_output_file}")
                    
                    # Save readable version
                    with open(readable_file, 'w', encoding='utf-8') as f:
                        for _, row in df.iterrows():
                            f.write(f"Ticker: {row['ticker']}\n")
                            f.write(f"Name: {row['display_name']}\n")
                            f.write(f"Handle: @{row['handle']}\n")
                            f.write(f"Post: {row['post_text']}\n")
                            f.write(f"Time: {row['timestamp']}\n")
                            f.write(f"Comments: {row['comments']}\n")
                            f.write(f"Likes: {row['likes']}\n")
                            f.write(f"Views: {row['views']}\n")
                            f.write("-" * 50 + "\n\n")
                    
                    # After saving, analyze historical data
                    self.analyze_historical_data(df, timestamp)
                    return True
                    
            except Exception as e:
                print(f"Error saving posts (attempt {retry_count + 1}): {str(e)}")
                retry_count += 1
                time.sleep(1)
        
        return False

    def analyze_historical_data(self, current_df, current_timestamp):
        """Analyze historical data to track changes in metrics"""
        try:
            # Get all historical X post files
            historical_files = sorted(glob.glob('x_posts_*.csv'))
            
            if len(historical_files) <= 1:
                print("\nNo historical data available for comparison yet")
                return
            
            print("\n=== Historical Data Analysis ===")
            
            # Create a dictionary to track metrics by ticker
            ticker_metrics = {}
            
            # Process all historical files
            for file in historical_files:
                timestamp = file.split('_')[1].split('.')[0]
                df = pd.read_csv(file)
                
                for ticker in df['ticker'].unique():
                    if ticker not in ticker_metrics:
                        ticker_metrics[ticker] = []
                    
                    ticker_data = df[df['ticker'] == ticker]
                    avg_likes = ticker_data['likes'].mean()
                    avg_comments = ticker_data['comments'].mean()
                    avg_views = ticker_data['views'].mean()
                    mention_count = len(ticker_data)
                    
                    ticker_metrics[ticker].append({
                        'timestamp': timestamp,
                        'avg_likes': avg_likes,
                        'avg_comments': avg_comments,
                        'avg_views': avg_views,
                        'mentions': mention_count
                    })
            
            # Compare metrics and generate insights
            self.generate_insights(ticker_metrics, current_timestamp)
            
        except Exception as e:
            print(f"Error analyzing historical data: {str(e)}")
            traceback.print_exc()

    def generate_insights(self, ticker_metrics, current_timestamp):
        """Generate insights from historical data"""
        print("\n=== Ticker Performance Insights ===")
        
        for ticker, history in ticker_metrics.items():
            if len(history) > 1:
                latest = history[-1]
                previous = history[-2]
                
                print(f"\nTicker: {ticker}")
                print(f"Time period: {previous['timestamp']} -> {latest['timestamp']}")
                
                # Calculate percentage changes
                metrics = {
                    'Average Likes': ('avg_likes', latest['avg_likes'], previous['avg_likes']),
                    'Average Comments': ('avg_comments', latest['avg_comments'], previous['avg_comments']),
                    'Average Views': ('avg_views', latest['avg_views'], previous['avg_views']),
                    'Mention Count': ('mentions', latest['mentions'], previous['mentions'])
                }
                
                for metric_name, (metric_key, new_val, old_val) in metrics.items():
                    if old_val > 0:  # Avoid division by zero
                        pct_change = ((new_val - old_val) / old_val) * 100
                        direction = "↑" if pct_change > 0 else "↓"
                        print(f"{metric_name}: {direction} {abs(pct_change):.1f}% ({old_val:.0f} -> {new_val:.0f})")
                
                # Generate visualization for this ticker
                self.visualize_ticker_metrics(ticker, history)

    def visualize_ticker_metrics(self, ticker, history):
        """Create visualizations for ticker metrics over time"""
        try:
            # Check if we're in the main thread
            if not threading.current_thread() is threading.main_thread():
                print(f"\nSkipping visualization for {ticker} - not in main thread")
                return
                
            timestamps = [h['timestamp'] for h in history]
            metrics = {
                'Average Likes': [h['avg_likes'] for h in history],
                'Average Comments': [h['avg_comments'] for h in history],
                'Average Views': [h['avg_views'] for h in history],
                'Mentions': [h['mentions'] for h in history]
            }
            
            # Use Agg backend which doesn't require GUI
            import matplotlib
            matplotlib.use('Agg')
            
            plt.figure(figsize=(15, 10))
            
            for i, (metric_name, values) in enumerate(metrics.items(), 1):
                plt.subplot(2, 2, i)
                plt.plot(timestamps, values, marker='o')
                plt.title(f'{ticker} - {metric_name}')
                plt.xticks(rotation=45)
                plt.grid(True)
            
            plt.tight_layout()
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            plt.savefig(f'ticker_metrics_{ticker}_{timestamp}.png')
            plt.close()
            
            print(f"\nVisualization saved as: ticker_metrics_{ticker}_{timestamp}.png")
            
        except Exception as e:
            print(f"Error creating visualization for {ticker}: {str(e)}")
            traceback.print_exc()

    def scrape_account_tickers(self, account_index, account_tickers, output_file, all_posts_lock, rate_limit_event):
        """Modified to get usernames from 5 posts per search"""
        print(f"\nAccount {account_index + 1} starting post collection...")
        
        all_posts = []
        for i, ticker in enumerate(account_tickers, 1):
            try:
                print(f"\nAccount {account_index + 1} searching {i}/{len(account_tickers)}: {ticker}")
                posts, rate_limited = self.search_ticker(
                    self.drivers[account_index],
                    self.waits[account_index],
                    ticker,
                    limit=5
                )
                
                if posts:
                    all_posts.extend(posts)
                    self.save_posts_with_retry(posts, output_file, all_posts_lock)
                    
                time.sleep(0.5)  # Keep the reduced delay
                
            except Exception as e:
                print(f"Error processing {ticker} on account {account_index + 1}: {str(e)}")
                continue
                
        print(f"\nAccount {account_index + 1} completed post collection")
        return

    def scrape_all_tickers(self, input_file, output_file):
        """Scrape all tickers using multiple accounts in parallel"""
        # Create timestamped output file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.current_output_file = f'x_posts_{timestamp}.csv'  # Store as class variable
        print(f"\nData will be saved to: {self.current_output_file}")
        
        # Find most recent bullx_tickers file
        bullx_files = sorted(glob.glob('bullx_tickers_*.csv'))
        if not bullx_files:
            print("\n❌ Error: No BullX ticker files found!")
            return
            
        latest_bullx_file = max(bullx_files, key=os.path.getctime)
        print(f"\nUsing most recent BullX data: {latest_bullx_file}")
        
        # Get date range before starting
        self.get_date_range()
        
        # Read all tickers and show the raw list
        try:
            raw_tickers = pd.read_csv(latest_bullx_file)['Ticker'].tolist()
            print(f"\nRaw tickers from file ({len(raw_tickers)}):")
            print(', '.join(raw_tickers))
            
            # Remove duplicates while preserving order
            tickers = list(dict.fromkeys(raw_tickers))
            
            print(f"\nUnique tickers after deduplication ({len(tickers)}):")
            print(', '.join(tickers))
            
            # Ensure we have enough tickers for all accounts
            if len(tickers) < self.num_accounts:
                active_accounts = len(tickers)
                print(f"\nReducing active accounts to {active_accounts} due to limited tickers")
            else:
                active_accounts = self.num_accounts
            
            # Distribute tickers evenly among active accounts
            account_tickers = []
            tickers_per_account = len(tickers) // active_accounts
            remainder = len(tickers) % active_accounts
            
            start = 0
            for i in range(active_accounts):
                # Add one extra ticker to some accounts if there's a remainder
                extra = 1 if i < remainder else 0
                end = start + tickers_per_account + extra
                account_tickers.append(tickers[start:end])
                start = end
            
            print("\nDetailed ticker distribution:")
            total_assigned = 0
            for i, ticks in enumerate(account_tickers):
                print(f"\nAccount {i+1} ({len(ticks)} tickers):")
                for j, ticker in enumerate(ticks, 1):
                    print(f"  {j}. {ticker}")
                total_assigned += len(ticks)
            
            print(f"\nTotal tickers assigned: {total_assigned}")
            
            # Create rate limit event and synchronization event
            rate_limit_event = threading.Event()
            start_event = threading.Event()
            
            # Create threads only for accounts with tickers
            threads = []
            for i in range(len(account_tickers)):
                thread = threading.Thread(
                    target=self.scrape_account_tickers_sync,
                    args=(i, account_tickers[i], output_file, self.all_posts_lock, rate_limit_event, start_event),
                    daemon=True
                )
                threads.append(thread)
            
            # Start all threads (they'll wait for the start event)
            for thread in threads:
                thread.start()
            
            # Small pause to ensure all threads are ready
            time.sleep(1)
            
            # Signal all threads to start simultaneously
            start_event.set()
            
            try:
                # Wait for all threads to complete
                for thread in threads:
                    thread.join()
                print(f"\n✅ Scraping complete! Data saved to: {self.current_output_file}")
                
                # Merge with BullX data
                print("\nMerging with BullX ticker data...")
                self.merge_with_bullx_data(self.current_output_file)
                
            except KeyboardInterrupt:
                print("\nStopping scraper...")
                return
                
        except Exception as e:
            print(f"Error processing tickers: {str(e)}")
            traceback.print_exc()

    def scrape_account_tickers_sync(self, account_index, account_tickers, output_file, all_posts_lock, rate_limit_event, start_event):
        """Modified version to scrape 20 posts per ticker"""
        try:
            # Wait for start signal
            start_event.wait()
            
            print(f"\nAccount {account_index + 1} starting post collection...")
            
            all_posts = []
            for i, ticker in enumerate(account_tickers, 1):
                try:
                    print(f"\nAccount {account_index + 1} searching {i}/{len(account_tickers)}: {ticker}")
                    posts_data, rate_limited = self.search_ticker(
                        self.drivers[account_index],
                        self.waits[account_index],
                        ticker,
                        limit=20  # Changed from 5 to 20 posts per ticker
                    )
                    
                    if posts_data:
                        all_posts.extend(posts_data)
                        self.save_posts_with_retry(posts_data, output_file, all_posts_lock)
                        
                    time.sleep(1)  # Slightly increased delay between tickers
                    
                except Exception as e:
                    print(f"Error processing {ticker} on account {account_index + 1}: {str(e)}")
                    continue
                    
            print(f"\nAccount {account_index + 1} completed post collection")
            return
            
        except Exception as e:
            print(f"Error in scrape_account_tickers_sync for account {account_index + 1}: {str(e)}")
            return

    def close(self):
        """Close all browser instances"""
        for driver in self.drivers:
            driver.quit()

    def auto_login(self, driver, wait, username, password):
        """Automated login process for X"""
        try:
            # Navigate to login page
            print(f"\nStarting login process for {username}...")
            driver.get("https://twitter.com/i/flow/login")
            time.sleep(3)  # Give page time to load
            
            # Enter username
            print("Entering username...")
            username_input = wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, 'input[autocomplete="username"]'
            )))
            username_input.clear()
            username_input.send_keys(username)
            time.sleep(1)
            
            # Click the Next button
            next_button = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//span[text()='Next']"
            )))
            next_button.click()
            time.sleep(2)
            
            # Enter password
            print("Entering password...")
            password_input = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, 'input[name="password"]'
            )))
            password_input.clear()
            password_input.send_keys(password)
            time.sleep(1)
            
            # Click the Login button
            login_button = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//span[text()='Log in']"
            )))
            login_button.click()
            time.sleep(3)
            
            # Verify login success
            try:
                wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, '[data-testid="primaryColumn"]'
                )))
                print(f"✅ Successfully logged in as {username}")
                
                # Zoom out the page
                print("Zooming out page to fit more content...")
                self.zoom_page(driver)
                time.sleep(1)
                
                # Minimize page elements
                print("Minimizing page elements...")
                self.minimize_page_elements(driver)
                time.sleep(1)
                
                return True
            except Exception as e:
                print(f"❌ Could not verify login success: {str(e)}")
                return False
                
        except Exception as e:
            print(f"❌ Error during login: {str(e)}")
            traceback.print_exc()
            return False

    def zoom_page(self, driver, zoom_level=25):
        """Zoom page to specified level using keyboard shortcuts"""
        actions = ActionChains(driver)
        # Reset zoom first (Cmd/Ctrl + 0)
        actions.key_down(Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL)
        actions.send_keys('0')
        actions.key_up(Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL)
        actions.perform()
        
        # Calculate how many times to zoom out
        current = 100
        while current > zoom_level:
            actions = ActionChains(driver)
            actions.key_down(Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL)
            actions.send_keys('-')
            actions.key_up(Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL)
            actions.perform()
            time.sleep(0.1)
            current = current * 0.8  # Approximate zoom reduction per keystroke

    def minimize_page_elements(self, driver):
        """Minimize page elements to fit more content"""
        compact_styles = """
            img, video, [data-testid="tweetPhoto"], 
            [data-testid="videoPlayer"], 
            [data-testid="tweetMediaContainer"] { 
                display: none !important; 
            }
            
            [data-testid="tweet"] {
                padding: 4px !important;
                margin: 2px 0 !important;
                min-height: auto !important;
                border-bottom: 1px solid #ccc !important;
            }
            
            [data-testid="tweetText"] {
                font-size: 12px !important;
                line-height: 1.2 !important;
            }
            
            [role="group"] {
                padding: 2px !important;
                font-size: 11px !important;
            }
        """
        
        try:
            driver.execute_script(f"""
                var style = document.createElement('style');
                style.type = 'text/css';
                style.innerHTML = `{compact_styles}`;
                document.head.appendChild(style);
            """)
            print("Page elements minimized successfully")
        except Exception as e:
            print(f"Error minimizing page elements: {e}")

    def merge_with_bullx_data(self, scraped_file=None):
        """Merge X scraping data with BullX ticker data"""
        try:
            if scraped_file is None:
                # Find most recent x_posts file
                x_files = sorted(glob.glob('x_posts_*.csv'))
                if not x_files:
                    print("\n❌ No X posts files found!")
                    return
                scraped_file = max(x_files, key=os.path.getctime)
            
            print(f"\nAttempting to merge file: {scraped_file}")
            
            if not os.path.exists(scraped_file):
                print(f"\n❌ Error: Scraped file not found")
                print("\nAvailable CSV files:")
                for file in sorted(glob.glob("*.csv")):
                    print(f"- {file}")
                return
            
            # Read the scraped data
            scraped_df = pd.read_csv(scraped_file)
            print(f"Successfully read scraped file with {len(scraped_df)} rows")
            
            # Find and read the most recent BullX data
            bullx_files = sorted(glob.glob('bullx_tickers_*.csv'))
            if not bullx_files:
                print("\n❌ No BullX ticker files found!")
                return
                
            latest_bullx_file = max(bullx_files, key=os.path.getctime)
            bullx_df = pd.read_csv(latest_bullx_file)
            print(f"Successfully read BullX file: {latest_bullx_file}")
            
            # Perform merge operations here
            # ... add your merge logic ...
            
            print("\n✅ Merge completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error merging files: {str(e)}")
            traceback.print_exc()

# Usage
if __name__ == "__main__":
    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"multi_x_posts_{timestamp}.csv"
    
    # Initialize and start scraper
    scraper = MultiXScraper()
    if scraper.start_sessions():
        scraper.scrape_all_tickers('bullx_tickers.csv', output_file)  # Changed from 'x_tickers.bullcsv'
    
    # Clean up
    for driver in scraper.drivers:
        driver.quit()