# Job Alert Automation

 

A production-ready Python bot that monitors job portals 24/7, sends instant push notifications when jobs appear, and automatically accepts suitable positions based on configurable filters.

 

## Overview

 

This system automates the entire job hunting workflow:

- Continuously monitors a job portal using browser automation

- Sends real-time push notifications with screenshots when new jobs are posted

- Automatically accepts the first job that passes filter criteria

- Runs indefinitely on cloud infrastructure with intelligent time-based scheduling

 

## Architecture

 

The system follows a clean, modular design with clear separation of concerns:

 

```

check_jobs.py          → Main controller (login, parsing, job acceptance)

driver_manager.py      → WebDriver lifecycle management

notifications.py       → Pushover API integration

timing.py              → Time-aware scheduling logic

error_handling.py      → Exception hierarchy and retry mechanism

```

 

### Module Details

 

**check_jobs.py** (Main Controller)

- `login()` - Authenticates with portal credentials

- `parse_jobs()` - Extracts job listings from HTML tables

- `accept_first_job()` - Filters and auto-accepts jobs

- `run_session_impl()` - Runs 10 check cycles per session

 

**driver_manager.py** (Browser Management)

- Creates headless Chrome with anti-detection measures

- Manages driver lifecycle (create, verify, destroy)

- Cleans up temp directories

 

**notifications.py** (Push Notifications)

- Sends messages via Pushover API with screenshot attachments

- Supports separate admin and user notification lists

- Graceful failure handling per recipient

 

**timing.py** (Smart Scheduling)

- Adjusts check frequency based on time of day (Pacific timezone)

- Peak hours (5-9 AM, 6-9 PM): 5-25 minute intervals

- Off-peak (12-6 PM): 2-8 minute intervals

- Night (9 PM-5 AM): 90-270 minute intervals

 

**error_handling.py** (Exception System)

- `TemporaryError` - Retryable failures (network, timeouts)

- `PermanentError` - Requires human intervention

- `retry_on_failure()` - Automatic retry with exponential backoff

 

## Key Features

 

### Intelligent Job Filtering

- **Same-day blocking**: Skip jobs scheduled for today (`BLOCK_SAME_DAY`)

- **Date blacklist**: Exclude specific dates (`UNWANTED_DATES`)

- **Classification filtering**: Skip unwanted job types (`UNWANTED_CLASSIFICATIONS`)

 

### Anti-Detection Measures

- Removes `navigator.webdriver` flag

- Disables automation indicators

- Randomized wait times to mimic human behavior

 

### Robust Error Handling

- Automatic retry on temporary failures (max 2 attempts)

- Debug dumps (HTML + screenshots) on errors

- Session recovery if browser crashes

- Escalation to admin on permanent failures

 

### Production-Ready

- Headless browser operation for server deployment

- Secure credential management via environment variables

- Resource-efficient (custom temp directories)

- Comprehensive logging and debugging

 

## Technology Stack

 

- **Python 3.x** - Core application

- **Selenium** - Browser automation and form interaction

- **BeautifulSoup4** - HTML parsing and data extraction

- **Requests** - HTTP client for Pushover API

- **python-dotenv** - Environment variable management

- **pytz** - Timezone handling (Pacific Time)

- **Chromium** - Headless browser engine

 

## Setup and Installation

 

### 1. Install Dependencies

 

```bash

pip install -r requirements.txt

```

 

### 2. Install System Requirements

 

**ChromeDriver** (must match your Chrome version):

```bash

# Example for Linux

wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE

# Download appropriate version

sudo mv chromedriver /usr/local/bin/

sudo chmod +x /usr/local/bin/chromedriver

```

 

**Chromium Browser**:

```bash

# Ubuntu/Debian

sudo apt-get install chromium-browser

 

# CentOS/RHEL

sudo yum install chromium

```

 

### 3. Configure Environment Variables

 

Create a `.env` file in the project root:

 

```bash

# Portal credentials

PORTAL_USERNAME=your_portal_username

PORTAL_PASSWORD=your_portal_password

PORTAL_URL=https://your-job-portal.com/login

 

# UI element selectors (customize for your portal)

USERNAME_FIELD=userId

PASSWORD_FIELD=userPin

JOB_TABLE_ID=parent-table-desktop-available

 

# Pushover notification credentials

PUSHOVER_API_TOKEN=your_pushover_api_token

ADMIN_USER_1=your_admin_pushover_user_key

PRODUCTION_USER_1=your_production_pushover_user_key

```

 

**Get Pushover credentials:**

1. Sign up at [pushover.net](https://pushover.net/)

2. Create an application to get your API token

3. Find your user key in your account settings

 

### 4. Customize Job Filters (Optional)

 

Edit `check_jobs.py` lines 18-26:

 

```python

UNWANTED_DATES = [

    "09/15/2025"  # Add dates to skip

]

 

BLOCK_SAME_DAY = True  # Block jobs starting today

 

UNWANTED_CLASSIFICATIONS = [

    "impaired"  # Add classifications to skip

]

```

 

## Usage

 

### Run Locally

```bash

python check_jobs.py

```
 




## How It Works

 

### Execution Flow

 

```

1. Initialize WebDriver with headless Chrome

2. Login to job portal with credentials

3. Loop 10 times:

   a. Navigate to "Available Jobs" tab

   b. Parse job listings from HTML table

   c. If jobs found:

      - Send push notification with screenshot

      - Filter jobs (dates, classifications)

      - Accept first suitable job

   d. Wait (time-aware interval)

4. Destroy driver (clean slate)

5. Repeat indefinitely

```

 

### Session Management

- Each session runs 10 job checks

- Driver is destroyed after each session to prevent memory leaks

- Automatic session recovery if browser crashes

- Login state verified before each check

 

### Error Recovery

- **Network timeouts**: Retry automatically (2 attempts)

- **Login failures**: Retry with fresh driver

- **Element not found**: Dump debug info and retry

- **Too many failures**: Notify admin and stop

 

## Project Structure

 

```

job-alert-automation/

├── check_jobs.py           # Main controller (415 lines)

├── driver_manager.py       # Browser management (71 lines)

├── notifications.py        # Push notifications (58 lines)

├── timing.py              # Smart scheduling (73 lines)

├── error_handling.py      # Exception system (45 lines)

├── requirements.txt       # Python dependencies

├── .env                   # Credentials (not in git)

├── .gitignore            # Git exclusions

└── README.md             # This file

```
