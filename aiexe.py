import webbrowser
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


url = "https://mail.google.com/mail/u/0/#search/info%40easygoshuttle.com.au"
webbrowser.open(url)

# Wait for the user to log in manually
time.sleep(30)  # Adjust the sleep time as needed to allow for manual login

# Set up Selenium WebDriver
chrome_options = Options()
chrome_options.add_argument("--start-maximized")

chrome_driver_path = 'C:/Users/sungk/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe'  

service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

# Connect to the already opened Gmail tab
driver.get("https://mail.google.com/mail/u/0/#search/info%40easygoshuttle.com.au")

# Wait for the Gmail interface to load
WebDriverWait(driver, 300).until(EC.presence_of_element_located((By.XPATH, "//div[@role='navigation']")))

# Search for the 'Re-reminder' label
search_box = driver.find_element(By.XPATH, "//input[@aria-label='Search mail']")
search_box.send_keys("label:Re-reminder")
search_box.send_keys(Keys.RETURN)

# Wait for the search results to load
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@role='main']")))

# Select all emails in the 'Re-reminder' label
select_all_checkbox = driver.find_element(By.XPATH, "//div[@aria-label='Select']")
select_all_checkbox.click()

time.sleep(2)

# Move selected emails to the 'completion' folder
move_to_button = driver.find_element(By.XPATH, "//div[@aria-label='Move to']")
move_to_button.click()

WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@role='menu']")))

completion_folder = driver.find_element(By.XPATH, "//div[@title='completion']")
completion_folder.click()

time.sleep(2)

driver.quit()