from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException)
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

# Configurable time ranges (in minutes)  
EARLY_MORN_MIN, EARLY_MORN_MAX = 5, 25   
LATE_MORN_MIN, LATE_MORN_MAX = 5, 25        
NOON_MIN, NOON_MAX = 25, 60
EVENING_MIN, EVENING_MAX = 25, 60  
NIGHT_MIN, NIGHT_MAX = 90, 270  

UNWANTED_DATES = [
    "09/15/2025"
]

BLOCK_SAME_DAY = True  # Easy toggle

UNWANTED_CLASSIFICATIONS = [
    "imapired"
]

# Load credentials
load_dotenv() 

"""
Exception classes
"""
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
    """Too many retries = permanent failure"""
    pass

# Local timezone
local_tz = pytz.timezone('America/Los_Angeles')  # Pacific Time

def get_now():
    return datetime.datetime.now(local_tz)

"""
Send Pushover notifications
"""
PRODUCTION_USERS = [
    os.getenv("ADMIN_USER_1"),    
    os.getenv("PRODUCTION_USER_1")   
]

ADMIN_USERS = [
    os.getenv("ADMIN_USER_1")
]

def send_notification(users, message, screenshot_path=None):
    """Sends notifications with optional screenshot"""
    print("Sending message to user: ")
    print(f"{message}\n\n")

    image_file = None

    if screenshot_path:
        try:
            image_file = open(screenshot_path, 'rb')
        except Exception as e:
            print(f"Failed to open screenshot {screenshot_path}: {e}")
            print(f"Will only send text.")
    try:
        for recipient in users:
            try:
                payload = {
                    "token": os.getenv("PUSHOVER_API_TOKEN"),
                    "user": recipient,
                    "message": message,
                }

                files = None
                if image_file:
                    files = {"attachment": image_file}
                
                response = requests.post("https://api.pushover.net/1/messages.json", 
                                        data=payload, files=files)
                response.raise_for_status()
                print(f"Sent notification to {recipient}")
            except Exception as e:
                print(f"Failed to send notification to {recipient}:", e)
    finally:
        if image_file:
            image_file.close()

def notify_admin(message, screenshot_path=None):
    send_notification(ADMIN_USERS, message, screenshot_path)

def notify_users(message, screenshot_path=None):
    send_notification(PRODUCTION_USERS, message, screenshot_path)

def screenshot_and_notify(message, screenshot_name, notify_function=notify_admin):
    """Takes, sends, then deletes screenshot"""
    global driver

    now = get_now()
    message += f"\n\n @ {now.strftime('%I:%M %p')}"

    driver.save_screenshot(screenshot_name)
    notify_function(message, screenshot_name)  # This calls whatever function you passed in
    os.remove(screenshot_name)

def dump_debug(tag="debug"):
    global driver
    timestamp = int(time.time())
    try:
        # Save HTML
        html_path = f"page_{tag}_{timestamp}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"Saved HTML: {html_path}")

        # Save screenshot
        png_path = f"page_{tag}_{timestamp}.png"
        driver.save_screenshot(png_path)
        print(f"Saved screenshot: {png_path}")

    except Exception as e:
        print(f"Failed to dump debug info: {e}")



"""
Randomized wait times
"""
def get_wait_time():

    now = get_now()
    current_hour = now.hour
    
    print(f"Local time: {now.strftime('%I:%M %p')} (Hour: {current_hour})")

    # Early morning (5 AM to 9 AM) - most active
    if 5 <= current_hour < 9:
        print(f"Early morning: checking every {EARLY_MORN_MIN}-{EARLY_MORN_MAX} minutes")
        return random.randint(EARLY_MORN_MIN * 60, EARLY_MORN_MAX * 60)
    
    # Late morning (9 AM to 12 PM) - somewhat active
    elif 9 <= current_hour < 12:
        print(f"Late morning: checking every {LATE_MORN_MIN}-{LATE_MORN_MAX} minutes")
        return random.randint(LATE_MORN_MIN * 60, LATE_MORN_MAX * 60)
    
    # Noon (12 PM to 6 PM) - not active
    elif 12 <= current_hour < 18:
        print(f"Noon: checking every {NOON_MIN}-{NOON_MAX} minutes")
        return random.randint(NOON_MIN * 60, NOON_MAX * 60)
    
    # Evening (6 PM to 9 PM) - most active
    elif 18 <= current_hour < 21:
        print(f"Evening: checking every {EVENING_MIN}-{EVENING_MAX} minutes")
        return random.randint(EVENING_MIN * 60, EVENING_MAX * 60)
    
    # Night (9 PM to 5 AM) - not active
    else:
        print(f"Evening: checking every {NIGHT_MIN}-{NIGHT_MAX} minutes")
        # Don't let it take up early morning time 
        return random.randint(NIGHT_MIN * 60, NIGHT_MAX * 60)

