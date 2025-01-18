from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import time
import csv
from datetime import datetime
import pandas as pd

# URL of the follow page
follow_page_url = "https://gmgn.ai/follow/8gcLcglg?chain=sol&tab=follow"

# Configure Chrome to connect to an already open session
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=chrome_options)

def safe_find(element, selector, attribute=None):
    """Safely find and return element text or attribute"""
    try:
        elements = element.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            if attribute:
                return elements[0].get_attribute(attribute)
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
    max_scroll_attempts = 2  # Reduced from 3 to 2

    try:
        # First, scroll to the top of the page
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)  # Reduced from 2 to 1
        
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
            
            if len(wallet_addresses) == last_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                
            last_count = len(wallet_addresses)
            
            # Scroll down faster
            if wallet_elements:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", 
                    wallet_elements[-1]
                )
                time.sleep(1)  # Reduced from 2 to 1
            
        print("No new wallets detected. Ending scrolling.")
        
        # Quick scroll back to top
        print("Scrolling back to top...")
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1.5)  # Reduced from 3 to 1.5
        
        return wallet_addresses
        
    except Exception as e:
        print(f"Error collecting wallets: {str(e)}")
        return wallet_addresses

def scrape_wallet(wallet_address):
    try:
        print(f"Scraping data for wallet: {wallet_address}")
        transactions = []
        
        # Wait for table to load
        print("Waiting for the Recent PnL table rows to load...")
        time.sleep(3)  # Reduced from 5 to 3 seconds
        
        # Get rows from Recent PnL table
        pnl_row_selector = "tr.g-table-row.g-table-row-level-0"
        rows = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, pnl_row_selector))
        )
        
        valid_rows = [row for row in rows if row.is_displayed()]
        print(f"Found {len(valid_rows)} valid rows in the wallet. Processing rows...")
        
        for idx, row in enumerate(valid_rows, 1):
            try:
                # Quick check if row has content
                if not row.text.strip():
                    continue
                
                # Get ticker name with faster checking
                ticker_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(1)")
                ticker_name = ticker_element.get_attribute('title') or ticker_element.text.strip()
                
                if not ticker_name or ticker_name == "N/A":
                    continue
                
                # Get all values in one pass
                transaction = {
                    'wallet_address': wallet_address,
                    'ticker': ticker_name,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Map of fields to their selectors with simplified selectors
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 7:  # Ensure we have enough cells
                    transaction.update({
                        'unrealized': cells[1].text.strip() or "N/A",
                        'realized': cells[2].text.strip() or "N/A",
                        'total_profit': cells[3].text.strip() or "N/A",
                        'balance': cells[4].text.strip() or "N/A",
                        'position': cells[5].text.strip() or "N/A",
                        'bought_avg': cells[6].text.strip() or "N/A"
                    })
                    
                    transactions.append(transaction)
                    print(f"Successfully processed ticker: {ticker_name}")
                
                if len(transactions) >= 75:
                    print("Reached maximum number of tickers (75). Stopping further scraping.")
                    break
                    
            except Exception as e:
                print(f"Error processing row {idx}: {str(e)}")
                continue
        
        print(f"Successfully processed {len(transactions)} transactions for wallet {wallet_address}")
        return transactions
        
    except Exception as e:
        print(f"Error scraping wallet data: {str(e)}")
        return []

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

def refresh_dom_with_scroll(target_wallet=None):
    """Helper function to ensure all wallets are properly loaded with better scanning"""
    print("Performing wallet list scroll to refresh DOM...")
    
    try:
        # Get the wallet list container
        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.g-table-tbody-virtual-holder"))
        )
        
        # Scroll to top first
        driver.execute_script("arguments[0].scrollTop = 0;", container)
        time.sleep(2)
        
        # Get container height
        container_height = driver.execute_script("return arguments[0].scrollHeight", container)
        scroll_height = container_height / 20  # Smaller scroll increments
        
        # Scroll slowly and check for wallet at each step
        current_scroll = 0
        wallet_found = False
        
        while current_scroll <= container_height and not wallet_found:
            # Scroll a small amount
            driver.execute_script(
                "arguments[0].scrollTop = arguments[1];", 
                container, 
                current_scroll
            )
            time.sleep(1.5)  # Longer wait for DOM to update
            
            # If we're looking for a specific wallet, check if it's visible
            if target_wallet:
                try:
                    wallet_selector = f"div.g-table-row.cursor-pointer[data-row-key='{target_wallet}']"
                    wallet_element = driver.find_element(By.CSS_SELECTOR, wallet_selector)
                    
                    # Check if element is in viewport
                    is_visible = driver.execute_script("""
                        var elem = arguments[0];
                        var container = elem.closest('.g-table-tbody-virtual-holder');
                        var containerRect = container.getBoundingClientRect();
                        var elemRect = elem.getBoundingClientRect();
                        return elemRect.top >= containerRect.top &&
                               elemRect.bottom <= containerRect.bottom;
                    """, wallet_element)
                    
                    if is_visible:
                        print(f"Found wallet {target_wallet} in viewport!")
                        wallet_found = True
                        return wallet_element
                except:
                    pass
            
            current_scroll += scroll_height
            
        # If we're looking for a specific wallet and didn't find it, try one more full scroll
        if target_wallet and not wallet_found:
            print("Wallet not found in first pass, trying one more full scroll...")
            driver.execute_script("arguments[0].scrollTop = 0;", container)
            time.sleep(2)
            return refresh_dom_with_scroll(target_wallet)
            
        return None
            
    except Exception as e:
        print(f"Error during scroll refresh: {str(e)}")
        return None

