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
    """Scroll through the page and collect all wallet addresses"""
    wallet_addresses = []  # Changed from set to list to maintain order
    last_count = 0
    scroll_attempts = 0
    max_scroll_attempts = 3

    try:
        # First, scroll to the top of the page
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        while scroll_attempts < max_scroll_attempts:
            # Get all wallet elements currently visible
            wallet_elements = driver.find_elements(
                By.CSS_SELECTOR, 
                "div.g-table-row.cursor-pointer[data-row-key]"
            )
            
            # Extract wallet addresses while maintaining order
            current_wallets = [
                element.get_attribute('data-row-key') 
                for element in wallet_elements 
                if element.get_attribute('data-row-key')
            ]
            
            # Add new wallets while maintaining order
            for wallet in current_wallets:
                if wallet not in wallet_addresses:
                    wallet_addresses.append(wallet)
            
            print(f"Scroll attempt {scroll_attempts + 1}: Collected {len(wallet_addresses)} wallets so far.")
            
            if len(wallet_addresses) == last_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                
            last_count = len(wallet_addresses)
            
            # Scroll down
            if wallet_elements:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", 
                    wallet_elements[-1]
                )
                time.sleep(2)
            
        print("No new wallets detected. Ending scrolling.")
        
        # Scroll back to top and wait
        print("Scrolling back to top...")
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(3)  # Increased wait time after scrolling to top
        
        return wallet_addresses
        
    except Exception as e:
        print(f"Error collecting wallets: {str(e)}")
        return wallet_addresses

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
                # Updated selectors based on the actual HTML structure
                ticker_name = safe_find(row, "td:nth-child(1) p.chakra-text")
                if not ticker_name or ticker_name == "N/A":
                    continue
                
                valid_rows += 1
                
                # Get other values with updated selectors
                unrealized_value = safe_find(row, "td:nth-child(2) p.chakra-text")
                realized_value = safe_find(row, "td:nth-child(3) div[class*='css']")
                total_profit_value = safe_find(row, "td:nth-child(4) div[class*='css']")
                balance_value = safe_find(row, "td:nth-child(5) div[class*='css']")
                position_value = safe_find(row, "td:nth-child(6) div[class*='css']")
                bought_avg_value = safe_find(row, "td:nth-child(7) p.chakra-text")
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

def refresh_dom_with_scroll():
    """Helper function to aggressively scroll the wallet list container"""
    print("Performing aggressive wallet list scroll...")
    
    try:
        # Get the wallet list container
        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.g-table-tbody-virtual-holder"))
        )
        
        # Get container height
        container_height = driver.execute_script("return arguments[0].scrollHeight", container)
        
        # Scroll container to top first
        driver.execute_script("arguments[0].scrollTop = 0;", container)
        time.sleep(2)
        
        # Scroll down in increments
        scroll_increment = container_height // 4  # Divide container into quarters
        for i in range(4):
            # Scroll down in increments
            driver.execute_script(
                "arguments[0].scrollTop = arguments[1];", 
                container, 
                scroll_increment * (i + 1)
            )
            time.sleep(1.5)
        
        # Stay at bottom position instead of scrolling back up
        time.sleep(2)
        
    except Exception as e:
        print(f"Error during container scroll: {str(e)}")

def process_wallet(wallet_address, attempt=0):
    """Process a single wallet with detailed error handling"""
    max_attempts = 3
    try:
        print(f"\nProcessing wallet: {wallet_address}")
        
        # Always refresh the follow page before processing a new wallet
        print("Refreshing follow page...")
        driver.get(follow_page_url)
        time.sleep(7)  # Increased wait time
        
        if attempt > 0:
            # Use aggressive scrolling on retry attempts and stay at bottom
            refresh_dom_with_scroll()
            time.sleep(2)  # Give time for new content to load
        
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
            
            # Don't scroll back to top, just center the element we want
            print("Scrolling to wallet...")
            driver.execute_script("""
                arguments[0].scrollIntoView({block: 'center'});
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
                print(f"\nRetrying... (Attempt {attempt + 1} of {max_attempts})")
                # Scroll up and down to refresh DOM
                print("Scrolling to refresh DOM...")
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
                return process_wallet(wallet_address, attempt + 1)
            raise
            
    except Exception as e:
        print(f"Error processing wallet: {str(e)}")
        if attempt < max_attempts:
            print(f"\nRetrying entire wallet process... (Attempt {attempt + 1} of {max_attempts})")
            # Scroll up and down to refresh DOM
            print("Scrolling to refresh DOM...")
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            return process_wallet(wallet_address, attempt + 1)
        else:
            print(f"Failed to process wallet {wallet_address} after {max_attempts} attempts")

def process_wallets_in_batches(wallet_list, batch_size=6):
    """Process wallets in batches, scrolling between each batch"""
    total_wallets = len(wallet_list)
    processed = 0
    
    while processed < total_wallets:
        print(f"\nProcessing batch {(processed // batch_size) + 1}...")
        
        # Get next batch of wallets
        batch = wallet_list[processed:processed + batch_size]
        
        # Process each wallet in the current batch
        for wallet_address in batch:
            print(f"\nAccessing wallet {(processed % batch_size) + 1} of current batch...")
            process_wallet(wallet_address)
            processed += 1
        
        if processed < total_wallets:
            print("\nBatch complete. Scrolling to reveal next set of wallets...")
            # Scroll down to reveal next batch
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(3)
            
            # Scroll back to top for next batch
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(3)
            
            # Refresh the page to ensure clean state
            driver.refresh()
            time.sleep(5)
    
    print("\nAll wallets processed successfully!")

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

    # Step 2: Process wallets in batches
    process_wallets_in_batches(wallet_addresses)

except Exception as e:
    print(f"Fatal error: {str(e)}")
finally:
    print("Cleaning up...")
    try:
        driver.quit()
    except:
        pass