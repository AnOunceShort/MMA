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
        try:
            if metric_type == "analytics":
                try:
                    # First find the analytics link/section
                    analytics_section = tweet.find_element(By.CSS_SELECTOR, 'a[href*="/analytics"]')
                    # Then find the view count within that section
                    view_element = analytics_section.find_element(By.CSS_SELECTOR, 'span[data-testid="app-text-transition-container"]')
                    value = view_element.text.strip()
                    
                    # Debug print
                    print(f"Found view count: {value}")
                    
                    return self.convert_metric_value(value)
                except Exception as e:
                    print(f"Error getting view count: {str(e)}")
                    return 0
            else:
                # Original logic for comments and likes
                element = tweet.find_element(By.CSS_SELECTOR, f'[data-testid="{metric_type}"] [dir="ltr"]')
                value = element.text.strip()
                return self.convert_metric_value(value)
            
        except Exception as e:
            print(f"Error in get_metric: {str(e)}")
            return 0

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
        
        while retry_count < max_retries:
            try:
                with all_posts_lock:
                    df = pd.DataFrame(posts)
                    # Updated column order to include timestamp
                    df = df[['ticker', 'display_name', 'handle', 'post_text', 'timestamp', 'comments', 'likes', 'views']]
                    
                    # Save standard CSV
                    df.to_csv(output_file, mode='a', header=not os.path.exists(output_file), index=False)
                    
                    # Save readable version
                    readable_file = output_file.replace('.csv', '_readable.txt')
                    with open(readable_file, 'a', encoding='utf-8') as f:
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
                    
                    return True
            except Exception as e:
                print(f"Error saving posts (attempt {retry_count + 1}): {str(e)}")
                retry_count += 1
                time.sleep(1)
        
        print("Failed to save posts after all retries")
        return False

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
        print(f"\nData will be saved to: {output_file}")
        
        # Get date range before starting
        self.get_date_range()
        
        # Read tickers - limit to first 6 tickers
        tickers = pd.read_csv(input_file)['Ticker'].tolist()[:6]  # Added back the [:6] limit
        print(f"\n🎯 Will scrape these tickers: {', '.join(tickers)}")
        
        # Split tickers evenly among accounts
        tickers_per_account = len(tickers) // self.num_accounts
        account_tickers = [
            tickers[i:i + tickers_per_account] 
            for i in range(0, len(tickers), tickers_per_account)
        ]
        
        # Create rate limit event
        rate_limit_event = threading.Event()
        
        # Create synchronization event
        start_event = threading.Event()
        
        # Create all threads
        threads = []
        for i in range(self.num_accounts):
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
            print(f"\n✅ Scraping complete! Data saved to: {output_file}")
            
        except KeyboardInterrupt:
            print("\nStopping scraper...")
            return

    def scrape_account_tickers_sync(self, account_index, account_tickers, output_file, all_posts_lock, rate_limit_event, start_event):
        """Modified version with synchronization - now including post text"""
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
                    limit=5
                )
                
                if posts_data:
                    all_posts.extend(posts_data)
                    self.save_posts_with_retry(posts_data, output_file, all_posts_lock)
                    
                time.sleep(0.5)  # Keep the reduced delay
                
            except Exception as e:
                print(f"Error processing {ticker} on account {account_index + 1}: {str(e)}")
                continue
                
        print(f"\nAccount {account_index + 1} completed post collection")
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

# Usage
if __name__ == "__main__":
    # Add timestamp to CSV filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'multi_x_posts_{timestamp}.csv'
    
    scraper = MultiXScraper(num_accounts=3)
    scraper.start_sessions()
    scraper.scrape_all_tickers('bullx_tickers.csv', output_file)
    scraper.close()