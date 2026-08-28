import functools
import time


def retry_with_backoff(retries=3, backoff_in_seconds=5):
    """Decorator to retry API calls on temporary failure."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        print(
                            f"[RETRY ERROR] Max retries ({retries}) reached. Raising error."
                        )
                        raise e
                    sleep_time = backoff_in_seconds * (2**x)
                    print(
                        f"[RETRY WARNING] Transient error ({e}). Retrying in {sleep_time}s..."
                    )
                    time.sleep(sleep_time)
                    x += 1

        return wrapper

    return decorator