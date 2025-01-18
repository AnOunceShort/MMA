import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from x import CryptoSentimentAnalyzer  # Import at top of file

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
            self.df = pd.read_csv('x_posts.csv')
            numeric_columns = ['likes', 'reposts', 'replies', 'views']
            for col in numeric_columns:
                if col in self.df.columns:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
            
            # Add sentiment analysis
            sentiments = []
            sentiment_words = []
            for text in self.df['text']:
                score, words = self.analyzer.analyze_text(text)
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
        st.markdown("### Post Index")
        
        # Sort dataframe by sentiment score (descending)
        sorted_df = filtered_df.sort_values('sentiment', ascending=False)
        
        # Create sentiment groups
        bullish_posts = sorted_df[sorted_df['sentiment'] > 0.3]
        neutral_posts = sorted_df[(sorted_df['sentiment'] >= -0.3) & (sorted_df['sentiment'] <= 0.3)]
        bearish_posts = sorted_df[sorted_df['sentiment'] < -0.3]
        
        # Bullish Posts Section
        if not bullish_posts.empty:
            st.markdown("#### 🟢 Bullish Posts")
            for _, row in bullish_posts.iterrows():
                self._render_post_card(row, "success")
        
        # Neutral Posts Section
        if not neutral_posts.empty:
            st.markdown("#### ⚪ Neutral Posts")
            for _, row in neutral_posts.iterrows():
                self._render_post_card(row, "info")
        
        # Bearish Posts Section
        if not bearish_posts.empty:
            st.markdown("#### 🔴 Bearish Posts")
            for _, row in bearish_posts.iterrows():
                self._render_post_card(row, "error")

    def _render_post_card(self, row, sentiment_type):
        """Helper method to render individual post cards"""
        with st.expander(f"Post by {row['author']} (Score: {row['sentiment']:.2f})", expanded=False):
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
    
    def run(self):
        """Main dashboard rendering method"""
        # Layout setup
        selected_ticker = self.render_ticker_list()
        
        if not self.df.empty and selected_ticker:
            filtered_df = self.df[self.df['ticker'] == selected_ticker]
            
            # Main content area
            main_col1, main_col2 = st.columns([2, 1])
            
            with main_col1:
                st.title("Sentiment Calculator")
                # Example sentiment value - replace with actual calculation
                avg_sentiment = 0.5  # placeholder
                sentiment_fig = self.render_sentiment_gauge(avg_sentiment)
                st.plotly_chart(sentiment_fig, use_container_width=True)
                
                # Additional metrics below the gauge
                metrics_cols = st.columns(4)
                with metrics_cols[0]:
                    st.metric("Total Posts", len(filtered_df))
                with metrics_cols[1]:
                    st.metric("Total Likes", filtered_df['likes'].sum())
                with metrics_cols[2]:
                    st.metric("Total Reposts", filtered_df['reposts'].sum())
                with metrics_cols[3]:
                    st.metric("Total Replies", filtered_df['replies'].sum())
            
            with main_col2:
                self.render_post_list(filtered_df)
        else:
            st.warning("No data available. Please check if the data file exists and contains valid data.")

if __name__ == "__main__":
    dashboard = SentimentDashboard()
    dashboard.run()