"""
Try an action with retry on failure
"""
def retry_on_failure(action_func, max_retries=2, delay=15):
    errors = [] # Stores all errors

    for attempt in range(max_retries):
        try:
            return action_func()    # Return on success
         
        except (TemporaryError, Exception) as e:
            # Handle both temporary and unexpected errors the same way
            error_type = "Temporary" if isinstance(e, TemporaryError) else "Unexpected"
            errors.append(f"Attempt {attempt + 1} failed during {action_func.__name__}: {error_type} - {e}")  
            
            if attempt == max_retries - 1:  # Last attempt
                all_errors = "\n".join(errors)
                raise TooManyFailuresError(f"{action_func.__name__} failed {max_retries} times:\n{all_errors}")
            
            print(f"{error_type} error, refreshing and retrying: {e}")
            if driver:
                driver.refresh()
            time.sleep(delay)

        except PermanentError as e:
            # Don't retry, escalate immediately
            print(f"Permanent error in {action_func.__name__}: {e}")
            raise e
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
    
    # Anti-detection options
    options.add_argument("--disable-blink-features=AutomationControlled")  # Removes navigator.webdriver flag
    options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Removes automation indicators
    options.add_experimental_option('useAutomationExtension', False)  # Disables Chrome automation extension
    
    print("configured selenium\n")
        
    try:        
        # Set up WebDriver
        driver = webdriver.Chrome(options=options)
        print("Set up webdrive\n")

        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
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

        # Wait for login form elements
        username_field = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, os.getenv("USERNAME_FIELD", "userId")))
        )
        password_field = driver.find_element(By.ID, os.getenv("PASSWORD_FIELD", "userPin"))

        # Fill in form to login
        username_field.send_keys(USERNAME)
        password_field.send_keys(PASSWORD + Keys.RETURN)

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

"""
Find confirmation message 
"""
def find_confirmation_text(class_name, text):
    global driver

    # Wait to see if message appears
    # if this method doesnt work switch to other
    try:
        WebDriverWait(driver, 30).until(
            EC.text_to_be_present_in_element(
                (By.CLASS_NAME, class_name), text
            )
        )
    
    except TimeoutException as e:
        # Message didn't appear - something might be wrong
        notify_admin("Message didn't appear - something might be wrong")
        raise TemporaryError(f"Message didn't appear: {e}")
        
    except Exception as e:
        # Other error checking for the message
        notify_admin(f"Other error checking for the message: {e}")
        raise TemporaryError(f"Message didn't appear: {e}")

def get_buttons(class_name):
    try:
        buttons = driver.find_elements(By.CLASS_NAME, class_name)

        if not buttons:
            print("No accept buttons were found")
            return None
        
        print(f"Found {len(buttons)} {class_name} buttons")
        return buttons
    
    except Exception as e:
        raise TemporaryError(f"Unexpected error during get_buttons(). Error: {e}")    

"""
Accept jobs
"""
def confirm_job_accept():
    try:
        find_confirmation_text(class_name="pds-message-content", text="Success, you have accepted job ")
        screenshot_name="accept_confirmed.png"
        message = "Accept button confirmed"
        screenshot_and_notify(message, screenshot_name, notify_users)

    except Exception as e:
        try:
            # Check if job was taken
            find_confirmation_text("pds-message-content", "Accept Job failed. Job is no longer available.")
            message = "Job is no longer available"
            screenshot_name = "job_gone.png"
            screenshot_and_notify(message, screenshot_name, notify_users)
        except Exception as e:
            raise TemporaryError(f"Error when checking if job is no longer available: {e}")
    
def click_accept(job_index=0):
    # Get all buttons
    accept_buttons = get_buttons(class_name="accept-icon")

    if not accept_buttons:
        notify_admin(f"Failed to accept - accept buttons were not found. Trying again")
        raise TemporaryError("Accept buttons missing")  
    
    if job_index >= len(accept_buttons):
        raise TemporaryError(f"Job index {job_index} out of range - only {len(accept_buttons)} jobs available")

    button = accept_buttons[job_index]

    if not button.is_displayed() or not button.is_enabled():
        print(f"Button {job_index} is found but not active")
        raise TemporaryError(f"Accept button {job_index} is not active.")

    driver.execute_script("arguments[0].click();", button)

    try:
        driver.execute_script("arguments[0].click();", button)
        print("JavaScript click executed successfully")
    except Exception as e:
        raise TemporaryError(f"Unexpected error during accept job click: {e}")
    
def click_confirm_accept():
    # Using WebDriverWait since page changed after click accept
    global driver
    try:
        confirm_btn = WebDriverWait(driver, 45).until(
            EC.element_to_be_clickable((By.ID, "confirm-dialog"))
        )
        confirm_btn.click()
    except TimeoutException:
        raise TemporaryError("Confirmation button did not appear within 30 seconds")
    except Exception as e:
        raise TemporaryError(f"Failed to click confirmation button: {e}")

