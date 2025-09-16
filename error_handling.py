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

        except PermanentError as e:
            # Don't retry, escalate immediately
            print(f"Permanent error in {action_func.__name__}: {e}")
            raise e