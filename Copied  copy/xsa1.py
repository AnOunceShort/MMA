import praw
import pandas as pd
from collections import Counter
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import os
import traceback

class XSentimentAnalyzer:
    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        self.ticker_emojis = {
            'MEMESAI': '🐙',
            'UFD': '🦄',
            'FARTCOIN': '💩',
            'SWARMS': '🐝',
            # Add more mappings as needed
        }

    def get_ticker_emoji(self, ticker):
        """Get emoji for a ticker (case insensitive)"""
        return self.ticker_emojis.get(ticker.upper(), '')

    def extract_tickers(self, text):
        """Extract stock tickers from text (in both $TICKER and #TICKER format)"""
        # Find tickers with $ symbol
        dollar_tickers = re.findall(r'\$([A-Za-z]+)', text)
        # Find tickers with # symbol
        hash_tickers = re.findall(r'#([A-Za-z]+)', text)
        # Combine both lists, remove duplicates, and add emojis
        tickers = list(set(dollar_tickers + hash_tickers))
        # Add emojis to tickers
        return [(ticker, self.get_ticker_emoji(ticker)) for ticker in tickers]

    def is_advertisement(self, comment):
        """Check if the comment is an advertisement"""
        try:
            # Try to find the "Ad" label using the specific path
            ad_element = comment.find_element(
                By.CSS_SELECTOR,
                'div.css-175oi2r.r-zl2h9q div.css-175oi2r.r-1kkk96v div.css-146c3p1 span'
            )
            return ad_element.text.lower() == 'ad'
        except:
            return False

    def scrape_comments(self):
        """Scrape all comments from the current X post"""
        comments_data = []
        
        try:
            # Increased initial wait time
            time.sleep(5)
            
            # Ensure we're on the correct window/tab
            self.driver.switch_to.window(self.driver.current_window_handle)
            
            # Wait for the main content to be present
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]')))
            
            # First scroll to bottom to load all comments
            scroll_attempts = 0
            max_scroll_attempts = 30
            
            while scroll_attempts < max_scroll_attempts:
                try:
                    # Get current height
                    last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                    
                    # Scroll down in smaller increments
                    for i in range(1, 5):  # Scroll in 4 steps
                        self.driver.execute_script(
                            f"window.scrollTo(0, document.documentElement.scrollHeight * {i/4});"
                        )
                        time.sleep(1)  # Wait between each small scroll
                    
                    time.sleep(2)
                    
                    # Calculate new height
                    new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                    
                    if new_height == last_height:
                        break
                        
                    scroll_attempts += 1
                    
                except Exception as e:
                    print(f"Scroll error: {str(e)}")
                    break
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Now scroll slowly through the entire thread to collect comments
            total_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            current_position = 0
            step = 500  # Pixels to scroll each time
            
            while current_position < total_height:
                # Scroll to next position
                self.driver.execute_script(f"window.scrollTo(0, {current_position});")
                time.sleep(1)
                
                # Find all visible comments at this position
                visible_comments = self.driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
                print(f"Found {len(visible_comments)} comments at scroll position {current_position}")
                
                current_position += step
            
            # Final scroll to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Get all comments now that everything is loaded
            comments = self.driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
            print(f"\nTotal comments found: {len(comments)}")
            
            # Process each comment
            for comment in comments[1:]:  # Skip the first one as it's usually the main post
                try:
                    # Check if comment is an advertisement
                    if self.is_advertisement(comment):
                        print("Skipping advertisement...")
                        continue
                        
                    # Scroll comment into view
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        comment
                    )
                    time.sleep(0.5)
                    
                    # Wait for comment to be interactive
                    self.wait.until(EC.visibility_of(comment))
                    time.sleep(0.5)  # Small delay between processing each comment
                    
                    # Get username and display name
                    user_info = comment.find_element(
                        By.CSS_SELECTOR,
                        'div[data-testid="User-Name"]'
                    )
                    
                    # Get display name
                    display_name = user_info.find_element(
                        By.CSS_SELECTOR,
                        'span'
                    ).text.strip()
                    
                    # Get username
                    username = user_info.find_element(
                        By.CSS_SELECTOR,
                        'a'
                    ).get_attribute("href").split('/')[-1]
                    
                    # Get comment text
                    try:
                        text_element = comment.find_element(
                            By.CSS_SELECTOR,
                            'div[data-testid="tweetText"]'
                        )
                        comment_text = text_element.text.strip()
                    except:
                        comment_text = ""
                    
                    # Get metrics
                    likes = self.get_metric(comment, "like")
                    replies = self.get_metric(comment, "reply")
                    
                    # Get timestamp
                    try:
                        time_element = comment.find_element(By.CSS_SELECTOR, 'time')
                        timestamp = time_element.get_attribute('datetime')
                    except:
                        timestamp = ""
                    
                    # Extract tickers with emojis
                    tickers_with_emojis = self.extract_tickers(comment_text)
                    
                    comments_data.append({
                        'username': username,
                        'display_name': display_name,
                        'comment': comment_text,
                        'likes': likes,
                        'replies': replies,
                        'timestamp': timestamp,
                        'tickers': [t[0] for t in tickers_with_emojis],  # Just the ticker names
                        'emojis': [t[1] for t in tickers_with_emojis if t[1]]  # Only non-empty emojis
                    })
                    
                    print(f"Processed comment by @{username}")
                    
                except Exception as e:
                    print(f"Error processing comment: {str(e)}")
                    continue
            
            return comments_data
            
        except Exception as e:
            print(f"Error scraping comments: {str(e)}")
            traceback.print_exc()
            return []

    def get_metric(self, tweet, metric_type):
        """Helper method to extract metrics safely"""
        try:
            element = tweet.find_element(
                By.CSS_SELECTOR,
                f'[data-testid="{metric_type}"] [dir="ltr"]'
            )
            value = element.text.strip()
            return self.convert_metric_value(value)
        except:
            return 0

    def convert_metric_value(self, value):
        """Convert metric strings to numbers"""
        if not value:
            return 0
        try:
            value = value.replace(',', '').strip()
            if 'K' in value:
                return int(float(value.replace('K', '')) * 1000)
            elif 'M' in value:
                return int(float(value.replace('M', '')) * 1000000)
            return int(value)
        except:
            return 0

    def analyze_post(self):
        """Analyze the current X post"""
        comments = self.scrape_comments()
        
        if not comments:
            print("No comments found to analyze")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(comments)
        
        # Calculate metrics
        total_comments = len(df)
        
        # Get top commenters by likes
        top_commenters = df.nlargest(5, 'likes')[['display_name', 'username', 'likes', 'comment']]
        
        # Get most mentioned tickers with their emojis
        all_tickers = [(ticker, emoji) 
                      for tickers, emojis in zip(df['tickers'], df['emojis'])
                      for ticker, emoji in zip(tickers, emojis or [''])]
        most_mentioned_tickers = Counter(ticker for ticker, _ in all_tickers).most_common(5)
        
        # Print analysis
        print("\n=== X Post Analysis ===")
        print(f"\nTotal Comments: {total_comments}")
        
        print("\nTop Commenters by Likes:")
        print(top_commenters.to_string())
        
        print("\nMost Mentioned Tickers:")
        for ticker, count in most_mentioned_tickers:
            emoji = next((e for t, e in all_tickers if t == ticker), '')
            print(f"{ticker} {emoji}: {count} mentions")
        
        # Save to CSV
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        df.to_csv(f'x_sentiment_analysis_{timestamp}.csv', index=False)
        print(f"\nFull analysis saved to: x_sentiment_analysis_{timestamp}.csv")

def main():
    print("Starting X Sentiment Analyzer...")
    print("\nBefore starting, please:")
    print("1. Open Terminal and run: '/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222'")
    print("2. In the new Chrome window, navigate to the X post you want to analyze")
    print("3. Make sure the post and its comments are visible")
    
    input("\nPress Enter when you're ready to start analysis...")
    
    try:
        analyzer = XSentimentAnalyzer()
        print("\nConnected to Chrome successfully!")
        print("Starting analysis...")
        analyzer.analyze_post()
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nMake sure Chrome is running with remote debugging enabled.")
        print("Run this command in a new Terminal window:")
        print("'/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222'")

if __name__ == "__main__":
    main() 