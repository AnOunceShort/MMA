from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import csv
from datetime import datetime

class SolscanScraper:
    def __init__(self):
        self.driver = webdriver.Chrome()  # or whatever browser you prefer
        self.base_url = "https://solscan.io"
        self.current_token_address = None
    
    def search_token(self, token_address):
        try:
            self.current_token_address = token_address
            token_url = f"{self.base_url}/token/{token_address}"
            print(f"Navigating to: {token_url}")
            self.driver.get(token_url)
            
            print("Waiting for page to load...")
            time.sleep(5)
            
            # Updated Transactions tab handling using exact properties from the UI
            print("Looking for Transactions tab...")
            try:
                # Using multiple selectors based on the exact properties we can see
                selectors = [
                    "//button[@role='tab' and contains(text(), 'Transactions')]",
                    "//button[contains(@class, 'ring-offset-background') and contains(text(), 'Transactions')]",
                    "//button[contains(@style, 'font: 12px Roboto') and contains(text(), 'Transactions')]"
                ]
                
                transactions_tab = None
                for selector in selectors:
                    try:
                        transactions_tab = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        if transactions_tab:
                            break
                    except:
                        continue
                
                if not transactions_tab:
                    raise Exception("Could not find Transactions tab")
                
                # Scroll into view with precise offset
                self.driver.execute_script("""
                    arguments[0].scrollIntoView({block: 'center'});
                    window.scrollBy(0, -100);
                """, transactions_tab)
                time.sleep(2)
                
                print("Attempting to click Transactions tab...")
                # Try multiple click methods with verification
                try:
                    transactions_tab.click()
                except:
                    try:
                        self.driver.execute_script("""
                            arguments[0].click();
                            arguments[0].dispatchEvent(new Event('click', { bubbles: true }));
                        """, transactions_tab)
                    except:
                        self.driver.execute_script("""
                            arguments[0].focus();
                            arguments[0].click();
                        """, transactions_tab)
                
                # Verify the click worked by checking if the tab is selected
                time.sleep(2)
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'transaction-row')]"))
                    )
                    print("Successfully clicked Transactions tab")
                except:
                    print("Warning: Could not verify if Transactions tab was clicked successfully")
                
                time.sleep(3)
                
                # Add this after the Transactions tab click is verified
                try:
                    # Find the dropdown trigger button
                    print("Looking for dropdown...")
                    dropdown = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//button[@role='combobox']"))
                    )
                    
                    # Scroll to dropdown
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown)
                    time.sleep(1)
                    
                    print("Attempting to click dropdown...")
                    # Click using multiple methods
                    try:
                        dropdown.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", dropdown)
                    
                    # Wait for the listbox to appear
                    print("Waiting for options to load...")
                    time.sleep(2)
                    
                    # Look for the options container first
                    listbox = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@role='listbox']"))
                    )
                    
                    # Try different page size options in order of preference
                    page_sizes = ['100', '50', '40', '20']
                    selected_size = None
                    
                    for size in page_sizes:
                        try:
                            print(f"Looking for {size} option...")
                            option = WebDriverWait(listbox, 2).until(
                                EC.presence_of_element_located((By.XPATH, f".//div[@role='option'][contains(., '{size}')]"))
                            )
                            
                            # Scroll the option into view and click it
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option)
                            time.sleep(1)
                            
                            print(f"Clicking {size} option...")
                            try:
                                option.click()
                                selected_size = size
                                break
                            except:
                                self.driver.execute_script("arguments[0].click();", option)
                                selected_size = size
                                break
                                
                        except Exception as e:
                            print(f"Option {size} not available, trying next size...")
                            continue
                    
                    if selected_size:
                        print(f"Selected {selected_size} items per page")
                    else:
                        print("Could not set custom page size, using default")
                    time.sleep(3)  # Wait for page to update
                    
                except Exception as e:
                    print(f"Could not set items per page: {e}")
                    print(f"Detailed error: {str(e)}")
                    print("Continuing with default page size...")
                
            except Exception as e:
                print(f"Error with Transactions tab: {e}")
                print("Attempting alternative method...")
                try:
                    # Direct JavaScript navigation attempt
                    self.driver.execute_script("""
                        document.querySelector('button[role="tab"]:not([disabled])').click();
                    """)
                    time.sleep(3)
                except Exception as e:
                    print(f"Alternative method failed: {e}")
                    return []
            
            return []  # We'll call get_transactions directly from main()
            
        except Exception as e:
            print(f"Error during search: {e}")
            return []
    
    def get_transactions(self, num_pages=5):
        try:
            all_values = []
            current_page = 1
            
            while current_page <= num_pages:
                print(f"\nScraping page {current_page}...")
                time.sleep(3)
                
                # Updated selector to catch all transaction values
                selectors = [
                    "//td[contains(@class, 'h-12')]//div[contains(@class, 'not-italic')]",
                    "//div[contains(@class, 'transaction-row')]//div[contains(@class, 'not-italic')]",
                    "//div[contains(@class, 'amount')]//div[contains(@class, 'not-italic')]"
                ]
                
                page_values = []
                for selector in selectors:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        try:
                            value = element.text.strip()
                            if value and '.' in value:
                                num = float(value)
                                if num > 0:  # Only include positive numbers
                                    page_values.append(f"{num:.6f}")
                        except ValueError:
                            continue
                
                if page_values:
                    print(f"Found {len(page_values)} values on page {current_page}")
                    all_values.extend(page_values)
                    
                    # Try to click next page button using the working implementation from solv1.py
                    try:
                        print("Looking for next page button...")
                        next_button = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "(//button[contains(@class, 'inline-flex')])[last()]"))
                        )
                        
                        print("Found next button, attempting to click...")
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                        time.sleep(1)
                        
                        next_button.click()
                        print("Clicked next page")
                        current_page += 1
                        time.sleep(2)
                        
                    except Exception as e:
                        print(f"\nError with next page button: {str(e)}")
                        break
                else:
                    print(f"No values found on page {current_page}, might have reached the end")
                    break
            
            print(f"\nTotal values scraped across {current_page-1} pages: {len(all_values)}")
            return all_values
            
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def find_specific_trade(self, amount):
        # We'll implement trade searching logic here
        pass

    def export_to_csv(self, values, token_address):
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"solscan_values_{token_address[:8]}_{timestamp}.csv"
            
            # Write values to CSV
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Value (SOL)'])  # Header
                for value in values:
                    writer.writerow([value])
            
            print(f"\nData exported to {filename}")
            
        except Exception as e:
            print(f"Error exporting to CSV: {e}")

def main():
    try:
        scraper = SolscanScraper()
        token_address = input("Enter the token address: ")
        
        # Ask how many pages to scrape
        num_pages = int(input("How many pages to scrape? (default is 5): ") or "5")
        
        # First navigate to the token and set up the page
        scraper.search_token(token_address)
        
        # Then scrape the transactions
        values = scraper.get_transactions(num_pages)
        
        # Export to CSV
        if values:
            scraper.export_to_csv(values, token_address)
        
        input("\nPress Enter to close the browser...")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'scraper' in locals():
            scraper.driver.quit()

if __name__ == "__main__":
    main()
