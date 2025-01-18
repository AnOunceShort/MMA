from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

class SolscanScraper:
    def __init__(self):
        self.driver = webdriver.Chrome()  # or whatever browser you prefer
        self.base_url = "https://solscan.io"
    
    def search_token(self, token_address):
        try:
            # Navigate directly to the token page
            token_url = f"{self.base_url}/token/{token_address}"
            print(f"Navigating to: {token_url}")
            self.driver.get(token_url)
            
            print("Waiting for page to load...")
            time.sleep(5)
            
            # Find and click the Transactions tab
            print("Looking for Transactions tab...")
            transactions_tab = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Transactions']"))
            )
            time.sleep(2)
            transactions_tab.click()
            print("Clicked Transactions tab")
            
            time.sleep(3)
            
            # Now try to scrape the transaction values
            return self.get_transactions()
            
        except Exception as e:
            print(f"Error during search: {e}")
            return []
    
    def get_transactions(self, num_pages=5):  # Default to 5 pages, can be changed
        try:
            all_values = []
            current_page = 1
            
            while current_page <= num_pages:
                print(f"\nScraping page {current_page}...")
                time.sleep(3)
                
                # Look for elements in the first column only (Value SOL)
                selector = "//td[contains(@class, 'h-12')]//div[contains(@class, 'not-italic')]"
                elements = self.driver.find_elements(By.XPATH, selector)
                
                page_values = []
                for element in elements:
                    try:
                        value = element.text.strip()
                        if value and '.' in value:  # Check if it's a decimal number
                            num = float(value)
                            if num > 0:  # Only include positive numbers
                                page_values.append(f"{num:.6f}")
                    except ValueError:
                        continue
                
                if page_values:
                    print(f"Found {len(page_values)} values on page {current_page}:")
                    for value in page_values:
                        print(value)
                    all_values.extend(page_values)
                
                # Try to click next page button
                try:
                    print("Looking for next page button...")
                    # Find the last button (which should be the next page button)
                    next_button = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "(//button[contains(@class, 'inline-flex')])[last()]"))
                    )
                    
                    print("Found next button, attempting to click...")
                    
                    # Scroll the button into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(1)
                    
                    # Print button state for debugging
                    print(f"Button classes: {next_button.get_attribute('class')}")
                    print(f"Button is displayed: {next_button.is_displayed()}")
                    print(f"Button is enabled: {next_button.is_enabled()}")
                    
                    # Try multiple click methods
                    try:
                        next_button.click()
                    except:
                        try:
                            self.driver.execute_script("arguments[0].click();", next_button)
                        except:
                            ActionChains(self.driver).move_to_element(next_button).click().perform()
                    
                    print("Clicked next page")
                    current_page += 1
                    time.sleep(2)  # Wait for new page to load
                    
                except Exception as e:
                    print(f"\nError with next page button: {str(e)}")
                    break
            
            print(f"\nTotal values scraped across {current_page} pages: {len(all_values)}")
            return all_values
            
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def find_specific_trade(self, amount):
        # We'll implement trade searching logic here
        pass

def main():
    try:
        scraper = SolscanScraper()
        token_address = input("Enter the token address: ")
        
        # Ask how many pages to scrape
        num_pages = int(input("How many pages to scrape? (default is 5): ") or "5")
        values = scraper.search_token(token_address)
        values = scraper.get_transactions(num_pages)
        
        input("\nPress Enter to close the browser...")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'scraper' in locals():
            scraper.driver.quit()

if __name__ == "__main__":
    main()