def accept_first_job(jobs):
    # Do not accept unwanted dates
    now = get_now()
    date_today = now.strftime("%m/%d/%Y")
    print(date_today) 

    # Convert set to list so we can iterate in order
    job_list = list(jobs)

    for i, job in enumerate(job_list):
        print(f"Checking job {i+1}: {job}")
        
        # Check if this job should be skipped
        # Check same-day jobs
        if BLOCK_SAME_DAY and date_today in job.lower():
            notify_users(f"Skipped auto accept {i+1} - same day ({date_today})")
            continue 
        
        # Check unwanted dates
        skip_job = False
        for unwanted_date in UNWANTED_DATES:
            if unwanted_date in job.lower():
                notify_users(f"Skipped auto accept {i+1} - unwanted day ({unwanted_date})")
                skip_job = True
                break
            
        if skip_job:
            continue 

        # Check for unwanted classifications
        for unwanted_classification in UNWANTED_CLASSIFICATIONS:
            if unwanted_classification in job.lower():
                notify_users(f"Skipped auto accept {i+1} - unwanted classification ({unwanted_classification})")
                skip_job = True
                break
            
        if skip_job:
            continue 

        # If this job passes all filters, accept it
        print(f"Accepting job {i+1}")
        try:
            click_accept(i)  # click the accept button for job at index i
            click_confirm_accept()
            confirm_job_accept()

            message = "Accept button clicked"
            screenshot_name = "accept_clicked.png"
            screenshot_and_notify(message, screenshot_name, notify_admin)
            return  # Exit after successfully accepting one job
            
        except Exception as e:
            raise TemporaryError(f"Error during job accept. Error: {e}")

def notify_of_jobs(current_jobs):
    """Send message to users with job updates"""
    try: 
        # Scroll to make sure job table is visible
        job_table_element = driver.find_element(By.ID, "parent-table-desktop-available")
        driver.execute_script("arguments[0].scrollIntoView(true);", job_table_element)
        time.sleep(1)

        message = f"New job(s) posted:\n\n" + "\n\n".join(current_jobs) 
        screenshot_name = "job_found.png"
        screenshot_and_notify(message, screenshot_name, notify_users)
    except NoSuchElementException as e:
        # Job table element not found - UI might have changed
        raise PermanentError(f"Job table element not found - UI may have changed: {e}")
    except Exception as e:
        # Catch-all for unexpected errors
        raise TemporaryError(f"Unexpected error in notify_of_jobs: {e}")

def parse_jobs():
    global driver 
    
    try:
        # Wait up to 50 seconds for dashboard to load
        WebDriverWait(driver, 50).until(
            EC.presence_of_element_located((By.ID, "job-search"))  
        )
    except TimeoutException as e:
        dump_debug("no_jobsearch")  # <-- save HTML for debugging
        raise TemporaryError(f"Timeout: job-search not found after refresh: {e}")
    except Exception as e:
        dump_debug("other_error")
        raise TemporaryError(f"Unexpected error while waiting for job-search: {e}")
    
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
    print(f"{job_table.get_text(separator=" | ", strip=True)}\n")

    # Get all table rows except the header
    rows = job_table.find_all("tr")[1:]  # skip the header
    print(f"rows:\n {rows}")

    jobs = set()
    
    if rows:
        for row in rows:
            cells = row.find_all("td")
            details = [cell.get_text(strip=True) for cell in cells]
            job = " | ".join(details)
            print("Found job:", job)
            jobs.add(job)
    
    return jobs

def driver_is_alive():
    try:
        if driver:
            driver.current_url  # This will fail if Chrome was killed
            return True
    except:
        return False
    
def logged_in():
    try:    
        driver.refresh()
    except Exception as e:
        print(f"Failed to refresh page on logged_in(): {e}")  
        # Try to recreat driver to work  
        create_driver()

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


def prepare_session(run):
    global driver

    if (run == 0):
        create_driver()
        login()
    else:
        # Make sure driver is alive
        if not driver_is_alive():
            create_driver()

        # Make sure logged in
        if not logged_in():
            login()

"""
Run a single session
""" 
def run_session_impl():
    runs = 10
    for i in range(runs):
        prepare_session(i)
        print(f"\n🔍 Starting job check {i+1}/{runs}")
        jobs_found = parse_jobs() 

        if jobs_found:
            notify_of_jobs(jobs_found)
            accept_first_job(jobs_found)
        else:
            find_confirmation_text("pds-message-info", "no jobs available")
        
        wait_time = get_wait_time()
        print(f"Waiting {wait_time/60:.1f} minutes before next check...\n")
        time.sleep(wait_time)  
    print(f"Completed {runs} runs.")

    destroy_driver()    # Fresh start


def run_session():            
    return retry_on_failure(run_session_impl)

if __name__ == "__main__":
    try:
        while True:
            run_session()    
    except TooManyFailuresError as e:
        notify_admin(f"Too many failures. Job bot needs help: {e}")
    except PermanentError as e:
        notify_users(f"Bot stopping permanently. Job bot needs help: {e}")
    except KeyboardInterrupt:
        print("Manually stopping bot...")
    except Exception as e:
        notify_admin(f"Fatal error. Job bot crashed: {e}")
    finally:
        if 'driver' in globals() and driver:
            driver.quit()
            print("Browser cleaned up")
