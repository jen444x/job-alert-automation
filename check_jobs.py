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
import datetime
import pytz

# Initialize driver variable
driver = None  

# Load credentials
load_dotenv() 

# Timezone configuration
TIMEZONE = os.getenv("TIMEZONE", "America/Los_Angeles")

"""
Exception classes
"""
class JobBotError(Exception):
    """Base exception for all job bot errors"""
    pass

class TemporaryError(JobBotError):
    """Error that might be fixed by retrying"""
    pass

class TooManyFailuresError(TemporaryError):
    """this level exhausted, escalate to next level"""
    pass

class PermanentError(JobBotError):
    """Error that requires human intervention"""
    pass

"""
Handle drivers
"""
def create_driver():
    global driver

    # Clean up any existing driver first
    destroy_driver()    

    # Selenium config
    options = Options() # Creates an empty ChromeOptions object. This will store settings for Selenium
    options.add_argument("--headless=new")  # Runs the browser without a GUI window
    options.add_argument("--no-sandbox") # Disables the browser’s “sandbox” security feature
    options.add_argument("--disable-dev-shm-usage") # Prevents Chrome from using /dev/shm (shared memory)
    print("configured selenium\n")
        
    try:        
        # Set up WebDriver
        driver = webdriver.Chrome(options=options)
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

"""
Helper function
"""
def retry_on_failure(action_func, max_retries=2, delay=15, on_failure="refresh"):
    """Try an action with retry on failure"""
    for attempt in range(max_retries):
        try:
            return action_func()    # Return on success
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                raise TooManyFailuresError(f"Action failed {max_retries} times. Last error: {e}")
            
            print(f"Attempt {attempt + 1} failed during {action_func.__name__} function, refreshing page...")
            print(f"{e}")

            if on_failure == "refresh":
                if driver:
                    driver.refresh()
            elif on_failure == "destroy_driver":
                destroy_driver()  # Clean up broken driver so it can be recreated

            time.sleep(delay)

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

def login_impl():
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
    
def login():
    return retry_on_failure(login_impl)

"""
If no jobs are found, check for no jobs available message
"""
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

"""
Send message to users with job updates
"""
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

def get_jobs_impl():
    global driver 

    # refresh page before check
    driver.refresh()
    
    # Wait for and click the Available Jobs tab
    try:
        available_tab = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.ID, "available-tab"))
            )
        available_tab.click()
    except Exception as e:
        raise TemporaryError(f"Failed to click available tab: {e}")
        
    # Wait for job table 
    try: 
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, os.getenv("JOB_TABLE_ID", "parent-table-desktop-available")))
        )
    except Exception as e:
        raise TemporaryError(f"Failed to find job table: {e}")  

    # Get full page content 
    try:
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        raise TemporaryError(f"Failed to get/parse page: {e}")

    # Get table
    try:
        job_table = soup.find("table", id=os.getenv("JOB_TABLE_ID", "parent-table-desktop-available"))
        if not job_table:
            raise Exception("Job table not found in page")
    except Exception as e:
        raise TemporaryError(f"Failed to parse job table: {e}")
    
    # Print table for debugging 
    print(job_table.get_text(separator=" | ", strip=True))

    # Get all table rows except the header
    rows = job_table.find_all("tr")[1:]  # skip the header
    print(rows)
    jobs = set()
    
    if rows:
        for row in rows:
            cells = row.find_all("td")
            details = [cell.get_text(strip=True) for cell in cells]
            job = " | ".join(details)
            print("Found job:", job)
            jobs.add(job)
    
    return jobs

"""Get jobs with automatic page refresh retry"""
def get_jobs():
    return retry_on_failure(get_jobs_impl)

"""
Find jobs on current page 
"""
def single_job_check_impl(last_jobs_found):
    new_jobs = get_jobs()
    
    if new_jobs:    # If jobs, notify
        notify(new_jobs, last_jobs_found) 
    else:   # If no jobs, confirm
        print(f"No jobs available at this time (empty table: {new_jobs})")
        confirm_no_jobs()

    # Update memory
    return set(new_jobs) # Success! These become the "last seen" for next time

def single_job_check(last_jobs_found):
    """Check jobs with retry on failure"""
    def check_action():
        return single_job_check_impl(last_jobs_found)
    
    return retry_on_failure(check_action)

def driver_is_alive():
    try:
        if driver:
            driver.current_url  # This will fail if Chrome was killed
            return True
    except:
        return False
    
def logged_in():
    global driver

    try:    
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "job-search"))
        )

        return True
    except TimeoutException:
        print("Job search element not found - likely logged out")
    except Exception as e:
        print(f"Other error occurred: {e}")    
    return False


def prepare_session():
    global driver

    # Make sure driver is alive
    if not driver_is_alive():
        create_driver()

    # Make sure logged in
    if not logged_in():
        login()

def get_wait_time():

    now = datetime.datetime.now(TIMEZONE)
    now = now.hour
    
    print(f"Local time: {now.strftime('%I:%M %p')} (Hour: {now})")
    
    # Late night (11 PM to 5 AM) - sleep mode
    if now >= 23 or now < 5:
        print("Sleep mode: checking every 3-3.5 hours")
        return random.randint(10800, 12600)  
    
    # Early morning (5 AM to 6 AM) - light activity
    elif 5 <= now < 6:
        print("Early morning: checking every 60-90 minutes")
        return random.randint(3600, 5400)  
    
    # School hours (6 AM to 4 PM) - most active
    elif 6 <= now < 16:
        print("School hours: checking every 10-25 minutes")
        return random.randint(600, 1500)  
    
    # After school (4 PM to 8 PM) - very active
    elif 16 <= now < 20:
        print("After school: checking every 10-45 minutes")
        return random.randint(600, 2700)  
    
    # Evening (8 PM to 11 PM) - moderate
    else:
        print("Evening: checking every 20-45 minutes") 
        return random.randint(1200, 2700)  

"""
Run a single session
""" 
def run_session_impl():
    last_jobs_found = set()  # Fresh memory for this session
    runs = 10
    for i in range(runs):
        prepare_session()
        print(f"\n🔍 Starting job check {i+1}/{runs}")
        last_jobs_found = single_job_check(last_jobs_found) 
        print(f"💤 Waiting before next check...")
        time.sleep(get_wait_time())  # 2 minutes between checks   
    print(f"Completed {runs} runs.")

    destroy_driver()    # Fresh start


def run_session():            
    return retry_on_failure(run_session_impl, on_failure="destroy_driver")


if __name__ == "__main__":
    try:
        while True:
            run_session()    
    except TooManyFailuresError as e:
            print(f"Too many failures: {e}")
            send_text_notification(f"Job bot needs help: {e}")
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