def click_wallet_with_retry(wallet_address, max_attempts=5):
    """Improved wallet clicking function with better scrolling and visibility checks"""
    for attempt in range(max_attempts):
        try:
            print(f"Click attempt {attempt + 1}...")
            
            # Wait for and find the wallet element
            wallet_selector = f"div.g-table-row.cursor-pointer[data-row-key='{wallet_address}']"
            
            # Get the container first
            container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.g-table-tbody-virtual-holder"))
            )
            
            # Find the wallet element
            wallet_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wallet_selector))
            )
            
            # Scroll the container to ensure element is in view
            driver.execute_script("""
                var element = arguments[0];
                var container = element.closest('.g-table-tbody-virtual-holder');
                
                // Get element and container positions
                var elementRect = element.getBoundingClientRect();
                var containerRect = container.getBoundingClientRect();
                
                // Calculate if element is in viewport
                var isInViewport = (
                    elementRect.top >= containerRect.top &&
                    elementRect.bottom <= containerRect.bottom
                );
                
                if (!isInViewport) {
                    // Scroll element into center of container
                    element.scrollIntoView({block: 'center', behavior: 'instant'});
                    
                    // Additional offset to center in container
                    container.scrollTop = container.scrollTop - (containerRect.height / 4);
                }
            """, wallet_element)
            
            # Wait for scrolling to settle
            time.sleep(2)
            
            # Verify element is clickable
            wallet_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, wallet_selector))
            )
            
            # Store initial URL
            initial_url = driver.current_url
            
            # Try multiple click methods
            click_methods = [
                # Method 1: Direct click after ensuring visibility
                lambda: (
                    driver.execute_script("arguments[0].style.border = '2px solid red';", wallet_element),
                    time.sleep(1),
                    wallet_element.click()
                ),
                # Method 2: JavaScript click
                lambda: driver.execute_script("arguments[0].click();", wallet_element),
                # Method 3: ActionChains with move and click
                lambda: ActionChains(driver).move_to_element(wallet_element).pause(1).click().perform(),
                # Method 4: JavaScript direct navigation
                lambda: driver.execute_script(f"window.location.href = '/wallet/{wallet_address}';")
            ]
            
            for click_method in click_methods:
                try:
                    click_method()
                    # Wait for URL change
                    WebDriverWait(driver, 5).until(
                        lambda d: wallet_address in d.current_url
                    )
                    print("Successfully navigated to wallet page")
                    return True
                except Exception as e:
                    print(f"Click method failed, trying next method... ({str(e)})")
                    continue
            
            print("All click methods failed, refreshing page...")
            driver.refresh()
            time.sleep(3)
            
        except Exception as e:
            print(f"Click attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_attempts - 1:
                print("Refreshing page and retrying...")
                driver.refresh()
                time.sleep(3)
                continue
    
    print("Failed to click wallet after all attempts")
    return False

def process_wallet(wallet_address, attempt=0):
    """Process a single wallet address with improved navigation handling"""
    try:
        print(f"\nProcessing wallet: {wallet_address}")
        
        # Navigate to follow page and wait for load
        driver.get(follow_page_url)
        print("Refreshing follow page...")
        time.sleep(3)
        
        print(f"Looking for wallet: {wallet_address}")
        print("Performing wallet list scroll to refresh DOM...")
        
        # Find the scroll container
        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.g-table-tbody-virtual-holder"))
        )
        
        # Scroll through the list to find the wallet
        wallet_found = False
        max_scroll_attempts = 10
        last_height = driver.execute_script("return arguments[0].scrollTop", container)
        
        for scroll_attempt in range(max_scroll_attempts):
            # Try to find the wallet
            try:
                wallet_selector = f"div.g-table-row.cursor-pointer[data-row-key='{wallet_address}']"
                wallet_element = driver.find_element(By.CSS_SELECTOR, wallet_selector)
                wallet_found = True
                print(f"Found wallet {wallet_address} after {scroll_attempt + 1} scroll attempts!")
                break
            except:
                # Scroll down
                driver.execute_script("arguments[0].scrollTop += 300", container)
                time.sleep(1)
                
                # Check if we've reached the bottom
                new_height = driver.execute_script("return arguments[0].scrollTop", container)
                if new_height == last_height:
                    # Scroll back to top and try again if we haven't found the wallet
                    driver.execute_script("arguments[0].scrollTop = 0", container)
                    time.sleep(1)
                last_height = new_height
        
        if not wallet_found:
            print(f"Could not find wallet {wallet_address} after scrolling")
            return []
            
        # Rest of the existing process_wallet function...
        print("Found wallet element, attempting to click...")
        if click_wallet_with_retry(wallet_address):
            # Wait for wallet data to load
            time.sleep(3)
            try:
                # Wait for transaction table to be present
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tr.g-table-row.g-table-row-level-0"))
                )
                return scrape_wallet(wallet_address)
            except TimeoutException:
                print("Transaction table not found")
                return []
        return []
            
    except Exception as e:
        print(f"Error processing wallet: {str(e)}")
        if attempt < 2:  # Max 3 attempts total
            print(f"Retrying wallet {wallet_address} (Attempt {attempt + 1} of 3)")
            time.sleep(3)
            return process_wallet(wallet_address, attempt + 1)
        return []

