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
    print(f"message\n\n")

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

    now = datetime.datetime.now(pytz.timezone('America/Los_Angeles'))
    message += f"\n\n @ {now.strftime('%I:%M %p')}"

    driver.save_screenshot(screenshot_name)
    notify_function(message, screenshot_name)  # This calls whatever function you passed in
    os.remove(screenshot_name)


"""
Randomized wait times
"""
def get_wait_time():

    now = datetime.datetime.now(pytz.timezone('America/Los_Angeles'))
    current_hour = now.hour
    
    print(f"Local time: {now.strftime('%I:%M %p')} (Hour: {current_hour})")
    
    # Late night (11 PM to 5 AM) - sleep mode
    if current_hour >= 23 or current_hour < 5:
        print("Sleep mode: checking every 3-3.5 hours")
        return random.randint(10800, 12600)  
    
    # Early morning (5 AM to 6 AM) - light activity
    elif 5 <= current_hour < 6:
        print("Early morning: checking every 60-90 minutes")
        return random.randint(3600, 5400)  
    
    # School hours (6 AM to 4 PM) - most active
    elif 6 <= current_hour < 16:
        print("School hours: checking every 10-25 minutes")
        return random.randint(600, 1500)  
    
    # After school (4 PM to 8 PM) - very active
    elif 16 <= current_hour < 20:
        print("After school: checking every 10-45 minutes")
        return random.randint(600, 2700)  
    
    # Evening (8 PM to 11 PM) - moderate
    else:
        print("Evening: checking every 20-45 minutes") 
        return random.randint(1200, 2700)  

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
    
    except TimeoutException:
        # Message didn't appear - something might be wrong
        notify_admin("Message didn't appear - something might be wrong")
        
    except Exception as e:
        # Other error checking for the message
        notify_admin(f"Other error checking for the message: {e}")

def get_buttons(class_name):
    buttons = driver.find_elements(By.CLASS_NAME, class_name)

    if not buttons:
        print("No accept buttons were found")
        return None
    
    print(f"Found {len(buttons)} {class_name} buttons")
    return buttons

"""
Accept jobs
"""
def confirm_accept():
    find_confirmation_text(class_name="pds-message-content", text="Success, you have accepted job ")

    screenshot_name="accept_confirmed.png"
    message = "Accept button confirmed"
    screenshot_and_notify(message, screenshot_name, notify_users)

def confirm_no_jobs():
    find_confirmation_text(class_name="pds-message-info", text="no jobs available")
    print("No jobs available (confirmed from message box).")

def accept_first_job():
    try:
        # Get all buttons
        accept_buttons = get_buttons(class_name="accept-icon")

        if not accept_buttons:
            notify_admin(f"Failed to accept - accept buttons were not found. Trying again")
            raise TemporaryError("Accept buttons missing")  # Will retry

        first_button = accept_buttons[0]

        if not first_button.is_displayed() or not first_button.is_enabled():
            print("Button is found but not active")
            raise TemporaryError("Accept button is not active.")

        driver.execute_script("arguments[0].click();", first_button)
        
        # Wait for page to respond
        time.sleep(5)

        # Prepare message and screenshot 
        message = "Accept button clicked"
        screenshot_name = "accept_clicked.png"
        screenshot_and_notify(message, screenshot_name, notify_admin)

    except TimeoutException as e:
        # This could be slow network OR bad credentials
        raise TemporaryError(f"Timeout exception during accept. Error: {e}")
    
    except NoSuchElementException as e:
        # Elements not found - website might have changed
        raise TemporaryError(f"Elements not found during accept. Error: {e}") 
    
    except Exception as e:
        # Any other selenium error - treat as temporary
        raise TemporaryError(f"Unexpected error during accept. Error: {e}")

"""
Send message to users with job updates
"""
def notify_of_jobs(current_jobs):
    # Scroll to make sure job table is visible
    job_table_element = driver.find_element(By.ID, "parent-table-desktop-available")
    driver.execute_script("arguments[0].scrollIntoView(true);", job_table_element)
    time.sleep(1)

    message = f"New job(s) posted:\n\n" + "\n\n".join(current_jobs) 
    screenshot_name = "job_found.png"
    screenshot_and_notify(message, screenshot_name, notify_users)

def parse_jobs():
    global driver 

    # refresh page before check
    try:
        driver.refresh()
    except Exception as e:
        raise TemporaryError(f"Failed to refresh page: {e}")
    
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
    notify_admin(rows)
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

"""
Run a single session
""" 
def run_session_impl():
    runs = 10
    for i in range(runs):
        prepare_session()
        print(f"\n🔍 Starting job check {i+1}/{runs}")
        jobs_found = parse_jobs() 

        if jobs_found:
            notify_of_jobs(jobs_found)
            accept_first_job()
            confirm_accept()
        else:
            confirm_no_jobs()
        
        print(f"💤 Waiting before next check...")
        time.sleep(get_wait_time())  
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
