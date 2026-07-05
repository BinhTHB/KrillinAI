import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar('T')

def retry(call: Callable[[], T], attempts: int = 3, delay_seconds: float = 2.0, backoff: float = 2.0) -> T:
    last_error: Exception | None = None
    current_delay = delay_seconds

    for attempt in range(1, attempts + 1):
        try:
            return call()
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(current_delay)
            current_delay *= backoff

    raise RuntimeError(f'retry failed after {attempts} attempts') from last_error
