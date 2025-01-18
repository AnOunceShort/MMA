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
        """Search for ticker and collect posts"""
        results = []
        
        try:
            # Random delay before search
            time.sleep(random.uniform(2, 4))
            
            # Search URL modified to get top posts
            search_url = f"https://twitter.com/search?q={ticker}&src=typed_query&f=top"
            self.driver.get(search_url)
            
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

class CryptoSentimentAnalyzer:
    def __init__(self):
        print("\n=== GPU Check ===")
        print(f"MPS (M3 GPU) available: {torch.backends.mps.is_available()}")
        print(f"MPS (M3 GPU) built: {torch.backends.mps.is_built()}")
        
        start_time = time.time()
        try:
            if torch.backends.mps.is_available():
                print("🚀 Using M3 GPU acceleration!")
                device = "mps"
            else:
                print("⚠️ Using CPU mode")
                device = -1
            
            self.analyzer = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                device=device
            )
            end_time = time.time()
            print(f"Model loaded in {end_time - start_time:.2f} seconds")
            
            # Test GPU with a sample
            test_start = time.time()
            self.analyze_text("Test message")
            test_end = time.time()
            print(f"Test analysis took {(test_end - test_start):.3f} seconds")
            
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Falling back to CPU mode")
            self.analyzer = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                device=-1
            )
        
        # Add crypto-specific sentiment boosters
        self.bullish_phrases = {
            'moon': 1.0,
            'breakout': 0.8,
            'bullish': 0.8,
            'potential': 0.6,
            'pump': 0.7,
            '$': 0.5,  # Dollar signs often indicate price targets
            'new high': 0.8,
            'runner': 0.7,
            'blast': 0.6
        }

    def analyze_text(self, text):
        """Enhanced sentiment analysis with crypto context"""
        try:
            # Get base sentiment from model
            result = self.analyzer(text)[0]
            base_score = result['score']
            base_label = result['label']
            
            # Check for crypto-specific bullish signals
            boost = 0
            key_points = []
            
            # Convert text to lowercase for matching
            text_lower = text.lower()
            
            # Look for price predictions (e.g., $100m, $900k)
            if '$' in text:
                import re
                price_matches = re.findall(r'\$\d+(?:k|m|M|K)?', text)
                if price_matches:
                    boost += 0.5
                    key_points.append(f"Price target: {', '.join(price_matches)}")
            
            # Check for bullish phrases
            for phrase, score in self.bullish_phrases.items():
                if phrase.lower() in text_lower:
                    boost += score
                    key_points.append(f"Bullish signal: {phrase}")
            
            # Calculate final sentiment
            final_score = min(1.0, max(-1.0, base_score + boost))
            
            # Determine final label
            if final_score > 0.3:
                final_label = 'positive'
            elif final_score < -0.3:
                final_label = 'negative'
            else:
                final_label = 'neutral'
            
            explanation = {
                'label': final_label,
                'confidence': f"{result['score']:.2f}",
                'score': f"{final_score:.2f}",
                'key_points': key_points if key_points else ['General tone and context'],
                'boost_applied': f"{boost:.2f}" if boost > 0 else None
            }
            
            return final_score, explanation
            
        except Exception as e:
            print(f"Error in analysis: {str(e)}")
            return 0.0, "Error analyzing sentiment"

    def _extract_key_points(self, text, sentiment):
        """Extract key points that contributed to sentiment"""
        # Basic key phrases to look for
        bullish_indicators = ['up', 'bull', 'grow', 'gain', 'profit', 'moon']
        bearish_indicators = ['down', 'bear', 'drop', 'loss', 'crash', 'dump']
        
        text_lower = text.lower()
        found_points = []
        
        # Look for relevant phrases based on sentiment
        if sentiment.lower() == 'positive':
            for indicator in bullish_indicators:
                if indicator in text_lower:
                    found_points.append(indicator)
        elif sentiment.lower() == 'negative':
            for indicator in bearish_indicators:
                if indicator in text_lower:
                    found_points.append(indicator)
        
        return found_points or ["General tone and context"]

    def analyze_csv(self, csv_file):
        """Analyze sentiment from CSV file"""
        print("\n=== Crypto Sentiment Analysis ===")
        print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 40)
        
        df = pd.read_csv(csv_file)
        results = []
        
        for _, row in df.iterrows():
            sentiment_score, explanation = self.analyze_text(row['text'])
            result = {
                'ticker': row['ticker'],
                'username': row['author'],
                'text': row['text'],
                'sentiment_score': sentiment_score,
                'sentiment_details': explanation,
                'engagement_score': self.calculate_engagement(
                    row.get('likes', 0),
                    row.get('reposts', 0),
                    row.get('replies', 0),
                    row.get('views', 0)
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
            print(f"Average sentiment: {ticker_data['sentiment_score'].mean():.2f}")
            print(f"Average engagement: {ticker_data['engagement_score'].mean():.2f}")
            
            # Most influential posts
            print("\nTop 3 Most Influential Posts:")
            top_posts = ticker_data.nlargest(3, 'engagement_score')
            for _, post in top_posts.iterrows():
                print(f"\nUser: {post['username']}")
                print(f"Text: {post['text'][:100]}...")
                print(f"Sentiment: {post['sentiment_score']:.2f}")
                print(f"Sentiment Details: {post['sentiment_details']}")
                print(f"Engagement Score: {post['engagement_score']:.2f}")

    def calculate_engagement(self, likes, reposts, replies, views):
        """Calculate engagement score based on metrics"""
        weights = {
            'likes': 1,
            'reposts': 2,
            'replies': 1.5,
            'views': 0.1
        }
        
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
    
    # Test single analysis
    text = "Bitcoin looking very bullish today with strong support levels!"
    score, explanation = analyzer.analyze_text(text)
    print(f"Score: {score}")
    print(f"Explanation: {explanation}")
    
    # Analyze CSV file
    analyzer.analyze_csv('x_posts.csv')
    
    scraper.close()