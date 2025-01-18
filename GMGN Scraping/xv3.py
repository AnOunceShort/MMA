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
    
    def search_ticker(self, ticker, limit=50):
        results = []
        seen_tweets = set()
        duplicate_threshold = 3
        duplicate_count = 0
        last_height = 0
        scroll_attempts = 0
        max_scroll_attempts = 3
        
        print(f"\nSearching for {ticker} posts (limit: {limit})...")
        
        # Navigate to search URL
        search_url = f"https://twitter.com/search?q={ticker}&src=typed_query&f=live"
        self.driver.get(search_url)
        time.sleep(5)  # Initial longer wait for search results
        
        while len(results) < limit:
            try:
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
                            view_element = article.find_element(By.CSS_SELECTOR, '[data-testid="analytics"]')
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
                            pass  # Views are not available for all tweets
                        except Exception as e:
                            print(f"Unexpected error getting views: {str(e)}")
                        
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
                break
        
        print(f"\nReached target of {limit} posts for {ticker}")
        return results
    
    def scrape_all_tickers(self, csv_file, output_file):
        """Main function to scrape all tickers"""
        tickers = self.load_tickers(csv_file)[:2]  # Only take first 2 tickers
        all_posts = []
        
        for i, ticker in enumerate(tickers, 1):
            print(f"\nProcessing ticker {i}/{len(tickers)}: {ticker}")
            posts = self.search_ticker(ticker, limit=50)  # Changed max_posts to limit
            all_posts.extend(posts)
            
            # Save progress after each ticker
            df = pd.DataFrame(all_posts)
            df.to_csv(output_file, index=False)
            print(f"Progress saved: {len(all_posts)} total posts in {output_file}")
            
            # Shorter delay between tickers
            if i < len(tickers):
                delay = random.uniform(3, 5)  # Reduced from 5-10 to 3-5 seconds
                print(f"Waiting {delay:.1f} seconds before next ticker...")
                time.sleep(delay)
        
        print(f"\nScraping completed! Total posts collected: {len(all_posts)}")
        
    def close(self):
        self.driver.quit()

class CryptoSentimentAnalyzer:
    def __init__(self):
        # Dictionary of words and their sentiment scores
        self.word_scores = {
            # Positive words
            'bullish': 0.8,
            'moon': 0.7,
            'pump': 0.6,
            'gain': 0.5,
            'up': 0.4,
            'profit': 0.6,
            'buy': 0.3,
            'long': 0.4,
            'lead': 0.5
            'good': 0.5,
            'great': 0.7,
            
            # Negative words
            'bearish': -0.8,
            'dump': -0.6,
            'dip': -0.4,
            'down': -0.4,
            'loss': -0.5,
            'sell': -0.3,
            'short': -0.4,
            'bad': -0.5,
            'crash': -0.8,
            'scam': -0.9,
            
            # Add more words as needed...
        }
    
    def analyze_text(self, text):
        """Analyze sentiment of text and return (score, found_words)"""
        if not isinstance(text, str):
            return 0.0, []
            
        text = text.lower()
        words = text.split()
        found_words = []
        total_score = 0
        
        for word in words:
            if word in self.word_scores:
                found_words.append(word)
                total_score += self.word_scores[word]
        
        # Normalize score to [-1, 1] range
        if found_words:
            final_score = max(min(total_score / len(found_words), 1.0), -1.0)
        else:
            final_score = 0.0
            
        return final_score, found_words

    def analyze_csv(self, csv_file):
        """Analyze sentiment from CSV file"""
        print("\n=== Crypto Sentiment Analysis ===")
        print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 40)
        
        df = pd.read_csv(csv_file)
        results = []
        
        for _, row in df.iterrows():
            sentiment_score, found_words = self.analyze_text(row['text'])  # Unpack the tuple
            result = {
                'ticker': row['ticker'],
                'username': row['author'],
                'text': row['text'],
                'sentiment': sentiment_score,  # Just use the score
                'sentiment_words': found_words,  # Store found words separately if needed
                'engagement_score': self.calculate_engagement(
                    row['likes'],
                    row['reposts'],
                    row['replies'],
                    row['views']
                )
            }
            results.append(result)
        
        # Convert results to DataFrame for analysis
        results_df = pd.DataFrame(results)
        
        # Group by ticker and calculate metrics
        for ticker in results_df['ticker'].unique():
            ticker_data = results_df[results_df['ticker'] == ticker]
            
            print(f"\nTicker: {ticker}")
            print(f"Number of posts: {len(ticker_data)}")
            print(f"Average sentiment: {ticker_data['sentiment'].mean():.2f}")
            print(f"Average engagement: {ticker_data['engagement_score'].mean():.2f}")
            
            # Most influential posts
            print("\nTop 3 Most Influential Posts:")
            top_posts = ticker_data.nlargest(3, 'engagement_score')
            for _, post in top_posts.iterrows():
                print(f"\nUser: {post['username']}")
                print(f"Text: {post['text'][:100]}...")
                print(f"Sentiment: {post['sentiment']:.2f}")
                print(f"Sentiment words: {', '.join(post['sentiment_words'])}")
                print(f"Engagement Score: {post['engagement_score']:.2f}")

    def calculate_engagement(self, likes, reposts, replies, views):
        """Calculate engagement score based on metrics"""
        # Weights for different engagement types
        weights = {
            'likes': 1,
            'reposts': 2,
            'replies': 1.5,
            'views': 0.1
        }
        
        # Calculate weighted sum
        score = (
            likes * weights['likes'] +
            reposts * weights['reposts'] +
            replies * weights['replies'] +
            views * weights['views']
        )
        
        return score

# Usage
if __name__ == "__main__":
    scraper = XScraper()
    scraper.start_session()  # Opens X and waits for manual login
    scraper.scrape_all_tickers('bullx_tickers.csv', 'x_posts.csv')
    
    # Run sentiment analysis
    analyzer = CryptoSentimentAnalyzer()
    analyzer.analyze_csv('x_posts.csv')
    
    scraper.close()