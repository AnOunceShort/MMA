from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import pandas as pd
import time

#### 

def scrape_bullx_tickers():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        wait = WebDriverWait(driver, 10)
        time.sleep(5)
        
        print("Looking for pump cards...")
        # Wait for and find the middle section (About to Graduate) using the exact path
        about_to_graduate_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, 
                "div.ant-layout.site-layout div.grid.grid-cols-1.lg\\:grid-cols-3.gap-2.h-full.p-2.min-h-0 > div:nth-child(2)"
            ))
        )
        
        print("Found About to Graduate section")
        
        # Find all pump cards within this section
        cards = about_to_graduate_section.find_elements(
            By.CSS_SELECTOR, 
            "div.pump-card"
        )
        
        print(f"Found {len(cards)} cards in About to Graduate section")
        
        # List to store all data
        ticker_data = []
        
        for i, card in enumerate(cards, 1):
            try:
                # Add explicit wait for card to be interactive
                wait.until(EC.element_to_be_clickable(card))
                
                # Find ticker
                ticker_element = card.find_element(
                    By.CSS_SELECTOR, 
                    "div.flex.items-center span"
                )
                ticker = ticker_element.text.strip()
                
                # Find market cap
                market_cap_element = card.find_element(
                    By.CSS_SELECTOR,
                    "div[title='Market Cap'] span.font-medium.text-xs.leading-none"
                )
                market_cap = market_cap_element.text.strip()
                
                # Find real traders with updated selector
                real_traders_element = card.find_element(
                    By.CSS_SELECTOR,
                    "div.flex.items-center span.text-grey-100.font-medium.text-xs.leading-none"
                )
                real_traders = real_traders_element.text.strip()
                
                # Find total holders
                total_holders_element = card.find_element(
                    By.CSS_SELECTOR,
                    "div[title='Total Holders'] span.text-grey-100.font-medium.text-xs.leading-none"
                )
                total_holders = total_holders_element.text.strip()
                
                # Add volume scraping
                volume_element = card.find_element(
                    By.CSS_SELECTOR,
                    "div[title='Volume'] span.font-medium.text-xs.leading-none"
                )
                volume = volume_element.text.strip()
                
                # Find all text elements with the specific class for additional data
                info_elements = card.find_elements(
                    By.CSS_SELECTOR,
                    "span.text-xs.leading-\\[1\\].font-normal.ml-0\\.5"
                )
                
                # Initialize variables
                insider_percentage = None
                dev_status = None
                top_10_holding = None
                
                # Process each text element
                for element in info_elements:
                    text = element.text.strip().lower()
                    if "insider" in text:
                        insider_percentage = element.text.strip()
                    elif "dev" in text:
                        dev_status = element.text.strip()
                    elif "top 10" in text:
                        top_10_holding = element.text.strip()
                
                # Modify insider percentage scraping to be more robust
                try:
                    insider_element = card.find_element(
                        By.CSS_SELECTOR,
                        "div[title='Percentage held by insiders'] span"
                    )
                    insider_percentage = insider_element.text.strip()
                except Exception as e:
                    # Try alternative selector if first one fails
                    try:
                        insider_element = card.find_element(
                            By.CSS_SELECTOR,
                            "div.flex.items-center span[title*='insider']"
                        )
                        insider_percentage = insider_element.text.strip()
                    except:
                        print(f"Card {i}: Insider percentage not found")
                        insider_percentage = None

                try:
                    # Look for the chef hat percentage specifically
                    dev_elements = card.find_elements(
                        By.CSS_SELECTOR,
                        "div.flex.items-center.gap-x-1.text-xs.leading-none.text-green-700 span, " +
                        "div.flex.items-center.gap-x-1.text-xs.leading-none.text-red-700 span"
                    )
                    
                    # Get the second span (the percentage value)
                    if len(dev_elements) >= 2:
                        dev_status = dev_elements[1].text.strip()
                    else:
                        dev_status = None

                    # Debug output
                    print(f"Card {i}: Found dev elements: {[e.text for e in dev_elements]}")
                    
                except Exception as e:
                    print(f"Card {i}: Dev status not found - {str(e)}")
                    dev_status = None

                try:
                    top10_element = card.find_element(
                        By.CSS_SELECTOR,
                        "div[title*='Top 10 holding']"  # Using contains(*) since percentage might vary
                    )
                    top_10_holding = top10_element.text.strip()
                except:
                    top_10_holding = None
                
                try:
                    # Find all elements with the specific class
                    elements = card.find_elements(
                        By.CSS_SELECTOR,
                        "span.text-xs.leading-\\[1\\].font-normal.ml-0\\.5"
                    )
                    
                    insider_percentage = None
                    sniper_count = None
                    
                    for element in elements:
                        parent = element.find_element(By.XPATH, '..')
                        parent_html = parent.get_attribute('outerHTML')
                        text = element.text.strip()
                        
                        # Check if this is an insider percentage element
                        if 'clip0_14699_77870' in parent_html:
                            insider_percentage = text
                        # Check if this is a sniper count element
                        elif 'M9.24992 7.0026' in parent_html:  # Unique part of the crosshair SVG
                            sniper_count = text
                            
                    print(f"Card {i}: Found insider: {insider_percentage}, snipers: {sniper_count}")

                except Exception as e:
                    print(f"Card {i}: Error in element processing - {str(e)}")
                    insider_percentage = None
                    sniper_count = None

                try:
                    # Get timestamp
                    timestamp_element = card.find_element(
                        By.CSS_SELECTOR, 
                        "div.flex.items-center.z-10.gap-3 > span > span"
                    )
                    timestamp = timestamp_element.text.strip() if timestamp_element else None
                    
                    # Get the link element that wraps the card
                    link_element = card.find_element(By.CSS_SELECTOR, "a[href*='terminal?chainId']")
                    href = link_element.get_attribute('href')
                    
                    # Extract the address from the href
                    # The format appears to be: .../terminal?chainId=1399811149&address=0x...
                    address = None
                    if href:
                        address_param = href.split('address=')[-1]
                        # If there are more parameters after the address, split them off
                        address = address_param.split('&')[0] if '&' in address_param else address_param
                    
                    if ticker and not ticker.startswith('$') and not any(c.isdigit() for c in ticker):
                        print(f"Card {i}: Found ticker {ticker} with MC {market_cap}, Address: {address}")
                        ticker_data.append({
                            'Ticker': ticker,
                            'Market_Cap': market_cap,
                            'Real_Traders': real_traders,
                            'Total_Holders': total_holders,
                            'Volume': volume,
                            'Insider_Percentage': insider_percentage,
                            'Dev_Status': dev_status,
                            'Top_10_Holding': top_10_holding,
                            'Sniper_Count': sniper_count,
                            'Timestamp': timestamp,
                            'Address': address  # Added contract address
                        })
                    
                    print(f"Card {i}: Found ticker {ticker} with additional data - Insiders: {insider_percentage}, Dev: {dev_status}, Top 10: {top_10_holding}")
                    
                except Exception as e:
                    print(f"Card {i}: Error in timestamp processing - {str(e)}")
                    timestamp = None

            except StaleElementReferenceException:
                print(f"Card {i}: Stale element")
                continue
            except Exception as e:
                print(f"Card {i}: Error - {str(e)}")
                continue
        
        # Save to CSV
        if ticker_data:
            df = pd.DataFrame(ticker_data)
            df.to_csv('bullx_tickers.csv', index=False)
            print(f"\nSuccessfully saved {len(ticker_data)} entries to bullx_tickers.csv")
            print("Data found:", df.to_string())
        else:
            print("\nNo data was found to save")
        
        return ticker_data
            
    except TimeoutException:
        print("Could not find any pump cards. Please make sure you're on the correct page.")
        return []
        
    finally:
        driver.quit()

if __name__ == "__main__":
    print("Starting BullX scraper...")
    print("Make sure Chrome is running with remote debugging port 9222")
    tickers = scrape_bullx_tickers()
    print(f"Scraped {len(tickers)} tickers") 