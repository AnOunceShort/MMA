from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time

# URL of the follow page
follow_page_url = "https://gmgn.ai/follow/8gcLcglg?chain=sol&tab=follow"

# Configure Chrome to connect to an already open session
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=chrome_options)

# Apply stealth settings to avoid detection
stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True)

def safe_find(element, selector):
    try:
        return element.find_element(By.CSS_SELECTOR, selector).text.strip()
    except NoSuchElementException:
        return "N/A"

def scroll_to_load_rows():
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)

def scrape_wallet(wallet_address, max_tickers=75):
    print(f"Scraping data for wallet: {wallet_address}")
    print("Waiting for the Recent PnL table rows to load...")
    pnl_row_selector = "tbody.g-table-tbody tr.g-table-row.g-table-row-level-0.cursor-pointer"
    WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, pnl_row_selector))
    )

    scroll_to_load_rows()

    recent_pnl_rows = driver.find_elements(By.CSS_SELECTOR, pnl_row_selector)
    total_rows = len(recent_pnl_rows)
    print(f"Found {total_rows} rows in the wallet. Processing up to {min(total_rows, max_tickers)} rows.")

    for i, row in enumerate(recent_pnl_rows[:max_tickers]):
        try:
            print(f"Scraping data from PnL row {i + 1}...")
            
            ticker_name = safe_find(row, "div.css-101kej7")
            unrealized_value = safe_find(row, "td.g-table-cell div.css-1ww4ost p.chakra-text.css-1nwuo4i")
            realized_value = safe_find(row, "td.g-table-cell div.css-1wknec8 div.css-qgi3xm")
            total_profit_value = safe_find(row, "td.g-table-cell div.css-vh0o7e div.css-69pi9u")
            balance_value = safe_find(row, "td.g-table-cell div.css-vh0o7e div.css-69pi9u")
            position_value = safe_find(row, "td.g-table-cell div.css-megq0p")
            bought_avg_value = safe_find(row, "td.g-table-cell div.css-1tstt9j p.chakra-text.css-kr52r7")
            sold_avg_value = safe_find(row, "td.g-table-cell div.css-1ww4ost p.chakra-text.css-kr52r7")
            txs_elements = row.find_elements(By.CSS_SELECTOR, "td.g-table-cell div.css-1a3soj1 div.css-k008qs")
            txs_value = f"{txs_elements[0].text.strip()}/{txs_elements[1].text.strip()}" if len(txs_elements) == 2 else "N/A"

            if ticker_name == "N/A" and unrealized_value == "N/A" and realized_value == "N/A":
                print("Encountered an empty or invalid row. Stopping further scraping.")
                break

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
            print("--------")

        except Exception as e:
            print(f"Error scraping row {i + 1}: {e}")
            continue

try:
    print("Navigating to the follow page...")
    driver.get(follow_page_url)
    time.sleep(10)

    wallet_selector = "div[data-row-key]"
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, wallet_selector)))

    wallets = driver.find_elements(By.CSS_SELECTOR, wallet_selector)

    for idx in range(len(wallets[:6])):  # Process the first six wallets
        try:
            print(f"Accessing wallet {idx + 1}...")
            wallet_address = wallets[idx].get_attribute("data-row-key")  # Extract wallet address
            wallets[idx].click()
            time.sleep(5)
            scrape_wallet(wallet_address)

            print("Returning to follow page...")
            driver.back()
            time.sleep(5)

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wallet_selector))
            )
            wallets = driver.find_elements(By.CSS_SELECTOR, wallet_selector)  # Refresh wallet list

        except (StaleElementReferenceException, TimeoutException):
            print("Stale element reference or timeout. Refreshing page and retrying...")
            driver.refresh()
            time.sleep(5)
            wallets = driver.find_elements(By.CSS_SELECTOR, wallet_selector)
            continue
        except Exception as e:
            print(f"Error accessing wallet {idx + 1}: {e}")
            continue

except Exception as e:
    print(f"Error: {e}")
finally:
    driver.quit()