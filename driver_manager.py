from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from error_handling import TemporaryError
driver = None

def driver_is_alive():
    try:
        if driver:
            driver.current_url  # This will fail if Chrome was killed
            return True
        return False
    except:
        return False

def destroy_driver():
    global driver

    try:
        # Check if driver exists and close it
        if driver_is_alive():
            driver.quit()
            print("Chrome browser closed")
            
        # Clean up Chrome's temp directory
        import shutil
        shutil.rmtree("/tmp/chrome_jobbot", ignore_errors=True)
        print("Cleaned up Chrome temp directory")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        # Still try to clean up temp directory even if driver.quit() failed
        import shutil
        shutil.rmtree("/tmp/chrome_jobbot", ignore_errors=True)
    finally:
        driver = None

def create_driver():
    global driver

    # Clean up any existing driver first
    destroy_driver()    

    # Selenium config
    options = Options() # Creates an empty ChromeOptions object. This will store settings for Selenium
    options.add_argument("--headless=new")  # Runs the browser without a GUI window
    options.add_argument("--no-sandbox") # Disables the browser’s “sandbox” security feature
    options.add_argument("--disable-dev-shm-usage") # Prevents Chrome from using /dev/shm (shared memory)
    options.add_argument("--user-data-dir=/tmp/chrome_jobbot")  # put temp folders in /tmp/chrome_jobbot
    
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