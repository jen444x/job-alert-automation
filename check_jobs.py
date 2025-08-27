from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv
import os
import time
from bs4 import BeautifulSoup
import requests
import random
import sys

# Load credentials
load_dotenv() # Reads your .env file and makes the values available via os.getenv()

# Global memory to avoid duplicate texts
recent_jobs = set()
driver = None

RECIPIENTS = [
    os.getenv("USER_KEY1"),    
    # os.getenv("USER_KEY2")    
]

# Twilio Notification
def send_text_notification(body):
    for recipient in RECIPIENTS:
        payload = {
            "token": os.getenv("PUSHOVER_API_TOKEN"),
            "user": recipient,
            "message": body,
        }

        try:
            response = requests.post("https://api.pushover.net/1/messages.json", data=payload)
            response.raise_for_status()
            print(f"Sent Pushover alert to {recipient}")
        except Exception as e:
            print(f"Failed to send Pushover alert to {recipient}:", e)

def set_up():
    global driver

    # Selenium config
    options = Options() # Creates an empty ChromeOptions object. This will store settings for Selenium
    options.binary_location = "/usr/bin/chromium-browser" # Tells Selenium where to find the browser executable
    options.add_argument("--headless")  # Runs the browser without a GUI window
    options.add_argument("--no-sandbox") # Disables the browser’s “sandbox” security feature
    options.add_argument("--disable-dev-shm-usage") # Prevents Chrome from using /dev/shm (shared memory)
    print("configured selenium\n")

    # Set up WebDriver
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    print("Set up webdrive\n")

def login():
    global driver

    # Go to login URL
    driver.get(os.getenv("PORTAL_URL"))
    print("Went to login URL\n")
    # driver.save_screenshot("after_load.png")

    # Login credentials
    USERNAME = os.getenv("PORTAL_USERNAME")
    PASSWORD = os.getenv("PORTAL_PASSWORD")

    # Wait for login prompt
    username_field = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, os.getenv("USERNAME_FIELD", "userId")))
    )
    password_field = driver.find_element(By.ID, os.getenv("PASSWORD_FIELD", "userPin"))

    # Fill in form to login
    username_field.send_keys(USERNAME)
    password_field.send_keys(PASSWORD + Keys.RETURN)

    # Save screenshot so we can verify login
    # driver.save_screenshot("login_check.png")

def find_job_table():
    global driver 

    # Wait for and click the Available Jobs tab
    try:
        available_tab = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.ID, "available-tab"))
            )
        available_tab.click()
    except Exception as e:
        print(f"Error clicking tab: {e}")  
        
    # Wait for job table 
    try: 
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, os.getenv("JOB_TABLE_ID", "parent-table-desktop-available")))
        )
    except Exception as e:
        print(f"Error finding job table: {e}")    

    # Get full page content 
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')   # Better for searching and reading 

    # return table
    job_table = soup.find("table", id=os.getenv("JOB_TABLE_ID", "parent-table-desktop-available")) 
    return job_table



def check_for_jobs(job_table):
    global recent_jobs, driver # Means we can update the outer variable

    print(job_table.get_text(separator=" | ", strip=True))

    # Get all table rows except the header
    rows = job_table.find_all("tr")[1:]  # skip the header
    if rows:
        current_jobs = set()
        new_jobs = []

        for row in rows:
            cells = row.find_all("td")
            details = [cell.get_text(strip=True) for cell in cells]
            job_text = " | ".join(details)
            print("Found job:", job_text)

            current_jobs.add(job_text)
            if job_text not in recent_jobs:
                new_jobs.append(job_text)
            else:
                print("Job already seen.")
                message = f"Job is still available:\n\n{job_text}"
                send_text_notification(message)

        # Update memory
        recent_jobs = current_jobs

        if new_jobs:
            message = "New job(s) posted:\n\n" + "\n\n".join(new_jobs)
            send_text_notification(message)
        else:
            print("No new jobs found. Skipping alert.")
    else:
        print(f"No jobs available at this time (empty table: {rows})")

        # Wait to see if a "no jobs available" message appears
        try:
            WebDriverWait(driver, 30).until(
                EC.text_to_be_present_in_element(
                    (By.CLASS_NAME, "pds-message-info"), 
                    "no jobs available"
                )
            )
            print("No jobs available (confirmed from message box).")
        except TimeoutException:
            message = "Error: Empty table but no 'no jobs available' message found."
            print(message)
            send_text_notification(message)



if __name__ == "__main__":
    table_not_found_count = 0
    try:
        while True:
            set_up()
            login()

            job_table = find_job_table()
            if job_table:
                # reset counter
                table_not_found_count = 0
                check_for_jobs(job_table)
            else:
                table_not_found_count += 1
                print("Couldn't find table, skipping this cycle")
                
                if table_not_found_count >= 3:
                    send_text_notification("Bot failed 3 times in a row, shutting down")
                    sys.exit("Could not find table")
            
            print("Waiting 2.3-3.5 minutes...\n")
            # wait_time = random.randint(150,210) # 2.5-3.5 minutes
            wait_time = random.randint(210,270) # 3.5-4.5 minutes
            time.sleep(wait_time)
    except KeyboardInterrupt:
        print("🛑 Stopping bot...")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        send_text_notification(f"💥 Job bot crashed: {e}")
    finally:
        if driver:
            driver.quit()
            print("🧹 Cleaned up browser on exit")