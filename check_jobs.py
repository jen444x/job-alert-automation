from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os
import time
from bs4 import BeautifulSoup
import requests

# Load credentials
load_dotenv() # Reads your .env file and makes the values available via os.getenv()

# Twilio Notification
def send_text_notification(body):
    payload = {
        "token": os.getenv("PUSHOVER_API_TOKEN"),
        "user": os.getenv("NOTIFICATION_USER_KEY"),
        "message": body,
    }

    try:
        response = requests.post("https://api.pushover.net/1/messages.json", data=payload)
        response.raise_for_status()
        print("Sent Pushover alert")
    except Exception as e:
        print("Failed to send Pushover alert:", e)

# Global memory to avoid duplicate texts
# Remembers the most recent job alert you sent, So you don’t keep texting the same job every 3 minutes
last_job_seen = None

def check_for_jobs():
    global last_job_seen # Means we can update the outer variable
    driver = None   # Will control the browser

    try:
        # Login credentials
        USERNAME = os.getenv("PORTAL_USERNAME")
        PASSWORD = os.getenv("PORTAL_PASSWORD")

        # Selenium config
        options = Options() # Creates an empty ChromeOptions object. This will store settings for Selenium
        options.binary_location = "/usr/bin/chromium-browser" # Tells Selenium where to find the browser executable
        options.add_argument("--headless")  # Runs the browser without a GUI window
        options.add_argument("--no-sandbox") # Disables the browser’s “sandbox” security feature
        options.add_argument("--disable-dev-shm-usage") # Prevents Chrome from using /dev/shm (shared memory)

        # Set up WebDriver
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    
        # Go to your login URL
        driver.get(os.getenv("PORTAL_URL"))

        driver.save_screenshot("after_load.png")

        # Login
        time.sleep(2) # Wait 2 sec. to give the browser time to load all HTML + JS
        # Fill in form to login
        driver.find_element(By.ID, os.getenv("USERNAME_FIELD", "userId")).send_keys(USERNAME)
        driver.find_element(By.ID, os.getenv("PASSWORD_FIELD", "userPin")).send_keys(PASSWORD + Keys.RETURN)

        # Wait up to 30 seconds for dashboard to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "job-search-tab"))  
        )

        # Save screenshot so we can verify login
        driver.save_screenshot("login_check.png")
        
        # Wait until the job table is present
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "parent-table-desktop-available"))
        )

        # Get the full page content
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')   # Better for searching and reading

        # Find the job table
        job_table = soup.find("table", id=os.getenv("JOB_TABLE_ID", "parent-table-desktop-available"))

        print(job_table.get_text(separator=" | ", strip=True))

        # Get all table rows except the header
        rows = job_table.find_all("tr")[1:]  # skip the header
        print(rows)

        if not rows:
            print("No jobs available at this time (empty table.)")
            
            # Double check there's no jobs
            no_jobs_msg = soup.find("div", class_="pds-message-info")
            if no_jobs_msg and "no jobs available" in no_jobs_msg.text.lower():
                print("No jobs available (confirmed from message box).")
            else:
                print("Error: There are jobs available.")
        else:
            new_jobs = []

            for row in rows:
                cells = row.find_all("td")
                details = [cell.get_text(strip=True) for cell in cells]
                job_text = " | ".join(details)
                print("Found job:", job_text)

                if job_text != last_job_seen:
                    new_jobs.append(job_text)
                else:
                    print("Job already seen. No alert sent.")
                    break  # We already alerted on this job before; no need to continue

            if new_jobs:
                message = "New job(s) posted:\n\n" + "\n\n".join(new_jobs)
                send_text_notification(message)
                last_job_seen = new_jobs[0]  # Update to the newest job
            else:
                print("No new jobs found. Skipping alert.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if driver:
            driver.quit()

while True:
    check_for_jobs()
    print("Waiting 3 minutes...\n")
    time.sleep(180)
