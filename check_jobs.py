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
import random

# Load credentials
load_dotenv() # Reads your .env file and makes the values available via os.getenv()

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

# Global memory to avoid duplicate texts
last_job_seen = None
driver = None

def check_for_jobs():
    global last_job_seen, driver # Means we can update the outer variable

    try:
        print("Logging in\n")
        # Login credentials
        USERNAME = os.getenv("PORTAL_USERNAME")
        PASSWORD = os.getenv("PORTAL_PASSWORD")

        # Selenium config
        options = Options() # Creates an empty ChromeOptions object. This will store settings for Selenium
        options.binary_location = "/usr/bin/chromium-browser" # Tells Selenium where to find the browser executable
        options.add_argument("--headless")  # Runs the browser without a GUI window
        options.add_argument("--no-sandbox") # Disables the browser’s “sandbox” security feature
        options.add_argument("--disable-dev-shm-usage") # Prevents Chrome from using /dev/shm (shared memory)
        print("configed selenium\n")

        # Set up WebDriver
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        print("Set up webdrive\n")

        # Go to your login URL
        driver.get(os.getenv("PORTAL_URL"))
        print("Went to login URL\n")
        # driver.save_screenshot("after_load.png")

        ## Login
        # Wait for login prompt
        username_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, os.getenv("USERNAME_FIELD", "userId")))
        )
        password_field = driver.find_element(By.ID, os.getenv("PASSWORD_FIELD", "userPin"))

        # Fill in form to login
        username_field.send_keys(USERNAME)
        password_field.send_keys(PASSWORD + Keys.RETURN)

        # Wait up to 30 seconds for dashboard to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "job-search"))  
        )

        # Save screenshot so we can verify login
        # driver.save_screenshot("login_check.png")

        try:
            # Wait for and click the Available Jobs tab
            available_tab = WebDriverWait(driver, 15).until(
                # wait for class within available jobs section
                EC.element_to_be_clickable((By.ID, "available-tab"))
            )
            available_tab.click()
        except Exception as e:
            print(f"Error clicking tab: {e}")     

        # Wait a bit for content to load
        time.sleep(5)       
        
        # driver.save_screenshot("before_scraping.png")

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
                # try to get new html and check 
                time.sleep(3)    

                # Get fresh HTML
                html1 = driver.page_source
                soup1 = BeautifulSoup(html, 'html.parser')

                no_jobs_msg = soup1.find("div", class_="pds-message-info")
                
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

if __name__ == "__main__":
    try:
        while True:
            check_for_jobs()
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