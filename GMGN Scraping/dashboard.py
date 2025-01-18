import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from transformers import pipeline
import torch
import time

### old model, not really used anymore. 

class CryptoSentimentAnalyzer:
    def __init__(self):
        print("\n=== GPU Check ===")
        print(f"MPS (M3 GPU) available: {torch.backends.mps.is_available()}")
        print(f"MPS (M3 GPU) built: {torch.backends.mps.is_built()}")
        
        # Initialize FinBERT
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
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Falling back to CPU mode")
            self.analyzer = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                device=-1
            )

        # Add crypto-specific context keywords
        self.crypto_context = {
            'general': ['crypto', 'token', 'coin', 'trading', 'price', 'market', 'chart',
                       'dex', 'exchange', 'volume', 'blockchain', 'wallet'],
            'price_action': ['resistance', 'support', 'breakout', 'breakdown', 'consolidation',
                           'trend', 'level', 'zone', 'accumulation', 'distribution'],
            'metrics': ['mcap', 'marketcap', 'supply', 'volume', 'liquidity', 'tvl'],
            'symbols': ['$', 'usd', 'usdt', 'btc', 'eth']
        }
        
        # Enhanced sentiment indicators
        self.sentiment_indicators = {
            'bullish': {
                'strong': ['accumulate', 'breakout', 'moon', 'long', 'buy signal', 'support holding'],
                'technical': ['higher lows', 'higher highs', 'golden cross', 'support test'],
                'fundamental': ['partnership', 'adoption', 'development', 'milestone']
            },
            'bearish': {
                'strong': ['breakdown', 'dump', 'short', 'resistance failed', 'support broken'],
                'technical': ['lower highs', 'lower lows', 'death cross', 'resistance test'],
                'fundamental': ['delay', 'issue', 'problem', 'concern']
            }
        }

    def is_crypto_relevant(self, text, ticker):
        """Check if the tweet is actually about the crypto token"""
        text = text.lower()
        ticker = ticker.lower().strip('$')
        
        # Direct ticker mentions
        ticker_mentioned = f"${ticker}" in text or f" {ticker} " in text
        if not ticker_mentioned:
            return False
            
        # Check for crypto context
        context_words = sum(self.crypto_context.values(), [])
        has_context = any(word in text for word in context_words)
        
        return has_context

    def analyze_text(self, text, ticker):
        """Enhanced sentiment analysis with relevancy check"""
        if not isinstance(text, str) or not text.strip():
            return 0.0, "Invalid text"
            
        # First check relevancy
        if not self.is_crypto_relevant(text, ticker):
            return 0.0, "Not crypto relevant"
            
        try:
            # Get base sentiment from FinBERT
            result = self.analyzer(text)[0]
            base_score = result['score']
            
            # Analyze technical indicators
            tech_score = self._analyze_technical_indicators(text)
            
            # Combine scores with weights
            final_score = (base_score * 0.4) + (tech_score * 0.6)
            
            # Normalize to [-1, 1]
            final_score = max(min(final_score, 1.0), -1.0)
            
            return final_score, self._get_sentiment_explanation(text, final_score)
            
        except Exception as e:
            return 0.0, f"Error: {str(e)}"

    def _analyze_technical_indicators(self, text):
        """Analyze technical and fundamental indicators"""
        text = text.lower()
        score = 0
        
        # Check bullish indicators
        for category in self.sentiment_indicators['bullish'].values():
            for phrase in category:
                if phrase in text:
                    score += 0.5
        
        # Check bearish indicators
        for category in self.sentiment_indicators['bearish'].values():
            for phrase in category:
                if phrase in text:
                    score -= 0.5
        
        return max(min(score, 1.0), -1.0)

    def _get_sentiment_explanation(self, text, score):
        """Generate explanation for sentiment score"""
        if score > 0.3:
            sentiment = "Bullish"
        elif score < -0.3:
            sentiment = "Bearish"
        else:
            sentiment = "Neutral"
            
        return {
            'label': sentiment,
            'score': f"{score:.2f}",
            'key_points': self._extract_key_points(text, sentiment)
        }

    def _extract_key_points(self, text, sentiment):
        """Extract key points that contributed to sentiment"""
        text = text.lower()
        points = []
        
        if sentiment == "Bullish":
            for category, phrases in self.sentiment_indicators['bullish'].items():
                for phrase in phrases:
                    if phrase in text:
                        points.append(f"{category.title()}: {phrase}")
        elif sentiment == "Bearish":
            for category, phrases in self.sentiment_indicators['bearish'].items():
                for phrase in phrases:
                    if phrase in text:
                        points.append(f"{category.title()}: {phrase}")
                        
        return points if points else ["General market sentiment"]

