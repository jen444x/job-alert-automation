import os
import requests

from dotenv import load_dotenv

# Load credentials
load_dotenv() 

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