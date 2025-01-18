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
            {"username": "flowinggriddd", "password": "Nosignal777"}
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
        for i, ticker in enumerate(tickers):
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

    def search_ticker(self, driver, wait, ticker, limit=50):
        """Search for ticker using specified driver"""
        results = []
        try:
            print(f"\nSearching for {ticker} posts (limit: {limit})...")
            
            # Configure advanced search directly
            if not self.configure_advanced_search(driver, wait, ticker):
                return [], True
            
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 5
            
            while len(results) < limit:
                tweets = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[data-testid="tweet"]')))
                
                for tweet in tweets:
                    try:
                        text = tweet.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]').text
                        username = tweet.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"]').text
                        time_element = tweet.find_element(By.TAG_NAME, "time")
                        timestamp = time_element.get_attribute("datetime")
                        
                        # Get metrics with different selectors
                        engagement_data = {
                            'replies': 0,
                            'retweets': 0,
                            'likes': 0,
                            'views': 0
                        }
                        
                        # Try to get metrics using data-testid attributes
                        metrics_map = {
                            'reply': 'replies',
                            'retweet': 'retweets',
                            'like': 'likes'
                        }
                        
                        for action, metric in metrics_map.items():
                            try:
                                selector = f'[data-testid="{action}"]'
                                metric_element = tweet.find_element(By.CSS_SELECTOR, selector)
                                number_element = metric_element.find_element(By.CSS_SELECTOR, '[dir="ltr"]')
                                value_text = number_element.text.strip()
                                
                                if value_text:
                                    if 'K' in value_text:
                                        value = float(value_text.replace('K', '')) * 1000
                                    elif 'M' in value_text:
                                        value = float(value_text.replace('M', '')) * 1000000
                                    else:
                                        value = float(value_text)
                                    
                                    engagement_data[metric] = int(value)
                                    print(f"Found {metric}: {value}")
                            except NoSuchElementException:
                                continue
                            except Exception as e:
                                print(f"Unexpected error getting {metric}: {str(e)}")
                        
                        # Try to get views
                        try:
                            view_element = tweet.find_element(By.CSS_SELECTOR, '[data-testid="analytics"]')
                            value_text = view_element.find_element(By.CSS_SELECTOR, '[dir="ltr"]').text.strip()
                            if value_text:
                                if 'K' in value_text:
                                    value = float(value_text.replace('K', '')) * 1000
                                elif 'M' in value_text:
                                    value = float(value_text.replace('M', '')) * 1000000
                                else:
                                    value = float(value_text)
                                engagement_data['views'] = int(value)
                                print(f"Found views: {value}")
                        except NoSuchElementException:
                            pass
                        except Exception as e:
                            print(f"Unexpected error getting views: {str(e)}")

                        results.append({
                            'ticker': ticker,
                            'text': text,
                            'username': username,
                            'timestamp': timestamp,
                            'likes': engagement_data['likes'],
                            'retweets': engagement_data['retweets'],
                            'replies': engagement_data['replies'],
                            'views': engagement_data['views']
                        })
                        
                        print(f"Successfully added post {len(results)}/{limit} for {ticker}")
                        print(f"Engagement: 👍 {engagement_data['likes']}, 🔁 {engagement_data['retweets']}, 💬 {engagement_data['replies']}, 👀 {engagement_data['views']}")

                        if len(results) >= limit:
                            break
                            
                    except Exception as e:
                        print(f"Error processing tweet: {str(e)}")
                        continue
                
                if len(results) >= limit:
                    break
                    
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                current_height = driver.execute_script("return document.body.scrollHeight")
                if current_height == last_height:
                    scroll_attempts += 1
                    if scroll_attempts >= max_scroll_attempts:
                        break
                else:
                    scroll_attempts = 0
                    last_height = current_height
                    
            print(f"Collected {len(results)} posts for {ticker}")
            return results, False
            
        except Exception as e:
            print(f"Error searching for ticker {ticker}: {str(e)}")
            return [], True

    def get_metric(self, tweet, metric_type):
        """Helper method to extract metrics safely"""
        try:
            element = tweet.find_element(By.CSS_SELECTOR, f'[data-testid="{metric_type}"] [dir="ltr"]')
            value = element.text.strip()
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

    def get_views(self, tweet):
        """Helper method to extract view count safely"""
        try:
            view_element = tweet.find_element(By.CSS_SELECTOR, '[data-testid="app-text-transition-container"] span')
            value = view_element.text.strip()
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
        """Save posts to CSV with retry logic"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                with all_posts_lock:
                    df = pd.DataFrame(posts)
                    df.to_csv(output_file, mode='a', header=not os.path.exists(output_file), index=False)
                    return True
            except Exception as e:
                print(f"Error saving posts (attempt {retry_count + 1}): {str(e)}")
                retry_count += 1
                time.sleep(1)
        
        print("Failed to save posts after all retries")
        return False

    def scrape_account_tickers(self, account_index, account_tickers, output_file, all_posts_lock, rate_limit_event):
        """Handle scraping for a single account"""
        ticker_count = 0
        
        for i, ticker in enumerate(account_tickers, 1):
            try:
                print(f"\nAccount {account_index + 1} processing ticker {i}/{len(account_tickers)}: {ticker}")
                posts, rate_limited = self.search_ticker(
                    self.drivers[account_index],
                    self.waits[account_index],
                    ticker,
                    limit=50
                )
                
                # Save with retry logic
                if posts:
                    self.save_posts_with_retry(posts, output_file, self.all_posts_lock)
                
                ticker_count += 1
                
                if ticker_count >= 10 or rate_limited:
                    print(f"\nAccount {account_index + 1} reached limit after {ticker_count} tickers")
                    rate_limit_event.set()
                    break
                    
                time.sleep(2)  # Add delay between tickers
                
            except Exception as e:
                print(f"Error processing ticker {ticker} on account {account_index + 1}: {str(e)}")
                continue

    def scrape_all_tickers(self, input_file, output_file):
        """Scrape all tickers using multiple accounts"""
        # Get date range before starting
        self.get_date_range()
        
        # Read tickers
        tickers = pd.read_csv(input_file)['Ticker'].tolist()
        
        # Split tickers among accounts
        tickers_per_account = len(tickers) // self.num_accounts
        account_tickers = [
            tickers[i:i + tickers_per_account] 
            for i in range(0, len(tickers), tickers_per_account)
        ]
        
        # Create rate limit event
        rate_limit_event = threading.Event()
        
        # Create and start threads
        threads = []
        for i in range(self.num_accounts):
            thread = threading.Thread(
                target=self.scrape_account_tickers,
                args=(i, account_tickers[i], output_file, self.all_posts_lock, rate_limit_event)
            )
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()

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

# Usage
if __name__ == "__main__":
    # Add timestamp to CSV filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'multi_x_posts_{timestamp}.csv'
    
    scraper = MultiXScraper(num_accounts=3)
    scraper.start_sessions()
    scraper.scrape_all_tickers('bullx_tickers.csv', output_file)
    scraper.close()