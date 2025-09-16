import datetime
import pytz
import random

# Local timezone
LOCAL_TZ = pytz.timezone('America/Los_Angeles')  # Pacific Time

# Configurable time ranges (in minutes)  
EARLY_MORN_MIN, EARLY_MORN_MAX = 5, 25   
LATE_MORN_MIN, LATE_MORN_MAX = 5, 25        
NOON_MIN, NOON_MAX = 2, 8
EVENING_MIN, EVENING_MAX = 2, 8
NIGHT_MIN, NIGHT_MAX = 90, 270  

""" Gets currrent date and time """
def get_now():
    return datetime.datetime.now(LOCAL_TZ)

""" Randomized wait times """
def get_wait_time(current_hour=None):

    now = datetime.datetime.now(LOCAL_TZ)

    if current_hour is None:
        current_hour = now.hour
    current_minute = now.minute
    
    print(f"Local time: {now.strftime('%I:%M %p')} (Current_hour: {current_hour})")

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
        print(f"Night: checking every {NIGHT_MIN}-{NIGHT_MAX} minutes")

        wait_time = random.randint(NIGHT_MIN * 60, NIGHT_MAX * 60)

        # If it's between 1 AM and 5 AM, check if wait would go past 5 AM
        if 1 <= current_hour < 5:
            # 5 AM = 300 minutes from midnight

            curr_hour_in_mins = current_hour * 60 + current_minute

            # Check if wait time will go into early morning time slot
            
            # 5 AM = 300 minutes from midnight
            minutes_until_5am = 300 - curr_hour_in_mins

            if wait_time > minutes_until_5am:
                print(f"Wait would cross into early morning. Waiting {minutes_until_5am/60:.1f}")
                print("minutes until 5 AM, then getting early morning wait time.")
                # Add wait time from early morning slot
                return minutes_until_5am + get_wait_time(5)

        return wait_time