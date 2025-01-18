from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import time

# URL of the follow page
follow_page_url = "https://gmgn.ai/follow/8gcLcglg?chain=sol&tab=follow"

# Configure Chrome to connect to an already open session
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=chrome_options)

def safe_find(element, selector):
    """Safely find and return element text"""
    try:
        elements = element.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            return elements[0].text.strip()
        return "N/A"
    except Exception as e:
        print(f"Error finding element with selector {selector}: {str(e)}")
        return "N/A"

def scroll_and_collect_wallets():
    """
    Scrolls the page gradually to load wallets in the div.g-table-tbody-virtual-holder container,
    collects wallet addresses, then scrolls back to top.
    """
    wallet_selector = "div[data-row-key]"
    scrollable_container_selector = "div.g-table-tbody-virtual-holder"
    loaded_wallets = set()
    max_scroll_attempts = 50
    scroll_attempts = 0
    previous_wallet_count = 0
    scroll_multiplier = 0.5  # Controls how much of the container height to scroll

    try:
        # Wait for the page and scrollable container to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, scrollable_container_selector))
        )
        scrollable_container = driver.find_element(By.CSS_SELECTOR, scrollable_container_selector)
        
        while scroll_attempts < max_scroll_attempts:
            # Collect wallet addresses currently visible
            wallets = driver.find_elements(By.CSS_SELECTOR, wallet_selector)
            new_wallets = [
                wallet.get_attribute("data-row-key")
                for wallet in wallets if wallet.get_attribute("data-row-key")
            ]
            loaded_wallets.update(new_wallets)

            print(f"Scroll attempt {scroll_attempts + 1}: Collected {len(loaded_wallets)} wallets so far.")

            # Scroll the container by a portion of its height
            driver.execute_script(
                "arguments[0].scrollTop += arguments[0].offsetHeight * arguments[1];", 
                scrollable_container, 
                scroll_multiplier
            )
            time.sleep(2)  # Allow time for content to load

            # Check if new wallets have been loaded
            if len(loaded_wallets) == previous_wallet_count:
                scroll_attempts += 1
                if scroll_attempts >= 3:  # If no new wallets after 3 attempts
                    print("No new wallets detected. Ending scrolling.")
                    break
            else:
                scroll_attempts = 0  # Reset counter if we found new wallets
                
            previous_wallet_count = len(loaded_wallets)

        # Scroll back to top
        print("Scrolling back to top...")
        driver.execute_script("arguments[0].scrollTop = 0;", scrollable_container)
        time.sleep(2)

    except Exception as e:
        print(f"Error during scrolling: {e}")

    return list(loaded_wallets)

