import time
from urllib.parse import urljoin

import requests


def poll_for(
    event_name,
    base_timeout=0.3,
    multiplier=1.2,
    ttl=30,
    max_attempts=None,
    sleep_f=time.sleep,
):
    attempt_number = 1
    time_awaited = 0
    while True:
        yield attempt_number, time_awaited
        if time_awaited > ttl:
            raise Exception(f"timeout while waiting for '{event_name}'")
        if max_attempts and attempt_number > max_attempts:
            raise Exception(f"max attempts reached while waiting for '{event_name}'")
        timeout = base_timeout * (multiplier ** (attempt_number - 1))
        sleep_f(timeout)
        time_awaited += timeout
        attempt_number += 1


class PrefixUrlHttpSession(requests.Session):
    def __init__(self, prefix_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix_url = prefix_url

    def request(self, method, url, *args, **kwargs):
        url = urljoin(self.prefix_url, url)
        response = super().request(method, url, *args, **kwargs)
        response.raise_for_status()
        return response
