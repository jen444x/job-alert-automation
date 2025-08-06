import requests
import os
from dotenv import load_dotenv

load_dotenv()

RECIPIENTS = [
    os.getenv("PUSHOVER_USER_KEY"),      # you
    os.getenv("KIM_PUSHOVER_USER")    # her
]

def send_text_notification(body):
    payload = {
        "token": os.getenv("PUSHOVER_API_TOKEN"),
        "user": os.getenv("KIM_PUSHOVER_USER"),
        "message": body,
    }

    try:
        response = requests.post("https://api.pushover.net/1/messages.json", data=payload)
        response.raise_for_status()
        print("Sent Pushover alert")
    except Exception as e:
        print("Failed to send Pushover alert:", e)

send_text_notification("Test from your job checker bot 🚨")