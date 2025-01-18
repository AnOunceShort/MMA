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
import re
from datetime import datetime
from selenium.common.exceptions import NoSuchElementException
from transformers import pipeline
import torch

class XScraper:
    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--start-maximized')
        self.driver = None
        self.wait = None
    
    def start_session(self):
        self.driver = webdriver.Chrome(options=self.options)
        self.wait = WebDriverWait(self.driver, 10)
        self.driver.get('https://twitter.com/home')
        input("Please log in and press Enter to continue...")
    
    def minimize_page_elements(self):
        """Minimize page elements to fit more content"""
        compact_styles = """
            // Hide images, videos, and unnecessary elements
            img, video, [data-testid="tweetPhoto"], 
            [data-testid="videoPlayer"], 
            [data-testid="tweetMediaContainer"] { 
                display: none !important; 
            }
            
            // Reduce padding and margins
            [data-testid="tweet"] {
                padding: 4px !important;
                margin: 2px 0 !important;
                min-height: auto !important;
                border-bottom: 1px solid #ccc !important;
            }
            
            // Reduce text size
            [data-testid="tweetText"] {
                font-size: 12px !important;
                line-height: 1.2 !important;
            }
            
            // Compact engagement metrics
            [role="group"] {
                padding: 2px !important;
                font-size: 11px !important;
            }
        """
        
        try:
            self.driver.execute_script(f"""
                var style = document.createElement('style');
                style.type = 'text/css';
                style.innerHTML = `{compact_styles}`;
                document.head.appendChild(style);
            """)
            
            # Force layout recalculation
            self.driver.execute_script("""
                document.body.style.zoom = '0.8';
            """)
            
            print("Page elements minimized successfully")
        except Exception as e:
            print(f"Error minimizing page elements: {e}")

    def search_ticker(self, ticker, limit=50):
        """Search for ticker and collect posts"""
        results = []
        
        try:
            search_url = f"https://twitter.com/search?q={ticker}&src=typed_query&f=top"
            self.driver.get(search_url)
            time.sleep(random.uniform(2, 4))
            
            # Apply compact layout
            self.minimize_page_elements()
            time.sleep(1)  # Let styles apply
            
            # Random delay before search
            time.sleep(random.uniform(2, 4))
            
            # Initial wait with random component
            time.sleep(random.uniform(3, 5))
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 5
            duplicate_count = 0
            duplicate_threshold = 10
            seen_tweets = set()
            
            while len(results) < limit:
                # Random small scrolls instead of full page
                scroll_amount = random.randint(300, 700)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(1, 2))  # Random delay between scrolls
                
                # Every few scrolls, go back up slightly
                if random.random() < 0.2:  # 20% chance
                    self.driver.execute_script(f"window.scrollBy(0, -{random.randint(100, 300)});")
                    time.sleep(random.uniform(0.5, 1))
                
                # Get current scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                # Get all tweet articles on the page
                articles = self.driver.find_elements(By.CSS_SELECTOR, 'article')
                print(f"Found {len(articles)} potential tweets on page")
                
                for article in articles:
                    try:
                        # Get author and tweet text
                        author = article.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"]').text.split('\n')[0]
                        tweet_text = article.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]').text
                        
                        # Create a unique identifier for the tweet
                        tweet_id = f"{author}:{tweet_text[:50]}"
                        
                        if tweet_id in seen_tweets:
                            print(f"Duplicate tweet found - continuing to scroll...")
                            duplicate_count += 1
                            continue
                        
                        seen_tweets.add(tweet_id)
                        duplicate_count = 0  # Reset duplicate counter when new tweet found
                        
                        # Get metrics with different selectors
                        engagement_data = {
                            'replies': 0,
                            'reposts': 0,
                            'likes': 0,
                            'views': 0
                        }
                        
                        # Try to get metrics using data-testid attributes
                        metrics_map = {
                            'reply': 'replies',
                            'retweet': 'reposts',
                            'like': 'likes'
                        }
                        
                        for action, metric in metrics_map.items():
                            try:
                                selector = f'[data-testid="{action}"]'
                                metric_element = article.find_element(By.CSS_SELECTOR, selector)
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
                        
                        # Try to get views separately (since they're not always available)
                        try:
                            # Try multiple selectors for views
                            view_selectors = [
                                '[data-testid="analytics"]',
                                'span[class*="css-1jxf684"][class*="r-bcqeeo"]',  # New selector based on the class
                                '[aria-label*="View"]'  # Backup selector
                            ]
                            
                            for selector in view_selectors:
                                try:
                                    view_element = article.find_element(By.CSS_SELECTOR, selector)
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
                                        break  # Stop trying other selectors if we found views
                                except NoSuchElementException:
                                    continue
                                except Exception as e:
                                    print(f"Unexpected error getting views with selector {selector}: {str(e)}")
                                    
                        except Exception as e:
                            print(f"Error processing views: {str(e)}")
                        
                        # Add to results if we found any engagement metrics
                        if any(engagement_data.values()):
                            post_data = {
                                'ticker': ticker,
                                'author': author,
                                'text': tweet_text,
                                **engagement_data
                            }
                            results.append(post_data)
                            print(f"Successfully added post {len(results)}/{limit} for {ticker} by {author}")
                            print(f"Engagement: 👍 {engagement_data['likes']}, 🔁 {engagement_data['reposts']}, 💬 {engagement_data['replies']}, 👀 {engagement_data['views']}")
                        else:
                            print("No engagement metrics found - skipping")
                            
                    except Exception as e:
                        print(f"Error processing tweet: {str(e)}")
                        continue
                
                # Scroll down for more content
                print("Scrolling for more tweets...")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)  # Wait for initial scroll
                
                # Check if new content loaded
                current_height = self.driver.execute_script("return document.body.scrollHeight")
                if current_height == last_height:
                    scroll_attempts += 1
                    print(f"No new content loaded. Attempt {scroll_attempts}/{max_scroll_attempts}")
                    time.sleep(2)  # Wait a bit longer
                    
                    if scroll_attempts >= max_scroll_attempts:
                        print("\nReached maximum scroll attempts without new content")
                        print(f"Collected {len(results)} posts for {ticker}")
                        return results
                else:
                    scroll_attempts = 0  # Reset scroll attempts when new content loads
                    last_height = current_height
                    duplicate_count = 0  # Reset duplicate counter on successful scroll
                
                # Check for too many consecutive duplicates
                if duplicate_count >= duplicate_threshold:
                    print(f"\nFound {duplicate_threshold} consecutive duplicates")
                    print(f"Collected {len(results)} posts for {ticker}")
                    return results
                
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            return results  # Return what we have instead of break
        
        print(f"\nReached target of {limit} posts for {ticker}")
        return results
    
    def scrape_all_tickers(self, csv_file, output_file):
        """Main function to scrape all tickers"""
        tickers = self.load_tickers(csv_file)
        all_posts = []
        
        for i, ticker in enumerate(tickers, 1):
            try:
                print(f"\nProcessing ticker {i}/{len(tickers)}: {ticker}")
                posts = self.search_ticker(ticker, limit=50)
                all_posts.extend(posts)
                
                # Save progress after each ticker
                df = pd.DataFrame(all_posts)
                df.to_csv(output_file, index=False)
                print(f"Progress saved: {len(all_posts)} total posts in {output_file}")
                
                # Shorter delay between tickers
                if i < len(tickers):
                    delay = random.uniform(3, 5)
                    print(f"Waiting {delay:.1f} seconds before next ticker...")
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"Error processing ticker {ticker}: {str(e)}")
                continue  # Move to next ticker instead of breaking
        
        print(f"\nScraping completed! Total posts collected: {len(all_posts)}")
        
    def close(self):
        self.driver.quit()

if __name__ == "__main__":
    scraper = XScraper()
    scraper.start_session()
    scraper.scrape_all_tickers('bullx_tickers.csv', 'x_posts.csv')
    scraper.close()