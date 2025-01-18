import praw
from textblob import TextBlob
import pandas as pd
from collections import Counter
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def initialize_reddit():
    """Initialize Reddit API connection"""
    return praw.Reddit(
        client_id=os.getenv('REDDIT_CLIENT_ID'),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
        user_agent=os.getenv('REDDIT_USER_AGENT'),
        username=os.getenv('REDDIT_USERNAME'),
        password=os.getenv('REDDIT_PASSWORD')
    )

def extract_tickers(text):
    """Extract stock tickers from text (assumed to be in $TICKER format)"""
    return re.findall(r'\$([A-Za-z]+)', text)

def analyze_sentiment(text):
    """Return sentiment polarity score (-1 to 1) for given text"""
    return TextBlob(text).sentiment.polarity

def analyze_reddit_post(post_url):
    """Analyze a Reddit post for comments, sentiment, and tickers"""
    reddit = initialize_reddit()
    
    # Get submission
    submission = reddit.submission(url=post_url)
    submission.comments.replace_more(limit=None)  # Get all comments
    
    comments_data = []
    all_tickers = []
    
    # Analyze each comment
    for comment in submission.comments.list():
        sentiment = analyze_sentiment(comment.body)
        tickers = extract_tickers(comment.body)
        all_tickers.extend(tickers)
        
        comments_data.append({
            'author': str(comment.author),
            'body': comment.body,
            'score': comment.score,
            'sentiment': sentiment,
            'tickers': tickers
        })
    
    # Convert to DataFrame
    df = pd.DataFrame(comments_data)
    
    # Generate analysis
    analysis = {
        'total_comments': len(df),
        'average_sentiment': df['sentiment'].mean(),
        'top_commenters': df.groupby('author')['score'].sum().sort_values(ascending=False).head(),
        'most_mentioned_tickers': Counter(all_tickers).most_common(5),
        'highest_scored_comments': df.nlargest(5, 'score')[['author', 'body', 'score']],
        'most_positive_comments': df.nlargest(5, 'sentiment')[['author', 'body', 'sentiment']],
        'most_negative_comments': df.nsmallest(5, 'sentiment')[['author', 'body', 'sentiment']]
    }
    
    return analysis

if __name__ == "__main__":
    post_url = input("Enter the Reddit post URL: ")
    try:
        results = analyze_reddit_post(post_url)
        
        print("\n=== Reddit Post Analysis ===")
        print(f"\nTotal Comments: {results['total_comments']}")
        print(f"Average Sentiment: {results['average_sentiment']:.2f}")
        
        print("\nTop Commenters:")
        for author, score in results['top_commenters'].items():
            print(f"- {author}: {score} points")
        
        print("\nMost Mentioned Tickers:")
        for ticker, count in results['most_mentioned_tickers']:
            print(f"- ${ticker}: {count} mentions")
        
        print("\nHighest Scored Comments:")
        print(results['highest_scored_comments'])
        
        print("\nMost Positive Comments:")
        print(results['most_positive_comments'])
        
        print("\nMost Negative Comments:")
        print(results['most_negative_comments'])
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