class SentimentDashboard:
    def __init__(self):
        st.set_page_config(
            page_title="Crypto Sentiment Dashboard",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        # Add the analyzer
        self.analyzer = CryptoSentimentAnalyzer()
        
        # Custom CSS to adjust layout
        st.markdown("""
            <style>
            .main > div {
                padding: 2rem;
            }
            .stSidebar > div {
                padding: 2rem;
                background-color: #1E1E1E;
            }
            .ticker-list {
                max-height: 400px;
                overflow-y: auto;
            }
            .post-list {
                max-height: 600px;
                overflow-y: auto;
                padding: 1rem;
                background-color: #2E2E2E;
                border-radius: 10px;
            }
            </style>
        """, unsafe_allow_html=True)
        self.load_data()
        
    def load_data(self):
        """Load and prepare data"""
        try:
            self.df = pd.read_csv('multi_x_posts_20250106_123559.csv')
            numeric_columns = ['likes', 'reposts', 'replies', 'views']
            for col in numeric_columns:
                if col in self.df.columns:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
            
            # Add sentiment analysis
            sentiments = []
            sentiment_words = []
            for _, row in self.df.iterrows():
                # Pass both text and ticker to analyze_text
                score, words = self.analyzer.analyze_text(row['text'], row['ticker'])
                sentiments.append(score)
                sentiment_words.append(words)
            
            self.df['sentiment'] = sentiments
            self.df['sentiment_words'] = sentiment_words
            
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            self.df = pd.DataFrame()
    
    def render_ticker_list(self):
        """Render the list of tickers on the left"""
        st.sidebar.title("Tickers")
        if not self.df.empty:
            tickers = sorted(self.df['ticker'].unique())
            selected_ticker = st.sidebar.selectbox(
                "Select Ticker",
                options=tickers,
                key="ticker_select"
            )
            return selected_ticker
        return None
    
    def render_sentiment_gauge(self, sentiment_value):
        """Render the main sentiment gauge"""
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = sentiment_value,
            domain = {'x': [0, 1], 'y': [0, 1]},
            gauge = {
                'axis': {'range': [-1, 1]},
                'bar': {'color': "lightblue"},
                'steps': [
                    {'range': [-1, -0.3], 'color': "red"},
                    {'range': [-0.3, 0.3], 'color': "gray"},
                    {'range': [0.3, 1], 'color': "green"}
                ]
            }
        ))
        fig.update_layout(height=400)
        return fig
    
    def explain_sentiment(self, text, sentiment_score, sentiment_details):
        """Create a human-readable explanation of the sentiment analysis"""
        try:
            # Handle the new sentiment_details format from the LLM
            if isinstance(sentiment_details, dict):
                explanation = f"""
                Sentiment: {sentiment_details.get('label', 'Unknown')}
                Confidence: {sentiment_details.get('confidence', 'N/A')}
                Score: {sentiment_details.get('score', 'N/A')}
                """
                
                # Add key points if available
                key_points = sentiment_details.get('key_points', [])
                if key_points:
                    explanation += f"\nKey points: {', '.join(key_points)}"
                    
                return explanation
            else:
                return f"Sentiment score: {sentiment_score:.2f}"
            
        except Exception as e:
            return f"Error explaining sentiment: {str(e)}"
    
    def render_post_list(self, filtered_df):
        """Render the scrollable post list with sentiment grouping"""
        st.markdown("### Post Analysis by Sentiment")
        
        # Create sentiment groups with clear thresholds
        bullish_posts = filtered_df[filtered_df['sentiment'] > 0.3]
        neutral_posts = filtered_df[(filtered_df['sentiment'] >= -0.3) & (filtered_df['sentiment'] <= 0.3)]
        bearish_posts = filtered_df[filtered_df['sentiment'] < -0.3]
        
        # Sort each group by views (descending)
        bullish_posts = bullish_posts.sort_values('views', ascending=False)
        neutral_posts = neutral_posts.sort_values('views', ascending=False)
        bearish_posts = bearish_posts.sort_values('views', ascending=False)
        
        # Display group counts
        st.markdown(f"""
        **Summary:**
        - 🟢 Bullish Posts: {len(bullish_posts)}
        - ⚪ Neutral Posts: {len(neutral_posts)}
        - 🔴 Bearish Posts: {len(bearish_posts)}
        """)
        
        # Bullish Posts Section
        st.markdown("---")
        st.markdown("### 🟢 Bullish Posts")
        if not bullish_posts.empty:
            for _, row in bullish_posts.iterrows():
                self._render_post_card(row, "success")
        else:
            st.info("No bullish posts found")
        
        # Neutral Posts Section
        st.markdown("---")
        st.markdown("### ⚪ Neutral Posts")
        if not neutral_posts.empty:
            for _, row in neutral_posts.iterrows():
                self._render_post_card(row, "info")
        else:
            st.info("No neutral posts found")
        
        # Bearish Posts Section
        st.markdown("---")
        st.markdown("### 🔴 Bearish Posts")
        if not bearish_posts.empty:
            for _, row in bearish_posts.iterrows():
                self._render_post_card(row, "error")
        else:
            st.info("No bearish posts found")

    def _render_post_card(self, row, sentiment_type):
        """Helper method to render individual post cards"""
        with st.expander(f"Post by {row['author']} (Views: {row.get('views', 0):,})", expanded=False):
            # Add a colored bar based on sentiment
            if sentiment_type == "success":
                st.markdown("🟢 **Bullish**")
            elif sentiment_type == "error":
                st.markdown("🔴 **Bearish**")
            else:
                st.markdown("⚪ **Neutral**")
            
            st.write(row['text'])
            
            # Engagement metrics
            cols = st.columns(4)
            cols[0].metric("Likes", row['likes'])
            cols[1].metric("Reposts", row['reposts'])
            cols[2].metric("Replies", row['replies'])
            cols[3].metric("Views", row.get('views', 0))
            
            # Sentiment explanation
            st.markdown("---")
            st.markdown("#### Sentiment Analysis")
            sentiment_explanation = self.explain_sentiment(
                row['text'],
                row['sentiment'],
                row.get('sentiment_words', [])
            )
            st.markdown(sentiment_explanation)
    
    def generate_ticker_summary(self, filtered_df):
        """Generate a comprehensive summary of all posts for a ticker"""
        try:
            total_posts = len(filtered_df)
            
            # Engagement metrics
            total_likes = filtered_df['likes'].sum()
            total_reposts = filtered_df['reposts'].sum()
            avg_engagement = (total_likes + total_reposts) / total_posts if total_posts > 0 else 0
            
            # Sentiment distribution
            bullish_count = len(filtered_df[filtered_df['sentiment'] > 0.3])
            neutral_count = len(filtered_df[(filtered_df['sentiment'] >= -0.3) & (filtered_df['sentiment'] <= 0.3)])
            bearish_count = len(filtered_df[filtered_df['sentiment'] < -0.3])
            
            # Identify influential accounts
            top_accounts = filtered_df.groupby('author').agg({
                'likes': 'sum',
                'reposts': 'sum'
            }).sort_values('likes', ascending=False).head(3)
            
            # Common themes/keywords
            text_blob = ' '.join(filtered_df['text'].str.lower())
            common_words = [word for word in text_blob.split() 
                           if word.startswith('$') or word.startswith('#') or 
                           any(term in word for term in ['bull', 'bear', 'pump', 'dump', 'moon', 'price'])]
            
            summary = f"""
            ### 📊 Ticker Analysis Summary
            
            **Overview:**
            - Total Posts Analyzed: {total_posts}
            - Overall Sentiment: {'Bullish' if bullish_count > bearish_count else 'Bearish' if bearish_count > bullish_count else 'Neutral'}
            
            **Sentiment Breakdown:**
            - 🟢 Bullish Posts: {bullish_count} ({(bullish_count/total_posts*100):.1f}%)
            - ⚪ Neutral Posts: {neutral_count} ({(neutral_count/total_posts*100):.1f}%)
            - 🔴 Bearish Posts: {bearish_count} ({(bearish_count/total_posts*100):.1f}%)
            
            **Engagement Metrics:**
            - Total Likes: {total_likes:,}
            - Total Reposts: {total_reposts:,}
            - Average Engagement per Post: {avg_engagement:.1f}
            
            **Key Influencers:**
            {self._format_top_accounts(top_accounts)}
            
            **Common Themes:**
            {', '.join(set(common_words[:10]))}
            """
            
            return summary
        
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    def _format_top_accounts(self, top_accounts):
        """Format top accounts data for display"""
        result = []
        for author, data in top_accounts.iterrows():
            result.append(f"- @{author}: {data['likes']} likes, {data['reposts']} reposts")
        return '\n'.join(result)

    def _generate_ai_insights(self, df):
        """Generate AI insights about the overall conversation"""
        # Calculate metrics
        recent_sentiment_trend = df.sort_values('timestamp')['sentiment'].tail(10).mean()
        high_engagement_sentiment = df.nlargest(5, 'likes')['sentiment'].mean()
        
        insights = []
        
        # Add trend analysis
        if recent_sentiment_trend > 0.3:
            insights.append("📈 Recent posts show increasingly bullish sentiment")
        elif recent_sentiment_trend < -0.3:
            insights.append("📉 Recent posts indicate growing bearish sentiment")
        
        # Add engagement analysis
        if high_engagement_sentiment > 0:
            insights.append("👥 Most engaged posts are predominantly bullish")
        elif high_engagement_sentiment < 0:
            insights.append("👥 Most engaged posts lean bearish")
        
        # Add volume analysis
        hourly_volume = df.groupby(pd.Grouper(key='timestamp', freq='H')).size()
        if hourly_volume.max() > hourly_volume.mean() * 2:
            insights.append("📊 Significant spikes in discussion volume detected")
        
        return "\n".join(insights)

    def run(self):
        """Run the dashboard"""
        st.title("Sentiment Calculator")
        
        # Sidebar for ticker selection
        st.sidebar.title("Tickers")
        selected_ticker = self.render_ticker_list()
        
        if selected_ticker:
            # Filter data for selected ticker
            filtered_df = self.df[self.df['ticker'] == selected_ticker]
            
            # Main content area
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Sentiment gauge
                avg_sentiment = filtered_df['sentiment'].mean()
                gauge_html = f"""
                    <div style="text-align: center;">
                        <div class="gauge" style="width: 300px; margin: auto;">
                            <div class="gauge-value" style="transform: rotate({(avg_sentiment + 1) * 90}deg);">
                                {avg_sentiment:.1f}
                            </div>
                        </div>
                    </div>
                """
                st.markdown(gauge_html, unsafe_allow_html=True)
                
                # Metrics below gauge
                metrics_cols = st.columns(4)
                with metrics_cols[0]:
                    st.metric("Total Posts", len(filtered_df))
                with metrics_cols[1]:
                    st.metric("Total Likes", filtered_df['likes'].sum() if 'likes' in filtered_df.columns else 0)
                with metrics_cols[2]:
                    st.metric("Total Reposts", filtered_df['reposts'].sum() if 'reposts' in filtered_df.columns else 0)
                with metrics_cols[3]:
                    st.metric("Total Replies", filtered_df['replies'].sum() if 'replies' in filtered_df.columns else 0)
            
            with col2:
                # Post Analysis by Sentiment
                st.markdown("### Post Analysis by Sentiment")
                
                # Summary counts
                bullish = len(filtered_df[filtered_df['sentiment'] > 0.3])
                neutral = len(filtered_df[(filtered_df['sentiment'] >= -0.3) & (filtered_df['sentiment'] <= 0.3)])
                bearish = len(filtered_df[filtered_df['sentiment'] < -0.3])
                
                st.markdown(f"""
                    🟢 Bullish Posts: {bullish}
                    ⚪ Neutral Posts: {neutral}
                    🔴 Bearish Posts: {bearish}
                """)
                
                # Expandable sections for posts by sentiment
                st.markdown("### 🟢 Bullish Posts")
                bullish_posts = filtered_df[filtered_df['sentiment'] > 0.3]
                for _, row in bullish_posts.iterrows():
                    with st.expander(f"Post by {row['username']} - Score: {row['sentiment']:.2f}"):
                        st.write(row['text'])
                
                st.markdown("### ⚪ Neutral Posts")
                neutral_posts = filtered_df[(filtered_df['sentiment'] >= -0.3) & (filtered_df['sentiment'] <= 0.3)]
                for _, row in neutral_posts.iterrows():
                    with st.expander(f"Post by {row['username']} - Score: {row['sentiment']:.2f}"):
                        st.write(row['text'])
                
                st.markdown("### 🔴 Bearish Posts")
                bearish_posts = filtered_df[filtered_df['sentiment'] < -0.3]
                for _, row in bearish_posts.iterrows():
                    with st.expander(f"Post by {row['username']} - Score: {row['sentiment']:.2f}"):
                        st.write(row['text'])
        
        else:
            st.warning("Please select a ticker from the dropdown")

        # Add CSS for the gauge
        st.markdown("""
        <style>
        .gauge {
            position: relative;
            border-radius: 50%/100% 100% 0 0;
            background-color: #ddd;
            height: 150px;
            overflow: hidden;
        }
        .gauge-value {
            position: absolute;
            background-color: #4CAF50;
            width: 100%;
            height: 100%;
            transform-origin: center top;
            transition: transform 0.2s ease-out;
        }
        </style>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    dashboard = SentimentDashboard()
    dashboard.run()