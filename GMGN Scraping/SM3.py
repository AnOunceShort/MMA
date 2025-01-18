from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time

# URL of the follow page
follow_page_url = "https://gmgn.ai/follow/8gcLcglg?chain=sol&tab=follow"

# Configure Chrome to connect to an already open session
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=chrome_options)

def collect_wallets():
    """Collect wallet addresses from the page"""
    print("Collecting wallet addresses...")
    try:
        # Wait for the table to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.g-table-tbody-virtual-holder"))
        )
        time.sleep(2)  # Give extra time for elements to render

        # Find all wallet elements
        wallet_elements = driver.find_elements(
            By.CSS_SELECTOR, 
            "div.g-table-row.cursor-pointer[data-row-key]"
        )
        
        # Extract wallet addresses
        wallet_addresses = [
            element.get_attribute('data-row-key') 
            for element in wallet_elements 
            if element.get_attribute('data-row-key')
        ]
        
        print(f"Found {len(wallet_addresses)} wallet addresses")
        if wallet_addresses:
            print(f"First wallet address: {wallet_addresses[0]}")
        return wallet_addresses
        
    except Exception as e:
        print(f"Error collecting wallets: {str(e)}")
        return []

def click_wallet(wallet_address):
    """Click on a specific wallet"""
    try:
        print(f"Attempting to click wallet: {wallet_address}")
        
        # Wait for wallet element
        wallet_selector = f"div.g-table-row.cursor-pointer[data-row-key='{wallet_address}']"
        wallet_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, wallet_selector))
        )
        
        # Scroll element into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", wallet_element)
        time.sleep(2)
        
        # Click the wallet
        wallet_element.click()
        
        # Wait for URL change
        WebDriverWait(driver, 10).until(
            lambda d: wallet_address in d.current_url
        )
        
        print("Successfully clicked wallet")
        return True
        
    except Exception as e:
        print(f"Error clicking wallet: {str(e)}")
        return False

def click_first_ticker():
    """Click the first ticker's row (blank space) in a wallet page"""
    try:
        print("Waiting for tickers to load...")
        time.sleep(5)  # Wait for page load
        
        # Print current URL to verify we're on the right page
        print(f"Current URL: {driver.current_url}")
        
        # Print page source length to verify content is loaded
        page_source = driver.page_source
        print(f"Page source length: {len(page_source)}")
        
        # Try different wait times and selectors
        selectors = [
            ".g-table-cell",  # Simple class selector
            "div.g-table-cell",  # More specific
            "//div[@class='g-table-cell']",  # XPath
            "//div[contains(@class, 'g-table-cell')]"  # Partial class match
        ]
        
        for wait_time in [5, 10, 15]:  # Try different wait times
            print(f"\nTrying with {wait_time} second wait...")
            time.sleep(wait_time)
            
            for selector in selectors:
                try:
                    print(f"\nTrying selector: {selector}")
                    by_type = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                    
                    # Find all elements matching the selector
                    elements = driver.find_elements(by_type, selector)
                    print(f"Found {len(elements)} elements")
                    
                    if elements:
                        print("Element details:")
                        for i, element in enumerate(elements[:3]):  # Look at first 3 elements
                            try:
                                print(f"\nElement {i}:")
                                print(f"Text: {element.text}")
                                print(f"Displayed: {element.is_displayed()}")
                                print(f"Class: {element.get_attribute('class')}")
                                
                                if element.is_displayed():
                                    print("Attempting to click visible element...")
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                                    time.sleep(2)
                                    
                                    try:
                                        element.click()
                                        print("Click successful!")
                                        return True
                                    except:
                                        print("Regular click failed, trying JavaScript click...")
                                        driver.execute_script("arguments[0].click();", element)
                                        print("JavaScript click successful!")
                                        return True
                            except Exception as e:
                                print(f"Error with element {i}: {str(e)}")
                                continue
                    
                except Exception as e:
                    print(f"Error with selector {selector}: {str(e)}")
                    continue
        
        print("Could not find or click any ticker cells")
        return False
        
    except Exception as e:
        print(f"Error in click_first_ticker: {str(e)}")
        return False

try:
    # Navigate to follow page
    print("Navigating to the follow page...")
    driver.get(follow_page_url)
    time.sleep(3)
    
    # Collect wallet addresses
    wallet_addresses = collect_wallets()
    
    if not wallet_addresses:
        print("No wallet addresses found!")
        exit()
    
    # Try to click the first wallet
    if click_wallet(wallet_addresses[0]):
        # Try to click the first ticker in that wallet
        if click_first_ticker():
            print("Successfully completed the workflow!")
        else:
            print("Failed to click ticker")
    else:
        print("Failed to click wallet")

except Exception as e:
    print(f"Fatal error: {str(e)}")
finally:
    print("Script completed")