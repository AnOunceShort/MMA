from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
import pandas as pd
import time
from bs4 import BeautifulSoup

def scrape_bullx_tickers():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        wait = WebDriverWait(driver, 10)
        time.sleep(2)
        
        # Disable updates
        driver.execute_script("""
            window._originalSetTimeout = window.setTimeout;
            window.setTimeout = function() { return 0; };
            window._originalSetInterval = window.setInterval;
            window.setInterval = function() { return 0; };
        """)
        
        # Wait for cards and get them directly with Selenium
        cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.pump-card.group.row-hover.bg-grey-900")))
        print(f"Found {len(cards)} pump cards")
        
        ticker_data = []
        
        for i, card in enumerate(cards, 1):
            try:
                # Debug print
                print(f"\nProcessing card {i}:")
                card_html = card.get_attribute('innerHTML')
                print(f"Card HTML: {card_html[:200]}...")  # Print first 200 chars
                
                # Get ticker with wait
                ticker_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.text-grey-100.font-medium")), message=f"Ticker not found for card {i}")
                ticker = ticker_element.text.strip()
                print(f"Found ticker: {ticker}")
                
                # Get other data with explicit waits
                market_cap = "N/A"
                try:
                    market_cap_element = card.find_element(By.CSS_SELECTOR, "[title*='Market'] span")
                    market_cap = market_cap_element.text.strip()
                except:
                    print(f"No market cap found for {ticker}")
                
                real_traders = "N/A"
                try:
                    real_traders_element = card.find_element(By.CSS_SELECTOR, "[title*='Real'] span")
                    real_traders = real_traders_element.text.strip()
                except:
                    print(f"No real traders found for {ticker}")
                
                total_holders = "N/A"
                try:
                    total_holders_element = card.find_element(By.CSS_SELECTOR, "[title*='Total'] span")
                    total_holders = total_holders_element.text.strip()
                except:
                    print(f"No total holders found for {ticker}")
                
                volume = "N/A"
                try:
                    volume_element = card.find_element(By.CSS_SELECTOR, "[title*='Volume'] span")
                    volume = volume_element.text.strip()
                except:
                    print(f"No volume found for {ticker}")
                
                # Get stats
                stats = card.find_elements(By.CSS_SELECTOR, "div.flex.items-center span.text-grey-100")
                dev_holding = stats[0].text.strip() if len(stats) > 0 else "N/A"
                top_10 = stats[1].text.strip() if len(stats) > 1 else "N/A"
                
                if ticker and not ticker.startswith('$') and not any(c.isdigit() for c in ticker):
                    ticker_data.append({
                        'Ticker': ticker,
                        'Market_Cap': market_cap,
                        'Real_Traders': real_traders,
                        'Total_Holders': total_holders,
                        'Volume': volume,
                        'Dev_Holding': dev_holding,
                        'Top_10': top_10
                    })
                    print(f"Successfully scraped {ticker}")
                
            except Exception as e:
                print(f"Error processing card {i}: {str(e)}")
                continue
        
        # Restore original functionality
        driver.execute_script("""
            window.setTimeout = window._originalSetTimeout;
            window.setInterval = window._originalSetInterval;
        """)
        
        if ticker_data:
            df = pd.DataFrame(ticker_data)
            df.to_csv('bullx_tickers.csv', index=False)
            print(f"\nSuccessfully saved {len(ticker_data)} entries to bullx_tickers.csv")
            print("Data found:", df.to_string())
        else:
            print("\nNo data was found to save")
        
        return ticker_data
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return []
    finally:
        driver.quit()

if __name__ == "__main__":
    print("Starting BullX scraper...")
    print("Make sure Chrome is running with remote debugging port 9222")
    tickers = scrape_bullx_tickers()
    print(f"Scraped {len(tickers)} tickers") 