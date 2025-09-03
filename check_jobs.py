from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv
import os
import time
from bs4 import BeautifulSoup
import requests
import random
import sys

# Exception classes
class JobBotError(Exception):
    """Base exception for all job bot errors"""
    pass

class TemporaryError(JobBotError):
    """Error that might be fixed by retrying"""
    pass

class PermanentError(JobBotError):
    """Error that requires human intervention"""
    pass

class TooManyFailuresError(PermanentError):
    """Escalated error after too many consecutive failures"""
    pass


driver = None  # Initialize driver variable

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

def create_driver():
    global driver

    # Clean up any existing driver first
    destroy_driver()    

    # Selenium config
    options = Options() # Creates an empty ChromeOptions object. This will store settings for Selenium
    options.binary_location = "/usr/bin/chromium-browser" # Tells Selenium where to find the browser executable
    options.add_argument("--headless")  # Runs the browser without a GUI window
    options.add_argument("--no-sandbox") # Disables the browser’s “sandbox” security feature
    options.add_argument("--disable-dev-shm-usage") # Prevents Chrome from using /dev/shm (shared memory)
    print("configured selenium\n")
        
    try:        
        # Set up WebDriver
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        print("Set up webdrive\n")
    except Exception as e:
        raise TemporaryError(f"Failed to create driver: {e}")

def destroy_driver():
    global driver

    # Clean up current driver if alive
    try:
        driver.current_url # If driver is dead, will fail
        driver.quit()
    except:
        pass  
    finally:
        driver = None

def login():
    global driver

    # Get necessary env vars
    USERNAME = os.getenv("PORTAL_USERNAME")
    PASSWORD = os.getenv("PORTAL_PASSWORD")
    PORTAL_URL = os.getenv("PORTAL_URL")

    # Make sure I have them
    if not USERNAME or not PASSWORD or not PORTAL_URL:
        raise PermanentError("Missing required environment variables (PORTAL_USERNAME, PORTAL_PASSWORD, or PORTAL_URL)")

    try: 
        # Go to login URL
        driver.get(PORTAL_URL)
        print("Went to login URL\n")
        # driver.save_screenshot("after_load.png")

        # Wait for login form elements
        username_field = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, os.getenv("USERNAME_FIELD", "userId")))
        )
        password_field = driver.find_element(By.ID, os.getenv("PASSWORD_FIELD", "userPin"))

        # Fill in form to login
        username_field.send_keys(USERNAME)
        password_field.send_keys(PASSWORD + Keys.RETURN)
        # Save screenshot so we can verify login
        # driver.save_screenshot("login_check.png")

        # Wait for successful login - job-search element should appear
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "job-search"))
        )
        print("Login successful!")
        
    except TimeoutException as e:
        # This could be slow network OR bad credentials
        raise TemporaryError(f"Timeout exception during login. Error: {e}")
    
    except NoSuchElementException as e:
        # Login form elements not found - website might have changed
        raise TemporaryError(f"Login form elements not found. Error: {e}") 
    
    except Exception as e:
        # Any other selenium error - treat as temporary
        raise TemporaryError(f"Unexpected error during login. Error: {e}")
    
def get_jobs(max_refreshes):
    global driver 

    for attempt in range(max_refreshes):
        try:
            # Wait for and click the Available Jobs tab
            try:
                available_tab = WebDriverWait(driver, 30).until(
                        EC.element_to_be_clickable((By.ID, "available-tab"))
                    )
                available_tab.click()
            except Exception as e:
                print(f"Error clicking Available Jobs tab: {e}")  
                raise Exception(f"Failed to click available tab: {e}")
                
            # Wait for job table 
            try: 
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, os.getenv("JOB_TABLE_ID", "parent-table-desktop-available")))
                )
            except Exception as e:
                print(f"Error finding job table: {e}")  
                raise Exception(f"Failed to find job table: {e}")  

            # Get full page content 
            try:
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
            except Exception as e:
                print(f"Failed to get/parse page: {e}")

            # Get table
            try:
                job_table = soup.find("table", id=os.getenv("JOB_TABLE_ID", "parent-table-desktop-available"))
                if not job_table:
                    raise Exception("Job table not found in page")
            except Exception as e:
                raise Exception(f"Failed to parse job table: {e}")
 

            # Get all table rows except the header
            # rows = job_table.find_all("tr")[1:]  # skip the header
            rows = job_table.find_all("tr")
            jobs = set()
            
            if rows:
                for i, row in enumerate(rows):
                    print(row)
                    if i == 0:  # Skip header row
                        continue
                    cells = row.find_all("td")
                    details = [cell.get_text(strip=True) for cell in cells]
                    job = " | ".join(details)
                    jobs.add(job)
            
            return jobs
        except Exception as e:
            if attempt == max_refreshes - 1:    # Last attempt
                raise TooManyFailuresError(f"Get jobs failed {max_refreshes} times. Last error: {e}")
            
            print(f"get_jobs attempt {attempt + 1} failed, refreshing page...")
            driver.refresh()
            time.sleep(3)  # Wait after refresh

