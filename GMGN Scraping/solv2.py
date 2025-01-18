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
            
            # Click Transactions tab
            print("Looking for Transactions tab...")
            transactions_tab = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[normalize-space()='Transactions']"))
            )
            self.driver.execute_script("arguments[0].click();", transactions_tab)
            print("Clicked Transactions tab")
            time.sleep(3)
            
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
                
                # Now find the 100 option within the listbox
                print("Looking for 100 option...")
                option_100 = WebDriverWait(listbox, 5).until(
                    EC.presence_of_element_located((By.XPATH, ".//div[@role='option'][contains(., '100')]"))
                )
                
                # Scroll the option into view and click it
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option_100)
                time.sleep(1)
                
                print("Clicking 100 option...")
                try:
                    option_100.click()
                except:
                    self.driver.execute_script("arguments[0].click();", option_100)
                
                print("Selected 100 items per page")
                time.sleep(3)  # Wait for page to update
                
            except Exception as e:
                print(f"Could not set items per page: {e}")
                print(f"Detailed error: {str(e)}")
                print("Continuing with default page size...")
            
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
                
                # Immediately grab the data without waiting
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
                
                # After scraping, navigate to next page quickly but safely
                try:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "(//button[contains(@class, 'inline-flex')])[last()]"))
                    )
                    
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(0.5)
                    
                    next_button.click()
                    current_page += 1
                    time.sleep(1.2)
                    
                except Exception as e:
                    print(f"\nError with next page button: {str(e)}")
                    break
            
            print(f"\nTotal values scraped across {current_page-1} pages: {len(all_values)}")
            
            # Export to CSV
            if all_values:
                self.export_to_csv(all_values, self.current_token_address)
            
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
        values = scraper.search_token(token_address)
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
