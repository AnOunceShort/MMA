from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import csv
import random
from selenium.webdriver.common.action_chains import ActionChains

class XScraper:
    def __init__(self):
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 10)
        
    def start_session(self):
        """Open X homepage and wait for manual login"""
        self.driver.get("https://x.com/home")
        input("Please log in manually and press Enter when ready...")
        print("Starting scraping process...")
        
    def load_tickers(self, csv_file):
        """Load tickers from CSV file"""
        tickers = []
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header row if it exists
            for row in reader:
                if row and row[0].strip():  # Only add non-empty values
                    tickers.append(row[0].strip())
        return tickers
    
    def search_ticker(self, ticker):
        """Search for a ticker and scrape posts"""
        try:
            # Go back to home page to reset everything
            self.driver.get("https://x.com/home")
            time.sleep(2)
            
            # Find and clear search box
            search_box = self.driver.find_element(By.CSS_SELECTOR, 'input[data-testid="SearchBox_Search_Input"]')
            
            # Clear using multiple methods
            search_box.clear()
            search_box.send_keys(Keys.CONTROL + "a")
            search_box.send_keys(Keys.DELETE)
            time.sleep(1)
            
            # Enter new search
            search_box.send_keys(ticker)
            search_box.send_keys(Keys.RETURN)
            time.sleep(2)
            
            # Zoom out to see more posts
            actions = ActionChains(self.driver)
            for _ in range(5):
                actions.key_down(Keys.CONTROL).send_keys('-').key_up(Keys.CONTROL).perform()
                time.sleep(0.5)
            
            posts = []
            last_height = 0
            consecutive_no_new_posts = 0
            max_no_new_posts = 3
            
            while True:
                # Get current articles
                articles = self.driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
                initial_post_count = len(posts)
                
                # Process all visible articles
                for article in articles:
                    try:
                        # Extract post text
                        try:
                            text_element = article.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                            text = text_element.text if text_element else "No text content"
                        except:
                            text = "No text content"
                        
                        # Extract username
                        try:
                            username_element = article.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"]')
                            username = username_element.text.split('\n')[0] if username_element else "Unknown user"
                        except:
                            username = "Unknown user"
                        
                        # Extract view count
                        try:
                            analytics_group = article.find_element(By.CSS_SELECTOR, '[data-testid="tweet"] [role="group"]')
                            all_spans = analytics_group.find_elements(By.TAG_NAME, 'span')
                            
                            views = "N/A"
                            for span in all_spans:
                                text_content = span.get_attribute('innerText')
                                if text_content and ('K' in text_content or 'M' in text_content or 'views' in text_content.lower()):
                                    views = text_content
                                    print(f"Debug - Found analytics text: {text_content}")
                                    break
                        except:
                            views = "N/A"
                                
                        # Extract timestamp
                        try:
                            time_element = article.find_element(By.CSS_SELECTOR, 'time')
                            timestamp = time_element.get_attribute('datetime')
                        except:
                            timestamp = None
                        
                        post_data = {
                            'ticker': ticker,
                            'username': username,
                            'text': text,
                            'views': views,
                            'timestamp': timestamp,
                            'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        # Check if we already have this post
                        if not any(p['text'] == post_data['text'] and p['username'] == post_data['username'] for p in posts):
                            posts.append(post_data)
                            print(f"Found post {len(posts)} for {ticker} by {username}")
                            
                    except Exception as e:
                        print(f"Error processing individual post: {str(e)}")
                        continue
                
                # Check if we got any new posts
                if len(posts) == initial_post_count:
                    consecutive_no_new_posts += 1
                else:
                    consecutive_no_new_posts = 0
                
                if consecutive_no_new_posts >= max_no_new_posts:
                    print(f"No new posts found after {max_no_new_posts} attempts. Stopping search.")
                    break
                
                # Scroll and wait for new content to load
                last_height = self.driver.execute_script("return document.body.scrollHeight")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(4)  # Increased wait time after scroll
                
                # Check if scroll was successful
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    consecutive_no_new_posts += 1
                
            return posts
            
        except Exception as e:
            print(f"Error searching for ticker {ticker}: {str(e)}")
            return []
    
    def scrape_all_tickers(self, csv_file, output_file):
        """Main function to scrape all tickers"""
        tickers = self.load_tickers(csv_file)[:2]  # Only take first 2 tickers
        all_posts = []
        
        for i, ticker in enumerate(tickers, 1):
            print(f"\nProcessing ticker {i}/2: {ticker}")
            posts = self.search_ticker(ticker)
            all_posts.extend(posts)
            
            # Save progress after each ticker
            df = pd.DataFrame(all_posts)
            df.to_csv(output_file, index=False)
            print(f"Progress saved: {len(all_posts)} total posts in {output_file}")
            
            # Longer delay between tickers
            if i < len(tickers):
                delay = random.uniform(5, 10)
                print(f"Waiting {delay:.1f} seconds before next ticker...")
                time.sleep(delay)
        
        print(f"\nScraping completed! Total posts collected: {len(all_posts)}")
        
    def close(self):
        self.driver.quit()

# Usage
if __name__ == "__main__":
    scraper = XScraper()
    scraper.start_session()  # Opens X and waits for manual login
    scraper.scrape_all_tickers('bullx_tickers.csv', 'x_posts.csv')
    scraper.close()