def confirm_no_jobs():
    global driver

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
        # Message didn't appear - something might be wrong
        message = "Warning: Empty job table but no 'no jobs available' message found"
        print(message)
        send_text_notification(message)
        
    except Exception as e:
        # Other error checking for the message
        message = f"Error confirming no jobs: {e}"
        print(message) 
        send_text_notification(message)

def notify(current_jobs, old_jobs):
    # Find new jobs
    new_jobs = current_jobs - old_jobs
    if new_jobs:
        message = "New job(s) posted:\n\n" + "\n\n".join(new_jobs)
        send_text_notification(message)
        print(message)
    
    # Find jobs still available (in both current and old)
    still_available = current_jobs & old_jobs
    if (still_available):
        message = "Job(s) still available:\n\n" + "\n\n".join(still_available)
        send_text_notification(message)
        print(message)

def single_job_check(last_jobs_found, max_failures):
    """
    Try one job check, retry up to n times if it fails
    """ 
    for attempt in range(max_failures):
        try:
            login()
            max_refreshes = 3
            new_jobs = get_jobs(max_refreshes)
            
            if new_jobs:    # If jobs, notify
                notify(new_jobs, last_jobs_found) 
            else:   # If no jobs, confirm
                print(f"No jobs available at this time (empty table: {new_jobs})")
                confirm_no_jobs()

            # Update memory
            return set(new_jobs) # Success! These become the "last seen" for next time
        except Exception as e:
            if attempt == max_failures - 1:  # Last attempt
                raise TooManyFailuresError(f"Job check failed {max_failures} times. Last error: {e}")
            
            print(f"Attempt {attempt + 1} failed: {e}")
            print("Retrying...")
            time.sleep(15)  # Short wait between retries

def run_session(checks):
    """
    Try one session, retry up to 3 times if it fails
    """ 
    last_jobs_found = set()  # Fresh memory for this session
    max_failures = 2

    for i in range(checks):  # Check jobs 10 times
        print(f"\n🔍 Starting job check {i+1}/{checks}")
        last_jobs_found = single_job_check(last_jobs_found, max_failures)  # Handles 3-error retry logic
        print(f"💤 Waiting before next check...")
        time.sleep(120)  # 2 minutes between checks

def run_jobbot(max_failures):
    """
    Sets up and creates a driver session which will run x times
    Keeps track of failures
    Once reaches max_failures, will terminate
    """ 
    checks = 10

    for attempt in range(max_failures):
        try:
            create_driver()
            run_session(checks) # Do 'checks' job bot checks in one session
            print(f"Completed {checks} runs. Getting fresh driver...")
            destroy_driver()  # Fresh start
            return # Success - exit the function
        except TemporaryError as e:
            destroy_driver()  # Clean up failed driver

            if attempt == max_failures - 1:  # Last attempt
                raise PermanentError(f"Job bot failed 3 times: {e}")
            print(f"Attempt {attempt+1} failed, trying again...")


if __name__ == "__main__":
    try:
        max_failures = 3
        while True:
            run_jobbot(max_failures)    
    except PermanentError as e:
            print(f"Bot stopping permanently: {e}")
            send_text_notification(f"Job bot needs help: {e}")
    except KeyboardInterrupt:
        print("Manually stopping bot...")
    except Exception as e:
        print(f"Fatal error: {e}")
        send_text_notification(f"Job bot crashed: {e}")
    finally:
        if 'driver' in globals() and driver:
            driver.quit()
            print("Browser cleaned up")

# Make sure i have a driver when starting
# When fialing 3 times save all error messages then send if failed 3 times
# maybe a function that will run things x amount of times instead of having to rewrite logic
# yes do that so i can do refreshes for things like waiting fro clickable button to show just refresh instead of logging in again 