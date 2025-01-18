from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time

# URL of the follow page
follow_page_url = "https://gmgn.ai/follow/8gcLcglg?chain=sol&tab=follow"

# Configure Chrome to connect to an already open session
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=chrome_options)

def scroll_and_collect_wallets():
    wallet_selector = "div[data-row-key]"
    scrollable_container_selector = "div.g-table-tbody-virtual-holder"
    loaded_wallets = set()
    max_scroll_attempts = 50
    scroll_attempts = 0
    previous_wallet_count = 0

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

            # Scroll the container
            driver.execute_script("arguments[0].scrollTop += arguments[0].offsetHeight;", scrollable_container)
            time.sleep(1.8)  # Reduced sleep time by 10% to make scrolling faster

            # Check if new wallets have been loaded
            if len(loaded_wallets) == previous_wallet_count:  # No new wallets found
                print("No new wallets detected. Ending scrolling.")
                break

            previous_wallet_count = len(loaded_wallets)
            scroll_attempts += 1

    except Exception as e:
        print(f"Error during scrolling: {e}")

    return list(loaded_wallets)

try:
    print("Navigating to the follow page...")
    driver.get(follow_page_url)
    time.sleep(5)

    print("Starting wallet collection...")
    wallets = scroll_and_collect_wallets()

    print(f"Collected a total of {len(wallets)} wallets:")
    for wallet in wallets:
        print(wallet)

except Exception as e:
    print(f"Error: {e}")
finally:
    driver.quit()