def process_wallets_in_batches(wallet_addresses, batch_size=5):
    """Process wallets in smaller batches and write to CSV"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'wallet_data_{timestamp}.csv'
    
    headers = [
        'wallet_address',
        'ticker',
        'unrealized',
        'realized',
        'total_profit',
        'balance',
        'position',
        'bought_avg',
        'timestamp'
    ]
    
    total_rows_written = 0
    
    # Create batches from wallet_addresses
    batches = [wallet_addresses[i:i + batch_size] for i in range(0, len(wallet_addresses), batch_size)]
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for batch_num, batch in enumerate(batches, 1):
            print(f"\nProcessing batch {batch_num} of {len(batches)}...")
            
            for idx, wallet_address in enumerate(batch, 1):
                print(f"\nAccessing wallet {idx} of {len(batch)} in current batch...")
                try:
                    transactions = process_wallet(wallet_address)
                    if transactions:
                        print(f"Writing {len(transactions)} transactions to CSV...")
                        writer.writerows(transactions)
                        csvfile.flush()
                        total_rows_written += len(transactions)
                        print(f"Total rows written so far: {total_rows_written}")
                    else:
                        print(f"No valid transactions found for wallet: {wallet_address}")
                except Exception as e:
                    print(f"Error processing wallet {wallet_address}: {str(e)}")
                    continue
    
    print(f"\nFinished! Total rows written to {csv_filename}: {total_rows_written}")

def check_csv_file(filename='wallet_data_20241227_175434.csv'):
    try:
        # Read the CSV file
        df = pd.read_csv(filename)
        
        # Print basic information about the dataset
        print("\nFile Information:")
        print("-" * 50)
        print(f"Number of rows: {len(df)}")
        print(f"Number of columns: {len(df.columns)}")
        print("\nColumns present:")
        for col in df.columns:
            print(f"- {col}")
            
        # Check if there's any data
        if len(df) == 0:
            print("\nWARNING: The file contains headers but no data!")
            return False
            
        # Print first few rows if data exists
        print("\nFirst few rows of data:")
        print(df.head())
        
        return True
        
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        return False

try:
    print("Navigating to the follow page...")
    driver.get(follow_page_url)
    time.sleep(2)  # Changed from 5 to 2 seconds

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