def scrape_wallet(wallet_address):
    """Scrape data from a wallet's ticker table"""
    try:
        print(f"Scraping data for wallet: {wallet_address}")
        print("Waiting for the Recent PnL table rows to load...")
        
        # Wait for the table to load with a longer timeout
        time.sleep(5)  # Additional wait for table to populate
        
        # Use the exact selector that worked before
        pnl_row_selector = "tr.g-table-row.g-table-row-level-0"
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, pnl_row_selector))
        )
        
        # Get all rows
        rows = driver.find_elements(By.CSS_SELECTOR, pnl_row_selector)
        print(f"Found {len(rows)} rows in the wallet. Processing rows...")
        
        valid_rows = 0
        for idx, row in enumerate(rows, 1):
            try:
                print(f"Processing row {idx} of {len(rows)}...")
                
                # Updated selectors based on the actual HTML structure
                ticker_name = safe_find(row, "td:nth-child(1) p.chakra-text")
                if not ticker_name or ticker_name == "N/A":
                    print(f"No valid ticker name found in row {idx}, skipping...")
                    continue
                
                valid_rows += 1
                print(f"Found valid ticker: {ticker_name}")
                
                # Get other values with updated selectors
                unrealized_value = safe_find(row, "td:nth-child(2) p.chakra-text")
                realized_value = safe_find(row, "td:nth-child(3) div[class*='css']")
                total_profit_value = safe_find(row, "td:nth-child(4) div[class*='css']")
                balance_value = safe_find(row, "td:nth-child(5) div[class*='css']")
                position_value = safe_find(row, "td:nth-child(6) div[class*='css']")
                bought_avg_value = safe_find(row, "td:nth-child(7) p.chakra-text")
                sold_avg_value = safe_find(row, "td:nth-child(8) p.chakra-text")
                
                # Special handling for transaction values
                txs_elements = row.find_elements(By.CSS_SELECTOR, "td:nth-child(9) div div")
                txs_value = f"{txs_elements[0].text.strip()}/{txs_elements[1].text.strip()}" if len(txs_elements) >= 2 else "N/A"

                print("-" * 50)
                print(f"Wallet Address: {wallet_address}")
                print(f"Ticker Name: {ticker_name}")
                print(f"Unrealized Value: {unrealized_value}")
                print(f"Realized Profit: {realized_value}")
                print(f"Total Profit: {total_profit_value}")
                print(f"Balance: {balance_value}")
                print(f"Position %: {position_value}")
                print(f"Bought Avg: {bought_avg_value}")
                print(f"Sold Avg: {sold_avg_value}")
                print(f"30D TXs: {txs_value}")
                print("-" * 50)

                if valid_rows >= 75:
                    print("Reached maximum number of tickers (75). Stopping further scraping.")
                    break

            except Exception as e:
                print(f"Error scraping row {idx}: {str(e)}")
                continue

        print(f"Finished processing wallet. Found {valid_rows} valid tickers.")

    except Exception as e:
        print(f"Error scraping wallet data: {str(e)}")

def wait_and_click_wallet(wallet_address, max_attempts=3):
    """
    Attempts to click on a wallet with retries and better wait conditions
    """
    for attempt in range(max_attempts):
        try:
            print(f"Attempt {attempt + 1} to click wallet {wallet_address}")
            
            # Store the current URL before any actions
            initial_url = driver.current_url
            
            # Wait for page to be fully loaded
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # First wait for the container to be present
            container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.g-table-tbody-virtual-holder"))
            )
            
            # Updated selector to match exact HTML structure
            wallet_selector = f"div.g-table-row.cursor-pointer[data-row-key='{wallet_address}']"
            print(f"Looking for wallet element with selector: {wallet_selector}")
            
            # Ensure the element is both present and visible
            wallet_element = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, wallet_selector))
            )
            
            # Scroll with offset to ensure element is clearly visible
            print("Scrolling to wallet...")
            driver.execute_script("""
                arguments[0].scrollIntoView({block: 'center'});
                window.scrollBy(0, -100);
            """, wallet_element)
            time.sleep(2)
            
            print("Attempting to click wallet...")
            # Try multiple click methods in sequence
            try:
                # Method 1: Direct click
                wallet_element.click()
            except:
                try:
                    # Method 2: JavaScript click
                    driver.execute_script("arguments[0].click();", wallet_element)
                except:
                    try:
                        # Method 3: Action chains
                        actions = ActionChains(driver)
                        actions.move_to_element(wallet_element).click().perform()
                    except:
                        # Method 4: Force click with JavaScript
                        driver.execute_script("""
                            var element = arguments[0];
                            var clickEvent = new MouseEvent('click', {
                                view: window,
                                bubbles: true,
                                cancelable: true
                            });
                            element.dispatchEvent(clickEvent);
                        """, wallet_element)
            
            # Wait for URL to change and verify we're on a new page
            print("Waiting for page navigation...")
            WebDriverWait(driver, 10).until(
                lambda d: d.current_url != initial_url
            )
            
            # Additional wait for the new page to load
            time.sleep(5)
            
            print("Successfully clicked wallet and navigated to new page!")
            return True
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_attempts - 1:
                print(f"Failed to click wallet after {max_attempts} attempts")
                return False
            print("Waiting before retry...")
            time.sleep(3)
    
    return False

