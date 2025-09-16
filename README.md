# Automated Job Monitoring System

A Python-based web automation tool that monitors job postings and sends real-time notifications when new opportunities become available.

## Project Overview

Developed an automated monitoring system that tracks job listings on a web portal and provides instant notifications. The system runs continuously on cloud infrastructure and demonstrates proficiency in web automation, API integration, and production deployment.

## Technical Implementation

### Web Automation & Data Extraction

- **Selenium WebDriver**: Automates browser interactions and form submissions
- **BeautifulSoup4**: Parses HTML and extracts structured data from web tables
- **Headless Browser**: Runs efficiently without GUI for server deployment

### Real-time Notification System

- **Push Notifications**: Integrates with Pushover API for reliable message delivery
- **Duplicate Detection**: Implements intelligent filtering to prevent redundant alerts
- **Error Handling**: Comprehensive exception management with debugging capabilities

### Production Infrastructure

- **Cloud Hosting**: Deployed on Digital Ocean for 24/7 availability
- **Environment Security**: Secure credential management using environment variables
- **Resource Optimization**: Configured for minimal server resource usage

## Key Technical Features

- Automated form filling and navigation
- Dynamic content parsing and data extraction
- RESTful API integration for notifications
- Session management and error recovery
- Production-ready cloud deployment
- Comprehensive logging and debugging

## Technology Stack

- **Python 3.x** - Core application development
- **Selenium** - Web browser automation framework
- **BeautifulSoup4** - HTML parsing and data extraction
- **Requests** - HTTP client for API communications
- **Python-dotenv** - Configuration management
- **Digital Ocean** - Cloud hosting platform
- **Chromium** - Headless browser engine

## Architecture

The system follows a modular design pattern:

- **Main Monitor** (`check_jobs.py`) - Core automation logic with continuous monitoring
- **Configuration Management** - Environment-based credential handling

## Setup and Installation

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**

   ```
   PORTAL_USERNAME=your_portal_username
   PORTAL_PASSWORD=your_portal_password
   PORTAL_URL=https://your-job-portal.com/login
   PUSHOVER_API_TOKEN=your_pushover_api_token
   ADMIN_USER_1=admin_user_key
   PRODUCTION_USER_1=production_user_key
   USERNAME_FIELD=userId
   PASSWORD_FIELD=userPin
   JOB_TABLE_ID=job-table-id
   ```

3. **System Requirements**
   - ChromeDriver for browser automation
   - Chromium browser for headless operation

## Skills Demonstrated

- **Web Automation** - Complex browser interaction and form handling
- **Data Processing** - HTML parsing, data extraction, and filtering algorithms
- **API Integration** - RESTful service consumption and error handling
- **Production Deployment** - Linux server configuration and service management
- **Security Practices** - Secure credential management and environment isolation
- **Problem Solving** - Automated solution for time-sensitive data monitoring
- **Code Organization** - Modular design with separation of concerns