def wait_for_wallet_data(wallet_address):
    """Wait for wallet-specific XHR requests to complete"""
    try:
        # Wait for wallet activity request
        WebDriverWait(driver, 15).until(
            lambda d: any(
                request.url for request in driver.requests 
                if f"wallet_activity/sol" in request.url 
                and wallet_address in request.url
                and request.response
                and request.response.status_code == 200
            )
        )
        
        # Wait for order list request
        WebDriverWait(driver, 15).until(
            lambda d: any(
                request.url for request in driver.requests 
                if "copy_order_list" in request.url 
                and wallet_address in request.url
                and request.response
                and request.response.status_code == 200
            )
        )
        return True
    except TimeoutException:
        return False

def process_wallet(wallet_address, attempt=0):
    """Process a single wallet with detailed error handling"""
    max_attempts = 3
    try:
        print(f"\nProcessing wallet: {wallet_address}")
        
        # Always refresh the follow page before processing a new wallet
        print("Refreshing follow page...")
        driver.get(follow_page_url)
        time.sleep(7)  # Increased wait time
        
        # Store initial URL
        initial_url = driver.current_url
        
        # Wait for the table container
        print("Waiting for table container...")
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.g-table-tbody-virtual-holder"))
        )
        
        # Find and click the wallet element
        print("Looking for wallet element...")
        wallet_selector = f"div.g-table-row.cursor-pointer[data-row-key='{wallet_address}']"
        
        try:
            print("Waiting for wallet element to be clickable...")
            wallet_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, wallet_selector))
            )
            
            # Scroll element into view
            print("Scrolling to wallet...")
            driver.execute_script("""
                arguments[0].scrollIntoView({block: 'center'});
                window.scrollBy(0, -100);
            """, wallet_element)
            time.sleep(2)
            
            print("Clicking wallet...")
            wallet_element.click()
            
            # Wait for URL change
            print("Waiting for page navigation...")
            WebDriverWait(driver, 10).until(
                lambda d: d.current_url != initial_url
            )
            
            # Additional wait for page load
            time.sleep(5)
            
            print("Wallet page loaded successfully, starting scrape...")
            scrape_wallet(wallet_address)
            
            # Return to main page
            print("Returning to main page...")
            driver.get(follow_page_url)
            time.sleep(3)
            
        except Exception as e:
            print(f"Error interacting with wallet element: {str(e)}")
            if attempt < max_attempts:
                print(f"Retrying... (Attempt {attempt + 1} of {max_attempts})")
                time.sleep(5)
                return process_wallet(wallet_address, attempt + 1)
            raise
            
    except Exception as e:
        print(f"Error processing wallet: {str(e)}")
        if attempt < max_attempts:
            print(f"Retrying entire wallet process... (Attempt {attempt + 1} of {max_attempts})")
            time.sleep(5)
            return process_wallet(wallet_address, attempt + 1)
        else:
            print(f"Failed to process wallet {wallet_address} after {max_attempts} attempts")

try:
    print("Navigating to the follow page...")
    driver.get(follow_page_url)
    time.sleep(5)

    # Step 1: Scroll and collect wallet addresses
    print("Starting wallet collection...")
    wallet_addresses = scroll_and_collect_wallets()
    
    print(f"\nCollected a total of {len(wallet_addresses)} wallets:")
    for addr in wallet_addresses:
        print(addr)

    # Step 2: Process first 6 wallet addresses
    for idx, wallet_address in enumerate(wallet_addresses[:6]):
        try:
            print(f"\nAccessing wallet {idx + 1}...")
            process_wallet(wallet_address)
        except Exception as e:
            print(f"Failed to process wallet {idx + 1}: {str(e)}")
            continue

except Exception as e:
    print(f"Fatal error: {str(e)}")
finally:
    print("Cleaning up...")
    try:
        driver.quit()
    except:
        pass